"""
updater.py — Moduł aktualizacji: sprawdzanie wersji przez GitHub API,
             pobieranie, weryfikacja SHA-256 i instalacja nowej wersji.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import os
import sys
import json
import threading
import urllib.request
import urllib.error
import tempfile
import hashlib
import shutil
import zipfile
import subprocess
import re

from config import APP_VERSION, GITHUB_REPO, GITHUB_TOKEN

# URL do GitHub Releases API
_GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


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


def sprawdz_wersje_w_tle(callback):
    """
    Sprawdza GitHub API w watku tla.
    Wywoluje callback(info) gdy jest nowa wersja, lub callback(None) gdy blad / brak.
    """
    def _worker():
        try:
            req = urllib.request.Request(
                _GITHUB_API_URL,
                headers={"User-Agent": "KalkulatorPrawniczy-Updater/1.0",
                         "Accept": "application/vnd.github.v3+json",
                         **( {"Authorization": f"token {GITHUB_TOKEN}"}
                             if GITHUB_TOKEN else {} )},
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))

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
            # Zapisz blad do pliku obok EXE - pomocne przy diagnozie
            try:
                import traceback
                log_dir = os.path.dirname(os.path.abspath(sys.executable))
                with open(os.path.join(log_dir, "updater_error.log"), "w", encoding="utf-8") as lf:
                    lf.write(f"APP_VERSION: {APP_VERSION}\n")
                    lf.write(f"API_URL: {_GITHUB_API_URL}\n")
                    lf.write(traceback.format_exc())
            except Exception:
                pass
            callback(None)

    t = threading.Thread(target=_worker, daemon=True)
    t.start()


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
        self.configure(bg="#1a1a2e")
        self.grab_set()
        self._anuluj = False
        self._build()

    def _build(self):
        BG_D   = "#1a1a2e"
        GOLD_D = "#c9a84c"
        TEXT_D = "#1a1a2e"

        # ── Nagłówek ──────────────────────────────────────────────────────────
        hdr = tk.Frame(self, bg=BG_D)
        hdr.pack(fill="x", pady=(18, 8))
        tk.Label(hdr, text="🔄  Dostępna nowa wersja",
                 font=("Segoe UI", 14, "bold"),
                 bg=BG_D, fg=GOLD_D).pack()
        tk.Label(hdr,
                 text=f"Aktualna: v{APP_VERSION}   →   Nowa: v{self.info['version']}",
                 font=("Segoe UI", 11),
                 bg=BG_D, fg="#aaaaaa").pack(pady=(4, 0))

        tk.Frame(self, bg=GOLD_D, height=2).pack(fill="x", pady=8)

        # ── Changelog ─────────────────────────────────────────────────────────
        tk.Label(self, text="Co nowego:", font=("Segoe UI", 10, "bold"),
                 bg=BG_D, fg="#cccccc", anchor="w").pack(fill="x", padx=20, pady=(4, 2))

        log_frame = tk.Frame(self, bg=BG_D)
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
        prog_frame = tk.Frame(self, bg=BG_D)
        prog_frame.pack(fill="x", padx=20, pady=(4, 2))

        self.lbl_status = tk.Label(prog_frame, text="",
                                   font=("Segoe UI", 9),
                                   bg=BG_D, fg="#aaaaaa", anchor="w")
        self.lbl_status.pack(fill="x")

        self.progress = ttk.Progressbar(prog_frame, mode="determinate",
                                        maximum=100, value=0)
        self.progress.pack(fill="x", pady=(2, 0))
        style_p = ttk.Style(self)
        style_p.configure("gold.Horizontal.TProgressbar",
                          troughcolor="#2d2d4a",
                          background=GOLD_D,
                          thickness=14)
        self.progress.configure(style="gold.Horizontal.TProgressbar")

        # ── Przyciski ─────────────────────────────────────────────────────────
        btn_frame = tk.Frame(self, bg=BG_D)
        btn_frame.pack(fill="x", padx=20, pady=12)

        self.btn_install = tk.Button(
            btn_frame,
            text="⬇  Pobierz i zainstaluj",
            font=("Segoe UI", 11, "bold"),
            bg=GOLD_D, fg=TEXT_D, relief="flat",
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

                # Bezpieczne tworzenie pliku tymczasowego (zastępuje mktemp)
                suffix = os.path.splitext(self.info.get("asset_name", ".zip"))[1] or ".zip"
                tmp_fd = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
                tmp = tmp_fd.name
                tmp_file = tmp

                download_url = (self.info.get("asset_api_url")
                                if GITHUB_TOKEN
                                else self.info.get("asset_url"))
                if not download_url:
                    download_url = self.info.get("asset_url") or \
                                   self.info.get("asset_api_url")

                headers = {"User-Agent": "KalkulatorPrawniczy-Updater/1.0",
                           "Accept": "application/octet-stream"}
                if GITHUB_TOKEN:
                    headers["Authorization"] = f"token {GITHUB_TOKEN}"

                class _TokenRedirectHandler(urllib.request.HTTPRedirectHandler):
                    def redirect_request(self, req, fp, h, code, msg, newurl):
                        new_req = urllib.request.Request(
                            newurl,
                            headers={"User-Agent": req.get_header("User-agent"),
                                     "Accept": "application/octet-stream"})
                        return new_req

                opener = urllib.request.build_opener(_TokenRedirectHandler)
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
                sums_download = (self.info.get("sums_api_url")
                                 if GITHUB_TOKEN else self.info.get("sums_url"))
                if not sums_download:
                    sums_download = self.info.get("sums_url") or \
                                    self.info.get("sums_api_url")

                if sums_download:
                    self._set_status("Weryfikacja integralności pliku…", 88)
                    sums_headers = {"User-Agent": "KalkulatorPrawniczy-Updater/1.0",
                                    "Accept": "application/octet-stream"}
                    if GITHUB_TOKEN:
                        sums_headers["Authorization"] = f"token {GITHUB_TOKEN}"
                    req_sums = urllib.request.Request(sums_download,
                                                      headers=sums_headers)
                    with opener.open(req_sums, timeout=15) as r:
                        sums_content = r.read().decode("utf-8")

                    asset_name = self.info.get("asset_name", "")
                    baza_nazwy = asset_name.lower()
                    oczekiwany = ""
                    for linia in sums_content.splitlines():
                        linia = linia.strip()
                        if not linia or linia.startswith("#"):
                            continue
                        parts = linia.split()
                        if len(parts) < 2:
                            continue
                        # Format normalny: HASH  [*]nazwa
                        tail = parts[-1].lower().lstrip("*./")
                        if baza_nazwy in tail:
                            h = parts[0].lower().strip(":")
                            if len(h) == 64 and all(c in "0123456789abcdef" for c in h):
                                oczekiwany = h
                                break
                        # Format odwrotny: nazwa: HASH
                        head = parts[0].lower().rstrip(":")
                        if baza_nazwy in head:
                            h = parts[-1].lower()
                            if len(h) == 64 and all(c in "0123456789abcdef" for c in h):
                                oczekiwany = h
                                break

                    if oczekiwany:
                        sha = hashlib.sha256()
                        with open(tmp, "rb") as f:
                            for blok in iter(lambda: f.read(65536), b""):
                                sha.update(blok)
                        if sha.hexdigest().lower() != oczekiwany:
                            raise ValueError(
                                "Weryfikacja integralności pliku nie powiodła się.\n"
                                "Plik może być uszkodzony lub zmodyfikowany.\n"
                                "Aktualizacja została anulowana dla Twojego bezpieczeństwa.")
                    else:
                        self._set_status(
                            "⚠ Brak wpisu SHA256 dla tego pliku — kontynuuję…", 88)
                else:
                    self._set_status(
                        "⚠ Brak pliku SHA256SUMS w release — pomijam weryfikację…", 88)

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

    def _instaluj_exe(self, tmp_path: str, exe_path: str):
        """Podmienia EXE przez zewnętrzny skrypt BAT (Windows).
        Używa cmd.exe — działa niezależnie od tego czy Python jest w PATH."""
        self._set_status("Instalowanie…", 96)

        target      = exe_path
        target_dir  = os.path.dirname(target)
        target_name = os.path.basename(target)
        backup      = os.path.join(target_dir, target_name + ".bak")
        log_path    = os.path.join(target_dir, "updater_install.log")

        if tmp_path.lower().endswith(".zip"):
            extract_dir = tempfile.mkdtemp()
            with zipfile.ZipFile(tmp_path, "r") as z:
                z.extractall(extract_dir)
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

        helper_path = os.path.join(tempfile.gettempdir(),
                                   f"kp_helper_{os.getpid()}.bat")

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
            raise RuntimeError(f"Helper BAT zakończył się natychmiast (kod {proc.returncode}). "
                               f"Sprawdź {target_dir}\\updater_install.log")

        self.after(1500, self._zakoncz_i_zamknij)

    def _instaluj_skrypt(self, tmp_path: str):
        """Podmienia main.py (tryb skryptowy)."""
        self._set_status("Instalowanie…", 96)
        # Używamy main.py z katalogu projektu, nie __file__ (który wskazuje na updater.py)
        script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")

        if tmp_path.lower().endswith(".zip"):
            extract_dir = tempfile.mkdtemp()
            with zipfile.ZipFile(tmp_path, "r") as z:
                z.extractall(extract_dir)
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
