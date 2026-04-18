"""
updater.py — Moduł aktualizacji: sprawdzanie wersji przez GitHub API,
             pobieranie, weryfikacja SHA-256 i instalacja nowej wersji.

POPRAWKI BEZPIECZEŃSTWA (2026-03-06):
  SHA-001  — exact match nazwy pliku w SHA256SUMS (było: substring 'in', teraz: ==)
  SHA-002  — brak SHA256SUMS lub brak wpisu dla pliku = przerwanie instalacji
             (było: ostrzeżenie i kontynuacja)
  REDIR-001 — _SecureRedirectHandler blokuje downgrade HTTPS→HTTP oraz
              przekierowania poza dozwolone domeny GitHub
  REDIR-002 — walidacja schematu i domeny URL assetów przed rozpoczęciem pobierania
  ZIP-001  — bezpieczna ekstrakcja ZIP: walidacja path traversal i whitelist rozszerzeń
  BAT-001  — walidacja ścieżek wstrzykiwanych do skryptu BAT (whitelist znaków)
  RACE-001 — losowa nazwa pliku BAT + ACL ograniczony do bieżącego użytkownika
  LOG-001  — logi błędów w %APPDATA%\\KalkulatorPrawniczy\\logs\\ (nie obok EXE)
  LOG-002  — sanityzacja tracebacka: usuwanie tokenów i nagłówków Authorization

NOWA FUNKCJA:
  Sprawdzanie aktualizacji wykonywane co najwyżej raz dziennie.
  Data ostatniego sprawdzenia zapisywana w pliku
  %APPDATA%\\KalkulatorPrawniczy\\last_update_check.
  Wywołanie ręczne (wymus=True) zawsze pomija ten limit.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import os
import sys
import json
import threading
import urllib.request
import urllib.error
import urllib.parse
import tempfile
import hashlib
import shutil
import zipfile
import subprocess
import re
import secrets
import traceback
from datetime import date

from config import APP_VERSION, GITHUB_REPO
from constants import BG, GOLD, TEXT

# F-01: GITHUB_TOKEN usunięty z kodu — nie wbudowuj tokenu w EXE.
# Dla repozytoriów publicznych token jest zbędny.
# Dla prywatnych użyj zmiennej środowiskowej lub serwera proxy po stronie dewelopera.
GITHUB_TOKEN = ""

# ── URL do GitHub Releases API ────────────────────────────────────────────────
_GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

# ── Nagłówek User-Agent używany we wszystkich żądaniach ──────────────────────
_USER_AGENT = "KalkulatorPrawniczy-Updater/1.0"

# ── Dozwolone domeny GitHub (REDIR-001 / REDIR-002) ──────────────────────────
_GITHUB_ALLOWED_HOSTS = frozenset({
    "github.com",
    "api.github.com",
    "objects.githubusercontent.com",
    "github-releases.githubusercontent.com",
    "release-assets.githubusercontent.com",
    "codeload.github.com",
})

# ── Katalog danych aplikacji ──────────────────────────────────────────────────
def _katalog_appdata() -> str:
    """
    Zwraca ścieżkę do katalogu %APPDATA%\\KalkulatorPrawniczy\\ i tworzy go
    jeśli nie istnieje. Używany przez logi i plik znacznika daty.
    Na systemach bez APPDATA (testy Linux/macOS): katalog obok modułu.
    """
    appdata = os.environ.get("APPDATA") or os.path.dirname(os.path.abspath(__file__))
    katalog = os.path.join(appdata, "KalkulatorPrawniczy")
    os.makedirs(katalog, exist_ok=True)
    return katalog


# ── Plik znacznika ostatniego sprawdzenia aktualizacji ───────────────────────
def _plik_znacznika() -> str:
    """
    Zwraca ścieżkę do pliku przechowującego datę ostatniego sprawdzenia.
    Lokalizacja: %APPDATA%\\KalkulatorPrawniczy\\last_update_check
    """
    return os.path.join(_katalog_appdata(), "last_update_check")


def _czy_sprawdzac_dzisiaj() -> bool:
    """
    Zwraca True jeśli od ostatniego sprawdzenia minął co najmniej 1 dzień
    (lub plik znacznika nie istnieje / jest uszkodzony).
    Zwraca False jeśli aktualizacja była już sprawdzana dzisiaj.
    """
    sciezka = _plik_znacznika()
    try:
        with open(sciezka, "r", encoding="utf-8") as f:
            zapisana = f.read().strip()
        ostatnie = date.fromisoformat(zapisana)   # format RRRR-MM-DD
        return ostatnie < date.today()
    except Exception:
        # Brak pliku, zły format, błąd odczytu — sprawdzamy
        return True


def _zapisz_date_sprawdzenia() -> None:
    """Zapisuje dzisiejszą datę jako datę ostatniego sprawdzenia."""
    try:
        sciezka = _plik_znacznika()
        with open(sciezka, "w", encoding="utf-8") as f:
            f.write(date.today().isoformat())
    except Exception:
        pass  # Błąd zapisu nie może blokować działania aplikacji


# ── LOG-002: sanityzacja tracebacka ──────────────────────────────────────────
_RE_SANITIZE = [
    (re.compile(r'Authorization[^\n]*',          re.IGNORECASE), 'Authorization: [REDACTED]'),
    (re.compile(r'Bearer\s+\S+',                 re.IGNORECASE), 'Bearer [REDACTED]'),
    (re.compile(r'token\s+[A-Za-z0-9_\-]{10,}', re.IGNORECASE), 'token [REDACTED]'),
    (re.compile(r'ghp_[A-Za-z0-9]{36}'),                         '[GITHUB_TOKEN_REDACTED]'),
    (re.compile(r'github_pat_[A-Za-z0-9_]{82}'),                 '[GITHUB_TOKEN_REDACTED]'),
]

def _sanitize_traceback(tb: str) -> str:
    """
    LOG-002: Usuwa tokeny i nagłówki Authorization z tracebacka przed zapisem do logu.
    Zapobiega przypadkowemu ujawnieniu GITHUB_TOKEN w pliku logu.
    """
    for pattern, replacement in _RE_SANITIZE:
        tb = pattern.sub(replacement, tb)
    return tb


# ── ZIP-001: bezpieczna ekstrakcja ───────────────────────────────────────────
# Rozszerzenia BLOKOWANE — pliki wykonywalne skryptów powłoki i potencjalnie
# niebezpieczne typy. PyInstaller bundluje dziesiątki typów (.tcl, .tk, .zip,
# .so, .dylib, .manifest itp.) których nie da się z góry wyliczyć, dlatego
# zamiast whitelisty rozszerzeń ochronę zapewnia wyłącznie walidacja ścieżki
# (path traversal). Blokujemy tylko jawnie szkodliwe typy skryptów.
_ZIP_ZABLOKOWANE_ROZSZERZENIA = frozenset({
    ".bat", ".cmd", ".ps1", ".vbs", ".js", ".jse", ".wsf", ".wsh",
    ".scr", ".com", ".lnk", ".msi", ".reg",
})

def _bezpieczna_ekstrakcja(zip_path: str, extract_dir: str) -> None:
    """
    ZIP-001: Bezpieczna ekstrakcja archiwum ZIP.

    Zabezpieczenia:
      • Walidacja path traversal: każda ścieżka musi pozostać wewnątrz extract_dir
        (chroni przed ../../../Windows/System32/evil.dll itp.)
      • Blokada absolutnych ścieżek i ścieżek z '..'
      • Blacklist jawnie szkodliwych typów skryptów (.bat, .cmd, .ps1 itp.)

    Celowo NIE stosuje whitelisty rozszerzeń — PyInstaller bundluje legalne
    pliki dziesiątek typów (.tcl, .tk, .zip, .so, .manifest itp.) których
    nie da się z góry wyliczyć bez ryzyka zablokowania poprawnej instalacji.
    Walidacja ścieżki jest wystarczającą i kompletną ochroną przed ZIP Slip.

    Zastępuje bezpośrednie wywołanie zipfile.ZipFile.extractall().
    """
    real_base = os.path.realpath(extract_dir)
    real_base_sep = real_base + os.sep

    with zipfile.ZipFile(zip_path, "r") as zf:
        for member in zf.infolist():
            # Blokuj katalogi (końcowe '/') — tworzone automatycznie przy extract()
            if member.filename.endswith("/"):
                continue

            # Blacklist jawnie szkodliwych typów skryptów
            ext = os.path.splitext(member.filename)[1].lower()
            if ext in _ZIP_ZABLOKOWANE_ROZSZERZENIA:
                raise ValueError(
                    f"Niedozwolony typ pliku w archiwum: {member.filename!r}\n"
                    "Instalacja przerwana ze względów bezpieczeństwa.")

            # Walidacja path traversal — jedyna niezbędna i wystarczająca ochrona
            target = os.path.realpath(os.path.join(real_base, member.filename))
            if not target.startswith(real_base_sep):
                raise ValueError(
                    f"Wykryto path traversal w archiwum: {member.filename!r}\n"
                    "Instalacja przerwana ze względów bezpieczeństwa.")

            zf.extract(member, extract_dir)


# ── Porównywanie wersji ───────────────────────────────────────────────────────
def _ver_tuple(v: str) -> tuple:
    """
    Zamienia '1.2.3' na (1, 2, 3, 0) do porownania wersji.
    Wyrownuje do stalej dlugosci 4 zerami, zeby krotki roznej
    dlugosci byly porownywane poprawnie, np.:
      '1.1'   -> (1, 1, 0, 0)
      '1.0.9' -> (1, 0, 9, 0)
      => (1,1,0,0) > (1,0,9,0) == True  OK
    """
    try:
        t = tuple(int(x) for x in re.findall(r"\d+", v))
        return t + (0,) * max(0, 4 - len(t))
    except Exception:
        return (0, 0, 0, 0)


# ── Rozwiązywanie URL assetów (API vs browser, z fallbackiem) ────────────────
def _resolve_download_url(info: dict, api_key: str, url_key: str) -> str:
    """
    Zwraca właściwy URL do pobrania assetu lub pliku SHA256SUMS.
    Przy dostępnym tokenie preferuje URL API (umożliwia pobranie z prywatnych repozytoriów),
    w przeciwnym razie używa browser_download_url. Fallback na drugą opcję jeśli pierwsza jest pusta.
    """
    url = info.get(api_key) if GITHUB_TOKEN else info.get(url_key)
    if not url:
        url = info.get(url_key) or info.get(api_key)
    return url or ""


# ── REDIR-001: bezpieczny redirect handler ────────────────────────────────────
class _SecureRedirectHandler(urllib.request.HTTPRedirectHandler):
    """
    REDIR-001 / REDIR-002: Zastępuje oryginalny _TokenRedirectHandler.

    Chroni przed:
      • Downgrade HTTPS → HTTP przy przekierowaniu (np. 301/302 na http://)
      • Przekierowaniami poza dozwolone domeny GitHub
      • Wyciekiem tokenu Authorization do adresu przekierowania

    Oryginalny _TokenRedirectHandler usuwał tylko nagłówek Authorization.
    Ten handler robi to samo ORAZ waliduje schemat i domenę docelową.
    """

    def redirect_request(self, req, fp, h, code, msg, newurl):
        parsed = urllib.parse.urlparse(newurl)

        # REDIR-001: blokuj downgrade HTTPS → HTTP
        if parsed.scheme != "https":
            raise urllib.error.URLError(
                f"Przekierowanie na niezaszyfrowany adres zostało odrzucone: {newurl!r}\n"
                "Aktualizacja przerwana ze względów bezpieczeństwa.")

        # REDIR-001: blokuj przekierowania poza GitHub
        if parsed.netloc not in _GITHUB_ALLOWED_HOSTS:
            raise urllib.error.URLError(
                f"Przekierowanie poza dozwoloną domenę zostało odrzucone: {parsed.netloc!r}\n"
                "Dozwolone: " + ", ".join(sorted(_GITHUB_ALLOWED_HOSTS)))

        # Token Authorization celowo NIE jest przekazywany do nowego żądania
        return urllib.request.Request(
            newurl,
            headers={
                "User-Agent": (req.get_header("User-agent")
                               or "KalkulatorPrawniczy-Updater/1.0"),
                "Accept": "application/octet-stream",
            })


# ── Sprawdzanie wersji w tle ──────────────────────────────────────────────────
def _sprawdz_wersje_wykonaj(callback):
    """
    Wewnętrzna funkcja — odpytuje GitHub API i wywołuje callback.
    Nie zawiera żadnej logiki limitowania częstotliwości.
    Wywoływana przez obie funkcje publiczne poniżej.
    """
    def _worker():
        try:
            req = urllib.request.Request(
                _GITHUB_API_URL,
                headers={"User-Agent": _USER_AGENT,
                         "Accept": "application/vnd.github.v3+json",
                         **( {"Authorization": f"token {GITHUB_TOKEN}"}
                             if GITHUB_TOKEN else {} )},
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            # Zapisz datę sprawdzenia niezależnie od wyniku — żeby nie
            # odpytywać GitHub przy każdym uruchomieniu w tym samym dniu
            _zapisz_date_sprawdzenia()

            tag = data.get("tag_name", "").lstrip("v")
            body = data.get("body", "")

            asset_url = None
            asset_api_url = None
            asset_name = ""
            sums_url = None
            sums_api_url = None
            for asset in data.get("assets", []):
                name = asset.get("name", "").lower()
                if name.endswith(".zip") or name.endswith(".exe"):
                    asset_url     = asset.get("browser_download_url", "")
                    asset_api_url = asset.get("url", "")
                    asset_name    = asset.get("name", "")
                elif name in ("sha256sums", "sha256sums.txt"):
                    sums_url     = asset.get("browser_download_url", "")
                    sums_api_url = asset.get("url", "")

            if _ver_tuple(tag) > _ver_tuple(APP_VERSION):
                callback({
                    "version": tag,
                    "asset_url": asset_url,
                    "asset_api_url": asset_api_url,
                    "asset_name": asset_name,
                    "sums_url": sums_url,
                    "sums_api_url": sums_api_url,
                    "body": body,
                    "html_url": data.get("html_url", ""),
                })
            else:
                callback(None)

        except Exception:
            # LOG-001 / LOG-002: logi w %APPDATA%\KalkulatorPrawniczy\logs\,
            # z usuniętymi tokenami — nie obok EXE i bez wrażliwych danych.
            try:
                log_dir = os.path.join(_katalog_appdata(), "logs")
                os.makedirs(log_dir, exist_ok=True)
                log_path = os.path.join(log_dir, "updater_error.log")
                tb = _sanitize_traceback(traceback.format_exc())
                with open(log_path, "w", encoding="utf-8") as lf:
                    lf.write(f"APP_VERSION: {APP_VERSION}\n")
                    lf.write(f"REPO: {GITHUB_REPO}\n")
                    lf.write(tb)
            except Exception:
                pass
            callback(None)

    threading.Thread(target=_worker, daemon=True).start()


def sprawdz_wersje_automatycznie(callback):
    """
    Sprawdza aktualizacje przy starcie aplikacji — maksymalnie raz dziennie.

    Jeśli plik znacznika w %APPDATA%\\KalkulatorPrawniczy\\last_update_check
    zawiera dzisiejszą datę, kończy się natychmiast wywołując callback(None)
    bez żadnego ruchu sieciowego.

    Wywołaj przy uruchomieniu programu (nie pod przyciskiem):
        sprawdz_wersje_automatycznie(moj_callback)
    """
    if not _czy_sprawdzac_dzisiaj():
        callback(None)
        return
    _sprawdz_wersje_wykonaj(callback)


def sprawdz_wersje_w_tle(callback):
    """
    Sprawdza aktualizacje natychmiast — zawsze, bez względu na datę
    ostatniego sprawdzenia.

    Przeznaczona wyłącznie do wywołania gdy użytkownik ręcznie klika
    przycisk sprawdzenia wersji. Nie blokuje się na pliku znacznika.

    Wywołaj po kliknięciu przycisku:
        sprawdz_wersje_w_tle(moj_callback)
    """
    _sprawdz_wersje_wykonaj(callback)


# ── Okno dialogowe aktualizacji ───────────────────────────────────────────────
class OknoAktualizacji(tk.Toplevel):
    """
    Dialog wyświetlany gdy dostępna jest nowa wersja.
    Pobiera asset (ZIP lub EXE) z paskiem postępu i uruchamia instalację.
    """

    def __init__(self, master, info: dict):
        super().__init__(master)
        self.master_app = master
        self.info = info
        self.title("Dostępna aktualizacja")
        self.geometry("560x460")
        self.resizable(False, False)
        self.configure(bg=BG)
        self.grab_set()
        self._anuluj = False
        self._build()

    def _build(self):
        # ── Nagłówek ──────────────────────────────────────────────────────────
        hdr = tk.Frame(self, bg=BG)
        hdr.pack(fill="x", pady=(18, 8))
        tk.Label(hdr, text="🔄  Dostępna nowa wersja",
                 font=("Segoe UI", 14, "bold"),
                 bg=BG, fg=GOLD).pack()
        tk.Label(hdr,
                 text=f"Aktualna: v{APP_VERSION}   →   Nowa: v{self.info['version']}",
                 font=("Segoe UI", 11),
                 bg=BG, fg="#aaaaaa").pack(pady=(4, 0))

        tk.Frame(self, bg=GOLD, height=2).pack(fill="x", pady=8)

        # ── Changelog ─────────────────────────────────────────────────────────
        tk.Label(self, text="Co nowego:", font=("Segoe UI", 10, "bold"),
                 bg=BG, fg="#cccccc", anchor="w").pack(fill="x", padx=20, pady=(4, 2))

        log_frame = tk.Frame(self, bg=BG)
        log_frame.pack(fill="both", expand=True, padx=20, pady=(0, 8))

        log_text = tk.Text(log_frame, height=8, wrap="word",
                           font=("Segoe UI", 9),
                           bg="#0d1117", fg="#c9d1d9",
                           relief="flat", bd=0,
                           highlightthickness=1, highlightbackground="#333355")
        log_vsb = ttk.Scrollbar(log_frame, orient="vertical", command=log_text.yview)
        log_text.configure(yscrollcommand=log_vsb.set)
        log_vsb.pack(side="right", fill="y")
        log_text.pack(side="left", fill="both", expand=True)

        body = self.info.get("body") or "(brak opisu)"
        log_text.insert("1.0", body)
        log_text.configure(state="disabled")

        # ── Pasek postępu ─────────────────────────────────────────────────────
        prog_frame = tk.Frame(self, bg=BG)
        prog_frame.pack(fill="x", padx=20, pady=(4, 2))

        self.lbl_status = tk.Label(prog_frame, text="",
                                   font=("Segoe UI", 9),
                                   bg=BG, fg="#aaaaaa", anchor="w")
        self.lbl_status.pack(fill="x")

        self.progress = ttk.Progressbar(prog_frame, mode="determinate",
                                        maximum=100, value=0)
        self.progress.pack(fill="x", pady=(2, 0))
        style_p = ttk.Style(self)
        style_p.configure("gold.Horizontal.TProgressbar",
                          troughcolor="#2d2d4a",
                          background=GOLD,
                          thickness=14)
        self.progress.configure(style="gold.Horizontal.TProgressbar")

        # ── Przyciski ─────────────────────────────────────────────────────────
        btn_frame = tk.Frame(self, bg=BG)
        btn_frame.pack(fill="x", padx=20, pady=12)

        self.btn_install = tk.Button(
            btn_frame,
            text="⬇  Pobierz i zainstaluj",
            font=("Segoe UI", 11, "bold"),
            bg=GOLD, fg=TEXT, relief="flat",
            padx=20, pady=8, cursor="hand2",
            activebackground="#e8c97a",
            command=self._pobierz)
        self.btn_install.pack(side="left", expand=True, padx=(0, 6))

        self.btn_cancel = tk.Button(
            btn_frame,
            text="✖  Pomiń tę wersję",
            font=("Segoe UI", 10),
            bg="#3a3a5a", fg="#cccccc", relief="flat",
            padx=12, pady=8, cursor="hand2",
            activebackground="#555577",
            command=self._pominij)
        self.btn_cancel.pack(side="left", expand=True, padx=(6, 0))

        if not self.info.get("asset_url"):
            self.btn_install.configure(
                text="🌐  Otwórz stronę wydania",
                command=self._otworz_www)

    def _otworz_www(self):
        import webbrowser
        webbrowser.open(self.info.get("html_url",
                        f"https://github.com/{GITHUB_REPO}/releases"))
        self.destroy()

    def _pominij(self):
        self._anuluj = True
        self.destroy()

    def _pobierz(self):
        asset_url = self.info.get("asset_url")
        if not asset_url:
            self._otworz_www()
            return

        self.btn_install.configure(state="disabled", text="⏳ Pobieranie...")
        self.btn_cancel.configure(state="disabled")

        def _worker():
            tmp_file = None
            try:
                self._set_status("Łączenie z serwerem…", 0)

                # ── REDIR-002: walidacja URL assetów przed pobraniem ──────────
                download_url = _resolve_download_url(
                    self.info, "asset_api_url", "asset_url")

                _parsed = urllib.parse.urlparse(download_url)
                if _parsed.scheme != "https":
                    raise ValueError(
                        f"Adres URL aktualizacji nie używa HTTPS: {download_url!r}\n"
                        "Instalacja przerwana ze względów bezpieczeństwa.")
                if _parsed.netloc not in _GITHUB_ALLOWED_HOSTS:
                    raise ValueError(
                        f"Adres URL aktualizacji wskazuje na niedozwoloną domenę: "
                        f"{_parsed.netloc!r}\n"
                        "Instalacja przerwana ze względów bezpieczeństwa.\n"
                        "Pobierz aktualizację ręcznie ze strony projektu.")
                # ── koniec REDIR-002 ──────────────────────────────────────────

                # Bezpieczne tworzenie pliku tymczasowego (zastępuje mktemp)
                suffix = os.path.splitext(self.info.get("asset_name", ".zip"))[1] or ".zip"
                tmp_fd = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
                tmp = tmp_fd.name
                tmp_file = tmp

                headers = {"User-Agent": _USER_AGENT,
                           "Accept": "application/octet-stream"}
                if GITHUB_TOKEN:
                    headers["Authorization"] = f"token {GITHUB_TOKEN}"

                # ── REDIR-001: używamy _SecureRedirectHandler ─────────────────
                opener = urllib.request.build_opener(_SecureRedirectHandler)
                req = urllib.request.Request(download_url, headers=headers)

                with opener.open(req, timeout=120) as resp:
                    total = int(resp.headers.get("Content-Length", 0))
                    pobrano = 0
                    chunk = 1024 * 64   # 64 KB

                    with tmp_fd:
                        while not self._anuluj:
                            buf = resp.read(chunk)
                            if not buf:
                                break
                            tmp_fd.write(buf)
                            pobrano += len(buf)
                            if total:
                                pct = int(pobrano / total * 85)
                                self._set_status(
                                    f"Pobieranie… {pobrano//1024} KB / {total//1024} KB",
                                    pct)

                if self._anuluj:
                    try:
                        os.remove(tmp)
                    except Exception:
                        pass
                    return

                # ── Weryfikacja SHA-256 ────────────────────────────────────────
                sums_download = _resolve_download_url(
                    self.info, "sums_api_url", "sums_url")

                # SHA-002: brak pliku SHA256SUMS = przerwanie instalacji
                if not sums_download:
                    raise ValueError(
                        "Repozytorium nie zawiera pliku SHA256SUMS.\n"
                        "Instalacja przerwana ze względów bezpieczeństwa.\n"
                        "Pobierz aktualizację ręcznie ze strony projektu.")

                self._set_status("Weryfikacja integralności pliku…", 88)
                sums_headers = {"User-Agent": _USER_AGENT,
                                "Accept": "application/octet-stream"}
                if GITHUB_TOKEN:
                    sums_headers["Authorization"] = f"token {GITHUB_TOKEN}"

                req_sums = urllib.request.Request(sums_download,
                                                  headers=sums_headers)
                with opener.open(req_sums, timeout=15) as r:
                    # utf-8-sig automatycznie usuwa BOM (\ufeff) jeśli obecny
                    sums_content = r.read().decode("utf-8-sig")

                asset_name = self.info.get("asset_name", "").strip()
                # SHA-001: normalizujemy nazwę do samej nazwy pliku (bez ścieżki)
                baza_nazwy = os.path.basename(asset_name).lower()
                oczekiwany = ""

                def _sha_basename(s: str) -> str:
                    """
                    Wyciąga samą nazwę pliku z tokenu SHA256SUMS niezależnie od formatu:
                      - lstrip usuwa prefiksy: *, ., /
                      - replace normalizuje Windows backslash → forward slash
                      - os.path.basename daje ostatni segment ścieżki
                    Obsługuje: sha256sum, GoReleaser, CertUtil, ścieżki Windows/Unix.
                    """
                    return os.path.basename(s.lower().lstrip("*./").replace("\\", "/"))

                for linia in sums_content.splitlines():
                    linia = linia.strip()
                    if not linia or linia.startswith("#"):
                        continue
                    parts = linia.split()
                    if len(parts) < 2:
                        continue

                    # Format normalny: HASH  [*]nazwa  lub  HASH  ./nazwa  lub  HASH  .\nazwa
                    # SHA-001: _sha_basename + == zamiast 'in'
                    tail = _sha_basename(parts[-1])
                    if tail == baza_nazwy:
                        h = parts[0].lower().strip(":")
                        if len(h) == 64 and all(c in "0123456789abcdef" for c in h):
                            oczekiwany = h
                            break

                    # Format odwrotny: nazwa: HASH  lub  nazwa = HASH
                    # SHA-001: _sha_basename + == zamiast 'in'
                    head = _sha_basename(parts[0].rstrip(":="))
                    if head == baza_nazwy:
                        h = parts[-1].lower()
                        if len(h) == 64 and all(c in "0123456789abcdef" for c in h):
                            oczekiwany = h
                            break

                # SHA-002: brak wpisu dla pliku = przerwanie instalacji
                if not oczekiwany:
                    raise ValueError(
                        f"Plik SHA256SUMS nie zawiera wpisu dla: {asset_name!r}\n"
                        "Instalacja przerwana ze względów bezpieczeństwa.\n"
                        "Pobierz aktualizację ręcznie ze strony projektu.")

                sha = hashlib.sha256()
                with open(tmp, "rb") as f:
                    for blok in iter(lambda: f.read(65536), b""):
                        sha.update(blok)
                if sha.hexdigest().lower() != oczekiwany:
                    raise ValueError(
                        "Weryfikacja integralności pliku nie powiodła się.\n"
                        "Plik może być uszkodzony lub zmodyfikowany.\n"
                        "Aktualizacja została anulowana dla Twojego bezpieczeństwa.")

                self._set_status("Przygotowanie instalacji…", 92)

                exe_path = os.path.abspath(sys.executable)
                if "python" in os.path.basename(exe_path).lower():
                    self._instaluj_skrypt(tmp)
                else:
                    self._instaluj_exe(tmp, exe_path)

            except Exception as ex:
                if tmp_file:
                    try:
                        os.remove(tmp_file)
                    except Exception:
                        pass
                self.after(0, lambda: messagebox.showerror(
                    "Błąd pobierania",
                    f"Nie udało się pobrać aktualizacji:\n{ex}\n\n"
                    f"Pobierz ręcznie ze strony:\n{self.info.get('html_url', '')}",
                    parent=self))
                self.after(0, lambda: self.btn_install.configure(
                    state="normal", text="⬇  Spróbuj ponownie"))
                self.after(0, lambda: self.btn_cancel.configure(state="normal"))

        threading.Thread(target=_worker, daemon=False).start()

    # BAT-001: blocklist znaków niebezpiecznych w ścieżkach wstrzykiwanych do BAT.
    # Wszystkie ścieżki w skrypcie BAT są ujęte w cudzysłów ("path"), więc
    # jedynymi znakami mogącymi przerwać kontekst lub wstrzyknąć polecenie są:
    #   "  — zamknięcie cudzysłowu (bezpośrednie wyjście z kontekstu)
    #   %  — rozwijanie zmiennych środowiskowych (%VAR%) przez CMD *przed*
    #        przetwarzaniem cudzysłowów — jedyny faktycznie niebezpieczny
    #        operator wewnątrz cudzysłowu
    #   znaki kontrolne (0x00–0x1F)
    # UWAGA: & | < > ; ^ ( ) są niebezpieczne tylko POZA cudzysłowem.
    # Wewnątrz "ścieżki" nie mają specjalnego znaczenia w CMD.exe, więc
    # nie blokujemy ich — w przeciwnym razie ścieżki z nawiasami
    # (np. "C:\Users\Jan (Admin)\AppData\Local\Temp\...") byłyby fałszywie
    # odrzucane i aktualizacja nie mogłaby się zainstalować.
    # Polskie litery, spacje i inne znaki Unicode są dozwolone — CMD.exe obsługuje
    # ścieżki Unicode w cudzysłowach poprawnie (Windows Vista+).
    _RE_NIEBEZPIECZNE_BAT = re.compile(r'[\x00-\x1f"%]')

    @staticmethod
    def _waliduj_sciezke_bat(nazwa: str, wartosc: str) -> None:
        """
        BAT-001: Rzuca ValueError jeśli ścieżka zawiera znaki specjalne CMD.
        Wywołaj przed każdą zmienną interpolowaną do skryptu BAT.
        """
        if wartosc and OknoAktualizacji._RE_NIEBEZPIECZNE_BAT.search(wartosc):
            raise ValueError(
                f"Ścieżka '{nazwa}' zawiera niedozwolone znaki i nie może być\n"
                f"użyta w instalatorze: {wartosc!r}\n"
                "Instalacja przerwana ze względów bezpieczeństwa.")

    def _instaluj_exe(self, tmp_path: str, exe_path: str):
        """Podmienia EXE przez zewnętrzny skrypt BAT (Windows).
        Używa cmd.exe — działa niezależnie od tego czy Python jest w PATH."""
        self._set_status("Instalowanie…", 96)

        target      = exe_path
        target_dir  = os.path.dirname(target)
        target_name = os.path.basename(target)
        backup      = os.path.join(target_dir, target_name + ".bak")

        # LOG-001: log instalatora w %APPDATA%\KalkulatorPrawniczy\logs\
        #          zamiast obok EXE (który może być w Program Files dostępnym dla wielu)
        log_path = os.path.join(_katalog_appdata(), "logs", "updater_install.log")
        os.makedirs(os.path.dirname(log_path), exist_ok=True)

        if tmp_path.lower().endswith(".zip"):
            extract_dir = tempfile.mkdtemp()
            # ZIP-001: bezpieczna ekstrakcja zamiast z.extractall()
            _bezpieczna_ekstrakcja(tmp_path, extract_dir)
            # Szukaj EXE o tej samej nazwie co uruchomiony program
            new_exe = None
            for root, _dirs, files in os.walk(extract_dir):
                for fname in files:
                    if fname.lower() == target_name.lower():
                        new_exe = os.path.join(root, fname)
                        break
                if new_exe:
                    break
            # Fallback: dowolny .exe
            if not new_exe:
                for root, _dirs, files in os.walk(extract_dir):
                    for fname in files:
                        if fname.lower().endswith(".exe"):
                            new_exe = os.path.join(root, fname)
                            break
                    if new_exe:
                        break
            if not new_exe:
                raise FileNotFoundError("Nie znaleziono pliku EXE w archiwum ZIP.")
            install_dir = os.path.dirname(new_exe)  # folder z EXE i _internal
        else:
            install_dir = None

        # BAT-001: walidacja wszystkich ścieżek przed interpolacją do BAT
        for _nazwa, _wartosc in [
            ("target",      target),
            ("target_dir",  target_dir),
            ("backup",      backup),
            ("log_path",    log_path),
            ("tmp_path",    tmp_path),
            ("install_dir", install_dir or ""),
        ]:
            self._waliduj_sciezke_bat(_nazwa, _wartosc)

        # RACE-001: losowa nazwa pliku BAT zamiast przewidywalnej (PID-based)
        helper_path = os.path.join(tempfile.gettempdir(),
                                   f"kp_{secrets.token_hex(16)}.bat")

        if install_dir:
            bat = (
                "@echo off\n"
                f"echo === Helper BAT start === > \"{log_path}\"\n"
                f"echo target:      {target} >> \"{log_path}\"\n"
                f"echo install_dir: {install_dir} >> \"{log_path}\"\n"
                "\n"
                ":: Czekaj az aplikacja sie zamknie\n"
                "timeout /t 4 /nobreak >nul\n"
                "\n"
                ":: Zdejmij atrybut ukrycia z plikow zrodlowych\n"
                f"attrib -h -r -s /s /d \"{install_dir}\" >nul 2>&1\n"
                "\n"
                ":: Kopia zapasowa EXE\n"
                f"copy /y \"{target}\" \"{backup}\" >> \"{log_path}\" 2>&1\n"
                "\n"
                ":: Kopiuj caly katalog (EXE + _internal + pozostale pliki)\n"
                f"echo Kopiowanie... >> \"{log_path}\"\n"
                f"xcopy /e /y /h /i /q \"{install_dir}\\*\" \"{target_dir}\\\" >> \"{log_path}\" 2>&1\n"
                "if errorlevel 1 (\n"
                f"    echo BLAD xcopy - przywracam backup >> \"{log_path}\"\n"
                f"    copy /y \"{backup}\" \"{target}\" >> \"{log_path}\" 2>&1\n"
                "    goto CLEANUP\n"
                ")\n"
                f"echo Kopiowanie OK >> \"{log_path}\"\n"
                "\n"
                ":: Uruchom nowy EXE\n"
                f"echo Uruchamiam: {target} >> \"{log_path}\"\n"
                f"start \"\" \"{target}\"\n"
                "\n"
                ":CLEANUP\n"
                "timeout /t 2 /nobreak >nul\n"
                f"if exist \"{tmp_path}\" del /f /q \"{tmp_path}\"\n"
                f"echo Helper koniec >> \"{log_path}\"\n"
                "del /f /q \"%~f0\"\n"
            )
        else:
            bat = (
                "@echo off\n"
                f"echo === Helper BAT start (single EXE) === > \"{log_path}\"\n"
                "timeout /t 4 /nobreak >nul\n"
                f"copy /y \"{target}\" \"{backup}\" >> \"{log_path}\" 2>&1\n"
                f"copy /y \"{tmp_path}\" \"{target}\" >> \"{log_path}\" 2>&1\n"
                "if errorlevel 1 (\n"
                f"    echo BLAD copy >> \"{log_path}\"\n"
                f"    copy /y \"{backup}\" \"{target}\" >> \"{log_path}\" 2>&1\n"
                "    goto CLEANUP\n"
                ")\n"
                f"start \"\" \"{target}\"\n"
                ":CLEANUP\n"
                "timeout /t 2 /nobreak >nul\n"
                f"if exist \"{tmp_path}\" del /f /q \"{tmp_path}\"\n"
                f"echo Helper koniec >> \"{log_path}\"\n"
                "del /f /q \"%~f0\"\n"
            )

        with open(helper_path, "w", encoding="cp1250") as f:
            f.write(bat)

        # RACE-001: ogranicz ACL pliku BAT do bieżącego użytkownika zaraz po zapisie.
        # Zapobiega podmianie przez inny proces w oknie między zapisem a uruchomieniem.
        # icacls dostępne na Windows Vista+; ignorujemy błąd na starszych systemach.
        try:
            import getpass
            subprocess.run(
                ["icacls", helper_path,
                 "/inheritance:r",
                 "/grant:r", f"{getpass.getuser()}:F"],
                check=True, capture_output=True, timeout=5)
        except Exception:
            pass  # Niepowodzenie icacls nie blokuje instalacji

        self._set_status("Uruchamianie instalatora…", 99)

        # Uruchom BAT przez cmd.exe z CREATE_NEW_CONSOLE zamiast DETACHED,
        # bo DETACHED bez konsoli na niektórych Windows 10/11 blokuje cmd.exe.
        # SW_HIDE = 0 ukrywa okno mimo CREATE_NEW_CONSOLE.
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = 0  # SW_HIDE

        proc = subprocess.Popen(
            ["cmd.exe", "/c", helper_path],
            cwd=target_dir,
            creationflags=0x00000010,   # CREATE_NEW_CONSOLE
            startupinfo=si,
            close_fds=True)

        # Upewnij się że proces ruszył zanim zamkniemy aplikację
        import time as _time
        _time.sleep(0.5)
        if proc.poll() is not None:
            # BAT zakończył się natychmiast — coś poszło nie tak
            raise RuntimeError(
                f"Helper BAT zakończył się natychmiast (kod {proc.returncode}).\n"
                f"Szczegóły: {log_path}")

        self.after(1500, self._zakoncz_i_zamknij)

    def _instaluj_skrypt(self, tmp_path: str):
        """Podmienia main.py (tryb skryptowy)."""
        self._set_status("Instalowanie…", 96)
        # Używamy main.py z katalogu projektu, nie __file__ (który wskazuje na updater.py)
        script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")

        if tmp_path.lower().endswith(".zip"):
            extract_dir = tempfile.mkdtemp()
            # ZIP-001: bezpieczna ekstrakcja zamiast z.extractall()
            _bezpieczna_ekstrakcja(tmp_path, extract_dir)
            new_script = None
            for root, _, files in os.walk(extract_dir):
                for f in files:
                    if f == "main.py":
                        new_script = os.path.join(root, f)
                        break
                if new_script:
                    break
            if not new_script:
                raise FileNotFoundError("Nie znaleziono main.py w archiwum.")
            install_src = new_script
        else:
            install_src = tmp_path

        backup = script_path + ".bak"
        shutil.copy2(script_path, backup)
        shutil.copy2(install_src, script_path)

        self._set_status("Zainstalowano! Uruchamiam ponownie…", 100)
        self.after(800, self._restart_skrypt)

    def _restart_skrypt(self):
        """Restartuje skrypt Python."""
        main_py = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
        subprocess.Popen([sys.executable, main_py])
        self.master_app.quit()

    def _zakoncz_i_zamknij(self):
        """Zamyka aplikację — helper uruchomi nowy EXE."""
        self.master_app.quit()

    def _set_status(self, tekst: str, pct: int):
        self.after(0, lambda t=tekst, p=pct: (
            self.lbl_status.configure(text=t),
            self.progress.configure(value=p)
        ))
