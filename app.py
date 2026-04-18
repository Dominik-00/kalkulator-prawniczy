"""
app.py — Główna klasa aplikacji App (tk.Tk) z wszystkimi zakładkami:
         Koszty, Raty, PKK, Opłata roczna, Daty, Spadki.
"""

import tkinter as tk
from tkinter import ttk, messagebox, font, filedialog
from datetime import datetime, date
import sys
import os
import json
import tempfile
import subprocess

from config import APP_VERSION, GITHUB_REPO, GITHUB_TOKEN
from constants import (BG, PANEL, CREAM, GOLD, GOLD_LT, TEXT, MUTED, RED, GREEN,
                       BORDER, HEADER_H, fmt, safe_float, safe_int,
                       oplata_sadowa, wynagrodzenie_pelnomocnika)
from updater import sprawdz_wersje_w_tle, OknoAktualizacji, _GITHUB_API_URL, _ver_tuple
from inheritance import (Osoba, BazaDanych, SilnikDziedziczenia,
                         DrzewoGenealogiczne, DialogOsoby,
                         _generuj_pdf_spadki, _sp_fmt_date)
from abuzywny import TabAbuzywny
from tab_koszty import TabKoszty
from tab_raty import TabRaty
from tab_pkk import TabPKK
from tab_oplata_roczna import TabOplataRoczna
from tab_daty import TabDaty
from tab_przedawnienie import TabPrzedawnienie

# ── Główna aplikacja ─────────────────────────────────────────────────────────
class App(tk.Tk):
    _RODZAJ_MAP = {0: "cywilna", 1: "gospodarcza", 2: "pracownicza", 3: "upominawcze"}

    def __init__(self):
        super().__init__()
        self.title(f"Kalkulator Prawniczy  v{APP_VERSION}")
        self.geometry("1365x1015")
        self.minsize(1066, 780)
        self.configure(bg=BG)
        self.resizable(True, True)
        self.state("zoomed")

        self._setup_fonts()
        self._build_header()
        self._build_tabs()

        self.after(3000, self._sprawdz_aktualizacje)

    def _setup_fonts(self):
        self.f_title  = font.Font(family="Georgia", size=18, weight="bold")
        self.f_sub    = font.Font(family="Georgia", size=13, weight="bold")
        self.f_body   = font.Font(family="Segoe UI", size=10)
        self.f_bold   = font.Font(family="Segoe UI", size=10, weight="bold")
        self.f_small  = font.Font(family="Segoe UI", size=9)
        self.f_small_bold = font.Font(family="Segoe UI", size=9, weight="bold")
        self.f_result = font.Font(family="Segoe UI", size=12, weight="bold")
        self.f_big    = font.Font(family="Georgia", size=16, weight="bold")

    def _build_header(self):
        hdr = tk.Frame(self, bg=BG, height=HEADER_H)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="⚖  Kalkulator Prawniczy", font=self.f_title,
                 bg=BG, fg=GOLD).pack(side="left", padx=24, pady=12)
        tk.Label(hdr, text="Narzędzia procesowe. Produkcja: ASR Dominik Mieczkowski-Wilga, wykorzystano formuły SSR Michała Legutki.",
                 font=self.f_small, bg=BG, fg="#aaaaaa").pack(side="left", pady=16)

        self.lbl_wersja = tk.Label(hdr, text=f"v{APP_VERSION}",
                                   font=self.f_small, bg=BG, fg="#666688",
                                   cursor="hand2")
        self.lbl_wersja.pack(side="right", padx=(0, 16))
        self.lbl_wersja.bind("<Button-1>",
                             lambda e: self._sprawdz_aktualizacje(reczne=True))

        self.btn_update = tk.Button(
            hdr, text="",
            font=self.f_small, bg=BG, relief="flat",
            fg=GOLD, activeforeground=GOLD_LT,
            activebackground=BG, cursor="hand2",
            command=lambda: self._sprawdz_aktualizacje(reczne=True))
        self._btn_update_info = None
        sep = tk.Frame(self, bg=GOLD, height=3)
        sep.pack(fill="x")

    def _build_tabs(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TNotebook.Tab", background="#2d2d4a", foreground="#aaaaaa",
                        padding=[16, 8], font=("Segoe UI", 10))
        style.map("TNotebook.Tab",
                  background=[("selected", GOLD)],
                  foreground=[("selected", BG)])

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=0, pady=0)
        self._nb = nb
        self._scroll_canvases = {}

        for cls, text in [
            (TabKoszty,        "⚖  Liczenie kosztów"),
            (TabRaty,          "📋  Rozłożenie na raty"),
        ]:
            nb.add(cls(nb, app=self), text=text)
        self._tab_abuzywny(nb)
        for cls, text in [
            (TabPKK,           "🏦  Koszty kredytu (art. 36a)"),
            (TabOplataRoczna,  "📅  Aktualizacja opłaty rocznej"),
            (TabDaty,          "🗓  Kalkulator dat"),
            (TabPrzedawnienie, "⏳  Przedawnienie"),
        ]:
            nb.add(cls(nb, app=self), text=text)
        self._tab_spadki(nb)
        self._setup_global_scroll()

    def _sprawdz_aktualizacje(self, reczne: bool = False):
        if reczne:
            self.lbl_wersja.configure(text=f"v{APP_VERSION} ↻", fg=GOLD_LT)

        def _callback(info):
            if info:
                self._btn_update_info = info
                self.after(0, lambda: self._pokaz_btn_aktualizacji(info))
                if reczne:
                    self.after(100, lambda: OknoAktualizacji(self, info))
                else:
                    self.after(1000, lambda: self._dyskretne_powiadomienie(info))
            else:
                self.after(0, lambda: self.lbl_wersja.configure(
                    text=f"v{APP_VERSION}", fg="#666688"))
                if reczne:
                    self.after(0, lambda: self._dialog_diagnostyczny())

        sprawdz_wersje_w_tle(_callback)

    def _dialog_diagnostyczny(self):
        dlg = tk.Toplevel(self)
        dlg.title("Sprawdzanie aktualizacji — diagnostyka")
        dlg.geometry("580x480")
        dlg.resizable(True, True)
        dlg.configure(bg=BG)
        dlg.grab_set()

        tk.Label(dlg, text="🔍  Diagnostyka aktualizacji",
                 font=self.f_sub, bg=BG, fg=GOLD).pack(pady=(16, 4))
        tk.Frame(dlg, bg=GOLD, height=2).pack(fill="x", padx=16)

        out = tk.Text(dlg, font=("Courier New", 9),
                      bg="#0d1117", fg="#c9d1d9",
                      relief="flat", bd=0, wrap="word",
                      highlightthickness=1, highlightbackground="#333355",
                      padx=10, pady=8)
        vsb = ttk.Scrollbar(dlg, orient="vertical", command=out.yview)
        out.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y", padx=(0, 8), pady=8)
        out.pack(fill="both", expand=True, padx=(16, 0), pady=8)

        def log(tekst, kolor="#c9d1d9"):
            out.configure(state="normal")
            out.insert("end", tekst + "\n")
            out.configure(state="disabled")
            out.see("end")
            dlg.update()

        bf = tk.Frame(dlg, bg=BG)
        bf.pack(fill="x", padx=16, pady=(0, 12))
        tk.Button(bf, text="↻  Sprawdź ponownie",
                  font=self.f_body, bg=GOLD, fg=BG, relief="flat",
                  padx=12, pady=6, cursor="hand2",
                  command=lambda: _uruchom()).pack(side="left", padx=(0, 8))
        tk.Button(bf, text="✖  Zamknij",
                  font=self.f_body, bg="#3a3a5a", fg="#cccccc", relief="flat",
                  padx=12, pady=6, cursor="hand2",
                  command=dlg.destroy).pack(side="left")

        def _uruchom():
            out.configure(state="normal")
            out.delete("1.0", "end")
            out.configure(state="disabled")

            import threading, urllib.request, urllib.error

            def _test():
                log("=" * 52)
                log("  KALKULATOR PRAWNICZY — Test aktualizacji")
                log("=" * 52)
                log(f"\n  Wersja lokalna   : {APP_VERSION}")
                log(f"  GITHUB_REPO      : {GITHUB_REPO}")
                log(f"  URL API          : {_GITHUB_API_URL}")

                if "twoj_login" in GITHUB_REPO:
                    log("\n  ❌ BŁĄD KONFIGURACJI:")
                    log("     GITHUB_REPO zawiera domyślną wartość")
                    log("     'twoj_login/kalkulator-prawniczy'.")
                    log("\n  ➤  ROZWIĄZANIE:")
                    log("     Zmień w main.py:")
                    log(f"     GITHUB_REPO = \"twoj_login/kalkulator-prawniczy\"")
                    log("     na swój login i nazwę repo, np.:")
                    log("     GITHUB_REPO = \"jkowalski/kalkulator-prawniczy\"")
                    log("\n  ⚠  Następnie SKOMPILUJ PONOWNIE EXE przez buduj_exe.bat")
                    log("     Zmiana w main.py nie wystarczy — EXE ma kod 'zamrożony'.")
                    return

                log("\n  [1/3] Test połączenia z internetem...")
                try:
                    req = urllib.request.Request(
                        "https://api.github.com",
                        headers={"User-Agent": "KalkulatorPrawniczy-Updater/1.0"})
                    with urllib.request.urlopen(req, timeout=6) as r:
                        log(f"        ✅ GitHub API dostępne (HTTP {r.status})")
                except urllib.error.URLError as e:
                    log(f"        ❌ Brak połączenia: {e.reason}")
                    log("\n  ➤  ROZWIĄZANIE: Sprawdź połączenie z internetem.")
                    log("     Jeśli jesteś za proxy sądowym — sieć może blokować")
                    log("     połączenia zewnętrzne. Skontaktuj się z IT.")
                    return
                except Exception as e:
                    log(f"        ❌ Błąd: {e}")
                    return

                log(f"\n  [2/3] Test dostępu do repozytorium...")
                log(f"        GET {_GITHUB_API_URL}")
                try:
                    req = urllib.request.Request(
                        _GITHUB_API_URL,
                        headers={"User-Agent": "KalkulatorPrawniczy-Updater/1.0",
                                 "Accept": "application/vnd.github.v3+json",
                                 **( {"Authorization": f"token {GITHUB_TOKEN}"}
                                     if GITHUB_TOKEN else {} )})
                    with urllib.request.urlopen(req, timeout=8) as r:
                        raw = r.read().decode("utf-8")
                        data = json.loads(raw)
                        log(f"        ✅ HTTP {r.status} — odpowiedź otrzymana")
                except urllib.error.HTTPError as e:
                    log(f"        ❌ HTTP {e.code}: {e.reason}")
                    if e.code == 404:
                        log("\n  ➤  ROZWIĄZANIE — możliwe przyczyny:")
                        log(f"     • Nieprawidłowy GITHUB_REPO: '{GITHUB_REPO}'")
                        log("       Sprawdź czy login i nazwa repo są poprawne.")
                        log("     • Repozytorium jest prywatne bez tokenu dostępu.")
                        log("     • Nie ma jeszcze żadnego Release w repozytorium.")
                    elif e.code == 403:
                        log("\n  ➤  ROZWIĄZANIE: Limit zapytań GitHub API (60/h).")
                        log("     Poczekaj chwilę i spróbuj ponownie.")
                    return
                except Exception as e:
                    log(f"        ❌ Błąd: {e}")
                    return

                log(f"\n  [3/3] Analiza odpowiedzi GitHub...")
                tag = data.get("tag_name", "(brak)")
                tag_czysty = tag.lstrip("v")
                published = data.get("published_at", "(brak daty)")[:10]
                assets = data.get("assets", [])

                log(f"        Tag najnowszego release : {tag}")
                log(f"        Data publikacji         : {published}")
                log(f"        Liczba assetów (plików) : {len(assets)}")

                for a in assets:
                    log(f"          • {a.get('name')} "
                        f"({a.get('size',0)//1024} KB)")

                log(f"\n        Wersja lokalna  : {APP_VERSION}  "
                    f"→ tuple {_ver_tuple(APP_VERSION)}")
                log(f"        Wersja z GitHub : {tag_czysty}  "
                    f"→ tuple {_ver_tuple(tag_czysty)}")

                if _ver_tuple(tag_czysty) > _ver_tuple(APP_VERSION):
                    log("\n        ✅ Aktualizacja DOSTĘPNA — powinna się pokazać!")
                    log("           Uruchamiam ponowne sprawdzenie...")
                    dlg.after(500, lambda: (
                        dlg.destroy(),
                        self._sprawdz_aktualizacje(reczne=True)
                    ))
                elif _ver_tuple(tag_czysty) == _ver_tuple(APP_VERSION):
                    log("\n        ℹ  Wersje są IDENTYCZNE — brak aktualizacji.")
                    log(f"           Lokalnie: {APP_VERSION}  |  GitHub: {tag_czysty}")
                    log("\n  ➤  Jeśli właśnie wgrałeś v1.0.1 na GitHub:")
                    log("     • Upewnij się, że EXE został skompilowany")
                    log("       z APP_VERSION = \"1.0.0\" (wersja starsza),")
                    log("       a Release ma tag v1.0.1 (wersja nowsza).")
                    log("     • Obie wartości muszą być RÓŻNE.")
                else:
                    log("\n        ℹ  GitHub ma starszą wersję niż lokalna.")
                    log(f"           Lokalnie: {APP_VERSION}  |  GitHub: {tag_czysty}")

                log("\n" + "=" * 52)

            threading.Thread(target=_test, daemon=True).start()

        _uruchom()

    def _pokaz_btn_aktualizacji(self, info: dict):
        self.btn_update.configure(
            text=f"🔄  Dostępna v{info['version']} — kliknij aby zainstalować")
        self.btn_update.pack(side="right", padx=(0, 8), pady=10)
        self.lbl_wersja.configure(text=f"v{APP_VERSION}", fg="#666688")

    def _dyskretne_powiadomienie(self, info: dict):
        pasek = tk.Frame(self, bg="#2a2a1a", cursor="hand2")
        pasek.pack(side="bottom", fill="x")
        tk.Label(pasek,
                 text=f"  🔄  Dostępna aktualizacja v{info['version']}  —  "
                      f"kliknij tutaj aby pobrać i zainstalować  ✕",
                 font=self.f_small, bg="#2a2a1a", fg=GOLD_LT,
                 cursor="hand2").pack(side="left", pady=6)

        def _otworz(e=None):
            pasek.destroy()
            OknoAktualizacji(self, info)

        def _zamknij(e=None):
            pasek.destroy()

        pasek.bind("<Button-1>", _otworz)
        for w in pasek.winfo_children():
            w.bind("<Button-1>", _otworz)

        btn_x = tk.Label(pasek, text=" ✕ ", font=self.f_small,
                         bg="#3a2a1a", fg="#aaaaaa", cursor="hand2")
        btn_x.pack(side="right", padx=4)
        btn_x.bind("<Button-1>", _zamknij)

    def _scrollable(self, parent):
        canvas = tk.Canvas(parent, bg=CREAM, highlightthickness=0)
        vsb = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        frame = tk.Frame(canvas, bg=CREAM)
        win = canvas.create_window((0, 0), window=frame, anchor="nw")

        def on_configure(e):
            canvas.configure(scrollregion=canvas.bbox("all"))
        frame.bind("<Configure>", on_configure)

        def on_canvas_resize(e):
            canvas.itemconfig(win, width=e.width)
        canvas.bind("<Configure>", on_canvas_resize)

        def _register(e=None):
            try:
                self._scroll_canvases[self._nb.select()] = canvas
            except Exception:
                pass
        canvas.bind("<Map>", _register)

        return frame, canvas


    def _setup_global_scroll(self):
        def _active_canvas():
            try:
                return self._scroll_canvases.get(self._nb.select())
            except Exception:
                return None
        def _is_combobox(w):
            try:
                return w.winfo_class() in ("TCombobox","Combobox","Listbox")
            except Exception:
                return False
        def on_mousewheel(e):
            if _is_combobox(e.widget): return
            c=_active_canvas()
            if c: c.yview_scroll(int(-1*(e.delta/120)),"units")
        def on_scroll_up(e):
            if not _is_combobox(e.widget):
                c=_active_canvas()
                if c: c.yview_scroll(-1,"units")
        def on_scroll_down(e):
            if not _is_combobox(e.widget):
                c=_active_canvas()
                if c: c.yview_scroll(1,"units")
        self.bind_all("<MouseWheel>",on_mousewheel)
        self.bind_all("<Button-4>",on_scroll_up)
        self.bind_all("<Button-5>",on_scroll_down)

    def _card(self, parent, title=None, pady=8):
        outer = tk.Frame(parent, bg=CREAM)
        outer.pack(fill="x", padx=20, pady=(pady, 0))
        card = tk.Frame(outer, bg=PANEL, bd=0,
                        highlightthickness=1, highlightbackground=BORDER)
        card.pack(fill="x")
        if title:
            th = tk.Frame(card, bg=PANEL)
            th.pack(fill="x", padx=16, pady=(12, 4))
            tk.Label(th, text=title.upper(), font=self.f_small,
                     bg=PANEL, fg=GOLD).pack(side="left")
            sep = tk.Frame(card, bg=BORDER, height=1)
            sep.pack(fill="x", padx=16)
        inner = tk.Frame(card, bg=PANEL)
        inner.pack(fill="x", padx=16, pady=12)
        return inner

    def _lbl(self, parent, text, col=0, row=0, sticky="w", span=1):
        tk.Label(parent, text=text, font=self.f_small,
                 bg=PANEL, fg=MUTED).grid(row=row, column=col, columnspan=span,
                                           sticky=sticky, pady=(6, 1))

    def _entry(self, parent, row=0, col=1, width=18, span=1, textvariable=None):
        e = tk.Entry(parent, font=self.f_body, relief="flat", bd=0,
                     bg=CREAM, fg=TEXT, width=width,
                     highlightthickness=1, highlightbackground=BORDER,
                     textvariable=textvariable)
        e.grid(row=row, column=col, columnspan=span, sticky="ew",
               padx=(4, 8), pady=2, ipady=4)
        return e

    def _combo(self, parent, values, row=0, col=1, width=20):
        cb = ttk.Combobox(parent, values=values, state="readonly",
                          font=self.f_body, width=width)
        cb.current(0)
        cb.grid(row=row, column=col, sticky="ew", padx=(4, 8), pady=2, ipady=2)
        return cb

    def _btn(self, parent, text, cmd, gold=False):
        bg = GOLD if gold else BG
        fg = BG  if gold else CREAM
        b = tk.Button(parent, text=text, command=cmd,
                      bg=bg, fg=fg, font=self.f_bold, relief="flat",
                      activebackground=GOLD_LT, activeforeground=BG,
                      cursor="hand2", padx=18, pady=7)
        return b

    def _result_box(self, parent):
        box = tk.Frame(parent, bg=CREAM)
        box.pack(fill="x", padx=20, pady=12)
        inner = tk.Frame(box, bg=BG, bd=0)
        inner.pack(fill="x")
        return inner

    def _res_row(self, parent, label, value, color=None, big=False):
        row = tk.Frame(parent, bg=BG)
        row.pack(fill="x", padx=16, pady=3)
        tk.Label(row, text=label, font=self.f_body,
                 bg=BG, fg="#aaaaaa").pack(side="left")
        fc = color or GOLD_LT
        fnt = self.f_big if big else self.f_result
        tk.Label(row, text=value, font=fnt,
                 bg=BG, fg=fc).pack(side="right")
        tk.Frame(parent, bg="#2d2d4a", height=1).pack(fill="x", padx=16)

    def _clear_frame(self, frame):
        for w in frame.winfo_children():
            w.destroy()

    # ═══════════════════════════════════════════════════════════════════════
    # ZAKŁADKA — POŻYCZKA / ABUZYWNOŚĆ
    # ═══════════════════════════════════════════════════════════════════════
    def _tab_abuzywny(self, nb):
        fonts = {
            "sub":        self.f_sub,
            "body":       self.f_body,
            "bold":       self.f_bold,
            "small":      self.f_small,
            "small_bold": self.f_small_bold,
            "result":     self.f_result,
            "big":        self.f_big,
        }
        tab = TabAbuzywny(nb, fonts=fonts)
        nb.add(tab, text="💳  Pożyczka / Abuzywność BETA")

    # ═══════════════════════════════════════════════════════════════════════
    # ZAKŁADKA — KALKULATOR SPADKOWY
    # ═══════════════════════════════════════════════════════════════════════
    def _tab_spadki(self, nb):
        outer = tk.Frame(nb, bg=CREAM)
        nb.add(outer, text="🏛  Kalkulator spadkowy")

        _fonts = {
            "body": self.f_body, "bold": self.f_bold, "small": self.f_small,
            "small_bold": self.f_small_bold, "sub": self.f_sub,
        }

        sp_baza = BazaDanych()
        sp_wybr = {"id": None}

        toolbar = tk.Frame(outer, bg=BG, pady=5)
        toolbar.pack(fill="x")

        tk.Label(toolbar, text="🏛  Kalkulator spadkowy",
                 font=self.f_sub, bg=BG, fg=GOLD).pack(side="left", padx=16)

        def _tbtn(text, cmd):
            tk.Button(toolbar, text=text, command=cmd,
                      bg=GOLD, fg=BG, font=self.f_bold, relief="flat",
                      padx=12, pady=4, cursor="hand2",
                      activebackground=GOLD_LT, activeforeground=BG
                      ).pack(side="left", padx=4)

        _tbtn("+ Dodaj osobę", lambda: _dodaj_osobe())
        _tbtn("✏ Edytuj", lambda: _edytuj_wybrana())
        _tbtn("🗑 Usuń", lambda: _usun_wybrana())

        tk.Frame(toolbar, bg=GOLD, width=2).pack(side="left", fill="y", padx=6)

        _tbtn("💾 Zapisz bazę", lambda: _zapisz())
        _tbtn("📂 Wczytaj bazę", lambda: _wczytaj())

        def _resetuj():
            if not sp_baza.osoby:
                return
            if not messagebox.askyesno(
                    "Resetuj bazę",
                    "Usunąć wszystkie osoby i zacząć od nowa?\n\nTej operacji nie można cofnąć.",
                    icon="warning"):
                return
            sp_baza.osoby.clear()
            sp_baza.plik = ""
            sp_wybr["id"] = None
            drzewo.reset_pozycji()
            _odswiez()

        tk.Button(toolbar, text="🗑 Resetuj", command=_resetuj,
                  bg="#c0392b", fg="white", font=self.f_bold, relief="flat",
                  padx=12, pady=4, cursor="hand2",
                  activebackground="#e74c3c", activeforeground="white"
                  ).pack(side="left", padx=4)

        tk.Frame(toolbar, bg=GOLD, width=2).pack(side="left", fill="y", padx=6)

        tk.Label(toolbar, text="Spadkodawca:", font=self.f_small,
                 bg=BG, fg="#aaaaaa").pack(side="left", padx=(6, 2))
        sp_combo_var = tk.StringVar()
        sp_combo = ttk.Combobox(toolbar, textvariable=sp_combo_var,
                                values=[], width=26, font=self.f_body,
                                state="readonly")
        sp_combo.pack(side="left", padx=4)

        _tbtn("⚖ Oblicz udziały", lambda: _oblicz())
        _tbtn("📄 Eksport PDF", lambda: _pdf())

        tk.Frame(outer, bg=GOLD, height=2).pack(fill="x")

        main_pane = tk.Frame(outer, bg=CREAM)
        main_pane.pack(fill="both", expand=True)

        left = tk.Frame(main_pane, bg="#eaf2fb", width=240)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)

        tk.Label(left, text="Osoby w bazie", font=self.f_bold,
                 bg="#eaf2fb", fg=TEXT).pack(pady=(8, 2))
        tk.Label(left, text="🔵 M   🩷 K   ⚫ zm.",
                 font=self.f_small, bg="#eaf2fb", fg=MUTED).pack()

        szuk_var = tk.StringVar()
        szuk_entry = tk.Entry(left, textvariable=szuk_var,
                              font=self.f_body, relief="flat", bd=0,
                              bg=CREAM, fg=TEXT,
                              highlightthickness=1, highlightbackground=BORDER)
        szuk_entry.pack(fill="x", padx=8, pady=4, ipady=3)
        tk.Label(left, text="🔍 Szukaj...", font=self.f_small,
                 bg="#eaf2fb", fg=MUTED).place(in_=szuk_entry, x=4, y=2)

        lista_outer = tk.Frame(left, bg=CREAM)
        lista_outer.pack(fill="both", expand=True, padx=4, pady=4)
        lista_canvas = tk.Canvas(lista_outer, bg=CREAM, highlightthickness=0)
        lista_vsb = ttk.Scrollbar(lista_outer, orient="vertical", command=lista_canvas.yview)
        lista_canvas.configure(yscrollcommand=lista_vsb.set)
        lista_vsb.pack(side="right", fill="y")
        lista_canvas.pack(side="left", fill="both", expand=True)
        lista_frame = tk.Frame(lista_canvas, bg=CREAM)
        lista_win = lista_canvas.create_window((0, 0), window=lista_frame, anchor="nw")

        def _lista_conf(e):
            lista_canvas.configure(scrollregion=lista_canvas.bbox("all"))
        lista_frame.bind("<Configure>", _lista_conf)
        lista_canvas.bind("<Configure>", lambda e: lista_canvas.itemconfig(lista_win, width=e.width))

        right = tk.Frame(main_pane, bg=CREAM)
        right.pack(side="left", fill="both", expand=True)

        inner_nb = ttk.Notebook(right)
        inner_nb.pack(fill="both", expand=True, padx=4, pady=4)

        tree_tab = tk.Frame(inner_nb, bg=CREAM)
        inner_nb.add(tree_tab, text="🌳 Drzewo genealogiczne")

        result_tab = tk.Frame(inner_nb, bg=CREAM)
        inner_nb.add(result_tab, text="⚖ Dziedziczenie")

        tree_toolbar = tk.Frame(tree_tab, bg="#dce8f8")
        tree_toolbar.pack(fill="x")
        tk.Label(tree_toolbar, text="Przeciągnij=przesuń  |  Scroll=zoom  |  2×klik=edycja  |  PPM=menu",
                 font=self.f_small, bg="#dce8f8", fg=MUTED).pack(side="left", padx=8, pady=4)

        cent_btn = tk.Button(tree_toolbar, text="⟳ Resetuj widok",
                             bg="#7a9ab8", fg="white", font=self.f_small,
                             relief="flat", padx=8, pady=3, cursor="hand2")
        cent_btn.pack(side="right", padx=4, pady=3)

        drzewo = DrzewoGenealogiczne(tree_tab, sp_baza, bg=CREAM)
        drzewo.pack(fill="both", expand=True)

        def _reset_drzewo():
            drzewo.reset_pozycji()

        cent_btn.config(command=_reset_drzewo)

        wynik_frame = tk.Frame(result_tab, bg=CREAM)
        wynik_frame.pack(fill="both", expand=True, padx=8, pady=8)
        wynik_text = tk.Text(wynik_frame, font=("Courier New", 11),
                             bg="#0d1117", fg="#c9d1d9",
                             relief="flat", bd=0, wrap="word",
                             highlightthickness=1, highlightbackground=BORDER)
        wynik_vsb = ttk.Scrollbar(wynik_frame, orient="vertical", command=wynik_text.yview)
        wynik_text.configure(yscrollcommand=wynik_vsb.set)
        wynik_vsb.pack(side="right", fill="y")
        wynik_text.pack(fill="both", expand=True)
        wynik_text.configure(state="disabled")

        leg = tk.Frame(outer, bg=CREAM, pady=2)
        leg.pack(fill="x")
        for tekst, kolor in [
            ("🔵 Mężczyzna żyjący", "#1a3a8a"),
            ("🩷 Kobieta żyjąca", "#a0205a"),
            ("⚫ Osoba ZMARŁA (✝)", "#333333"),
            ("🔴 Wydziedziczona/y", "#c0392b"),
            ("🟠 Odrzucił/a spadek", "#8b5000"),
        ]:
            tk.Label(leg, text=f"  {tekst}", font=self.f_small,
                     bg=CREAM, fg=kolor).pack(side="left")

        import time as _time
        _last_btn_click = {"oid": None, "t": 0.0}

        def _btn_click(oid):
            now = _time.time()
            if _last_btn_click["oid"] == oid and now - _last_btn_click["t"] < 0.45:
                _last_btn_click["oid"] = None
                _edytuj_id(oid)
            else:
                _last_btn_click["oid"] = oid
                _last_btn_click["t"] = now
                _wybierz(oid)

        def _odswiez():
            self._clear_frame(lista_frame)
            filtr = szuk_var.get().strip().lower()

            for o in sorted(sp_baza.osoby.values(), key=lambda x: (x.nazwisko, x.imie)):
                if filtr and filtr not in o.pelne_imie.lower():
                    continue

                wyb = (o.id == sp_wybr["id"])

                if o.wydziedziczona:
                    bg_c, tc = "#fde8e8", "#c0392b"
                elif o.odrzucila_spadek:
                    bg_c, tc = "#fef3e0", "#8b5000"
                elif not o.zyje:
                    bg_c, tc = ("#b8b8c8" if wyb else "#d8d8d8"), "#111111"
                elif o.plec == "K":
                    bg_c, tc = ("#f0c8e0" if wyb else "#fce8f2"), "#a0205a"
                else:
                    bg_c, tc = ("#b8d8f8" if wyb else "#ddeeff"), "#1a3a8a"

                label = f"{'✝ ' if not o.zyje else ''}{o.pelne_imie}"
                if o.wiek:
                    label += f" ({o.wiek}l.)"

                btn = tk.Button(lista_frame, text=label, anchor="w",
                                bg=bg_c, fg=tc, font=self.f_small,
                                relief="flat", cursor="hand2",
                                command=lambda oid=o.id: _btn_click(oid))
                btn.pack(fill="x", pady=1, padx=2, ipady=3)
                btn.bind("<ButtonPress-3>", lambda e, oid=o.id: _kontekst_lista(e, oid))

            choices = [f"{o.pelne_imie} [{o.id}]"
                       for o in sorted(sp_baza.osoby.values(), key=lambda x: x.nazwisko)]
            sp_combo["values"] = choices
            if choices and not sp_combo_var.get():
                sp_combo_var.set(choices[0])

            drzewo.odrysuj()

        def _wybierz(oid: str):
            sp_wybr["id"] = oid
            _odswiez()

        def _kontekst_lista(e, oid):
            o = sp_baza.osoby.get(oid)
            if not o:
                return
            menu = tk.Menu(outer, tearoff=0)
            menu.add_command(label=f"👤 {o.pelne_imie}", state="disabled",
                             font=("Segoe UI", 9, "bold"))
            menu.add_separator()
            menu.add_command(label="✏ Edytuj", command=lambda: _edytuj_id(oid))
            menu.add_command(label="🗑 Usuń", command=lambda: _usun_id(oid),
                             foreground="#c0392b")
            try:
                menu.tk_popup(e.x_root, e.y_root)
            finally:
                menu.grab_release()

        def _dodaj_osobe():
            dlg = DialogOsoby(outer, sp_baza, _fonts)
            outer.wait_window(dlg)
            if dlg.result:
                _odswiez()
                if dlg.auto_created:
                    n = ", ".join(x.pelne_imie for x in dlg.auto_created)
                    messagebox.showinfo("Auto-dodano",
                        f"Automatycznie dodano: {n}\nMożesz uzupełnić dane klikając Edytuj.")

        def _edytuj_id(oid: str):
            if oid not in sp_baza.osoby:
                return
            sp_wybr["id"] = oid
            o = sp_baza.osoby[oid]
            dlg = DialogOsoby(outer, sp_baza, _fonts, osoba=o)
            outer.wait_window(dlg)
            if dlg.result:
                _odswiez()

        def _edytuj_wybrana():
            oid = sp_wybr["id"]
            if not oid or oid not in sp_baza.osoby:
                messagebox.showinfo("Info", "Wybierz osobę z listy.")
                return
            _edytuj_id(oid)

        def _usun_id(oid: str):
            o = sp_baza.osoby.get(oid)
            if not o:
                return
            if messagebox.askyesno("Usuń osobę",
                    f"Usunąć {o.pelne_imie}?\nTej operacji nie można cofnąć!"):
                sp_baza.usun(oid)
                if sp_wybr["id"] == oid:
                    sp_wybr["id"] = None
                _odswiez()

        def _usun_wybrana():
            oid = sp_wybr["id"]
            if not oid:
                messagebox.showinfo("Info", "Wybierz osobę z listy.")
                return
            _usun_id(oid)

        def _zapisz():
            plik = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON", "*.json"), ("Wszystkie", "*.*")],
                title="Zapisz bazę danych rodziny")
            if plik:
                try:
                    sp_baza.zapisz(plik)
                    messagebox.showinfo("Zapisano", f"Baza zapisana:\n{plik}")
                except Exception as ex:
                    messagebox.showerror("Błąd", str(ex))

        def _wczytaj():
            plik = filedialog.askopenfilename(
                filetypes=[("JSON", "*.json"), ("Wszystkie", "*.*")],
                title="Wczytaj bazę danych rodziny")
            if plik:
                try:
                    sp_baza.wczytaj(plik)
                    sp_wybr["id"] = None
                    _odswiez()
                except Exception as ex:
                    messagebox.showerror("Błąd", f"Nie można wczytać:\n{ex}")

        def _oblicz():
            val = sp_combo_var.get()
            if not val:
                messagebox.showerror("Błąd", "Wybierz spadkodawcę.")
                return
            if "[" in val and val.endswith("]"):
                sp_id = val.split("[")[-1][:-1]
            else:
                messagebox.showerror("Błąd", "Nieprawidłowy wybór spadkodawcy.")
                return
            if sp_id not in sp_baza.osoby:
                messagebox.showerror("Błąd", "Wybrana osoba nie istnieje w bazie.")
                return

            sp = sp_baza.osoby[sp_id]
            silnik = SilnikDziedziczenia(sp_baza, sp_id)
            udzialy = silnik.oblicz()
            opis = silnik.opis_udzialu(udzialy)

            wynik_text.configure(state="normal")
            wynik_text.delete("1.0", "end")
            ln = "═" * 54 + "\n"
            wynik_text.insert("end", ln)
            wynik_text.insert("end", f"  SPADKODAWCA: {sp.pelne_imie}\n")
            if sp.data_smierci:
                wynik_text.insert("end", f"  Data śmierci: {_sp_fmt_date(sp.data_smierci)}\n")
            wynik_text.insert("end", ln)
            wynik_text.insert("end", "\n  PORZĄDEK DZIEDZICZENIA USTAWOWEGO (art. 931–940 KC)\n\n")

            if not opis:
                wynik_text.insert("end", "  Brak danych do obliczenia.\n")
            else:
                wynik_text.insert("end", f"  {'Spadkobierca':<30} {'Udział':>10}  {'%':>8}\n")
                wynik_text.insert("end", "  " + "─" * 52 + "\n")
                for imie_o, ulamek, procent in opis:
                    wynik_text.insert("end", f"  {imie_o:<30} {ulamek:>10}  {procent:>8}\n")
                wynik_text.insert("end", "\n" + ln)

                for o in sp_baza.osoby.values():
                    if o.wydziedziczona:
                        wynik_text.insert("end", f"  ⚠ {o.pelne_imie} — wydziedziczona/y\n")
                    if o.odrzucila_spadek:
                        wynik_text.insert("end", f"  ⚠ {o.pelne_imie} — odrzuciła/ił spadek\n")

            wynik_text.insert("end",
                "\n  UWAGA: Wynik ma charakter informacyjny.\n"
                "  Zweryfikuj zgodność z KC przed zastosowaniem w sprawie.\n")
            wynik_text.configure(state="disabled")

            inner_nb.select(result_tab)

        def _pdf():
            val = sp_combo_var.get()
            if not val or "[" not in val:
                messagebox.showerror("Błąd", "Wybierz spadkodawcę.")
                return
            sp_id = val.split("[")[-1][:-1]
            if sp_id not in sp_baza.osoby:
                messagebox.showerror("Błąd", "Wybrana osoba nie istnieje.")
                return
            plik = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("PDF", "*.pdf")],
                title="Zapisz raport PDF")
            if not plik:
                return
            try:
                _generuj_pdf_spadki(sp_baza, sp_id, plik)
                if sys.platform == "win32":
                    os.startfile(plik)
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", plik])
                else:
                    subprocess.Popen(["xdg-open", plik])
            except RuntimeError as ex:
                messagebox.showerror("Brak biblioteki", str(ex))
            except Exception as ex:
                messagebox.showerror("Błąd PDF", str(ex))

        drzewo.on_select = _wybierz
        drzewo.on_edit = _edytuj_id
        drzewo.on_delete = _usun_id

        szuk_var.trace_add("write", lambda *a: _odswiez())

        _odswiez()


