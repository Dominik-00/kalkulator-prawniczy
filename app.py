"""
app.py — Główna klasa aplikacji App (tk.Tk) z wszystkimi zakładkami:
         Koszty, Raty, PKK, Opłata roczna, Daty, Spadki.
"""

import tkinter as tk
from tkinter import ttk, messagebox, font, filedialog
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from fractions import Fraction
import sys
import os
import json
import tempfile
import subprocess

from config import APP_VERSION, GITHUB_REPO, GITHUB_TOKEN
from constants import (BG, PANEL, CREAM, GOLD, GOLD_LT, TEXT, MUTED, RED, GREEN,
                       BORDER, HEADER_H, fmt, safe_float, safe_int,
                       oplata_sadowa, wynagrodzenie_pelnomocnika)
from updater import sprawdz_wersje_w_tle, OknoAktualizacji
from inheritance import (Osoba, BazaDanych, SilnikDziedziczenia,
                         DrzewoGenealogiczne, DialogOsoby,
                         _generuj_pdf_spadki, _sp_fmt_date)

# ── Główna aplikacja ─────────────────────────────────────────────────────────
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"Kalkulator Prawniczy  v{APP_VERSION}")
        self.geometry("1365x1014")
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

        self._tab_koszty(nb)
        self._tab_raty(nb)
        self._tab_pkk(nb)
        self._tab_oplata_roczna(nb)
        self._tab_daty(nb)
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

    # ═══════════════════════════════════════════════════════════════════════
    # ZAKŁADKA 1 – KOSZTY
    # ═══════════════════════════════════════════════════════════════════════
    def _tab_koszty(self, nb):
        outer = tk.Frame(nb, bg=CREAM)
        nb.add(outer, text="⚖  Liczenie kosztów")
        frame, _ = self._scrollable(outer)

        tk.Label(frame, text="Koszty postępowania sądowego",
                 font=self.f_sub, bg=CREAM, fg=TEXT).pack(anchor="w", padx=20, pady=(14, 2))
        tk.Label(frame,
                 text="Art. 98–110 KPC · rozp. MS z 22.10.2015 · UKSCP - aktualne na dzień 28.02.2026",
                 font=self.f_small, bg=CREAM, fg=MUTED).pack(anchor="w", padx=20)

        c = self._card(frame, "Parametry sprawy", pady=14)
        c.columnconfigure(1, weight=1); c.columnconfigure(3, weight=1)

        self._lbl(c, "Wartość przedmiotu sporu (PLN):", 0, 0)
        self.k_wps = self._entry(c, 0, 1)
        self.k_wps.insert(0, "50000")

        self._lbl(c, "Rodzaj sprawy:", 2, 0)
        self.k_rodzaj = self._combo(c,
            ["Cywilna / majątkowa", "Gospodarcza",
             "Pracownicza (zwolnienie z opłat)",
             "Upominawcze / nakazowe (¼ opłaty)"],
            row=0, col=3)

        self._lbl(c, "Instancja:", 0, 1)
        self.k_instancja = self._combo(c,
            ["I instancja", "II instancja (apelacja)", "Skarga kasacyjna"],
            row=1, col=1)

        self._lbl(c, "Pełnomocnik:", 2, 1)
        self.k_repr = self._combo(c,
            ["Adwokat / radca prawny", "Bez pełnomocnika"],
            row=1, col=3)

        self._lbl(c, "Sygnatura / opis sprawy:", 0, 2)
        self.k_sygnatura = self._entry(c, 2, 1)
        tk.Label(c, text="(np. I C 123/25 – przy zapisie i druku)",
                 font=self.f_small, bg=PANEL, fg=MUTED).grid(
            row=2, column=2, columnspan=2, sticky="w", padx=(8, 0))

        tk.Frame(c, bg=BORDER, height=1).grid(
            row=3, column=0, columnspan=4, sticky="ew", pady=(10, 6))

        self._lbl(c, "Opłata sądowa (PLN):", 0, 4)

        oplata_frame = tk.Frame(c, bg=PANEL)
        oplata_frame.grid(row=4, column=1, columnspan=3, sticky="ew", padx=(4, 0), pady=2)
        oplata_frame.columnconfigure(0, weight=1)

        self.k_oplata_var = tk.StringVar()
        self.k_oplata_entry = tk.Entry(
            oplata_frame, textvariable=self.k_oplata_var,
            font=self.f_body, relief="flat", bd=0,
            bg=CREAM, fg=TEXT, width=14,
            highlightthickness=1, highlightbackground=BORDER)
        self.k_oplata_entry.grid(row=0, column=0, sticky="ew", ipady=4, padx=(0, 8))

        tk.Label(oplata_frame, text="(możesz edytować przed dodaniem)",
                 font=self.f_small, bg=PANEL, fg=MUTED).grid(
            row=0, column=1, sticky="w")

        def dodaj_opiate_do_powoda():
            try:
                amt = float(self.k_oplata_var.get().replace(",", ".").replace(" ", ""))
            except ValueError:
                messagebox.showerror("Błąd", "Wpisz poprawną kwotę opłaty sądowej.")
                return
            if amt <= 0:
                messagebox.showerror("Błąd", "Opłata sądowa musi być większa od zera.")
                return
            self.powod_items.append({
                'desc': 'Opłata sądowa',
                'amt': amt,
                'type': 'Opłata sądowa'
            })
            self.powod_refresh()
            messagebox.showinfo("Dodano", f"Opłata sądowa {fmt(amt)} została dodana do kosztów powoda.")

        btn_oplata = tk.Button(
            c, text="➕  Dodaj do kosztów powoda",
            command=dodaj_opiate_do_powoda,
            bg=GOLD, fg=BG, font=self.f_bold, relief="flat",
            activebackground=GOLD_LT, activeforeground=BG,
            cursor="hand2", padx=14, pady=5)
        btn_oplata.grid(row=4, column=0, sticky="w", pady=(2, 0))

        self.k_info_var = tk.StringVar()
        tk.Label(c, textvariable=self.k_info_var, font=self.f_small,
                 bg="#fffbf0", fg="#555555", justify="left", wraplength=700,
                 relief="flat", bd=0, padx=8, pady=6).grid(
            row=5, column=0, columnspan=4, sticky="ew", pady=(8, 0))

        for w in [self.k_wps, self.k_rodzaj, self.k_instancja, self.k_repr]:
            w.bind("<<ComboboxSelected>>", lambda e: self._update_koszty_info())
        self._update_koszty_info()

        c2 = self._card(frame, "Wynik postępowania (art. 100 KPC)")
        c2.columnconfigure(1, weight=1); c2.columnconfigure(3, weight=1)

        self._lbl(c2, "Ile zasądzono (PLN):", 0, 0)
        self.k_zasadzone = self._entry(c2, 0, 1, width=16)
        self.k_zasadzone.insert(0, "")

        tk.Label(c2, text="← wpisz kwotę, % wyliczy się automatycznie",
                 font=self.f_small, bg=PANEL, fg=MUTED,
                 ).grid(row=0, column=2, columnspan=2, sticky="w", padx=(8, 0))

        tk.Frame(c2, bg=BORDER, height=1).grid(
            row=1, column=0, columnspan=4, sticky="ew", pady=(10, 8))

        self._lbl(c2, "Powód wygrał (%):", 0, 2)
        self.k_pctW = self._entry(c2, 2, 1, width=10)
        self.k_pctW.insert(0, "100")

        self._lbl(c2, "Powód przegrał (%):", 2, 2)
        self.k_pctP = tk.Entry(c2, font=self.f_body, width=10, state="disabled",
                                relief="flat", bg="#eeeeee", fg=MUTED,
                                highlightthickness=1, highlightbackground=BORDER,
                                disabledbackground="#eeeeee", disabledforeground=MUTED)
        self.k_pctP.grid(row=2, column=3, sticky="ew", padx=(4, 8), pady=2, ipady=4)

        self.k_wynik_info_var = tk.StringVar()
        tk.Label(c2, textvariable=self.k_wynik_info_var, font=self.f_small,
                 bg="#fffbf0", fg="#555555", justify="left", wraplength=680,
                 relief="flat", bd=0, padx=8, pady=5).grid(
            row=3, column=0, columnspan=4, sticky="ew", pady=(8, 0))

        self.k_zasadzone.bind("<KeyRelease>", self._on_zasadzone_change)
        self.k_pctW.bind("<KeyRelease>", self._on_pct_change)
        self.k_wps.bind("<KeyRelease>", lambda e: (self._update_koszty_info(), self._on_zasadzone_change()))
        self._set_pctP(0.0)

        # ── Karta: koszty powoda
        self.powod_items = []
        self._build_costs_card(frame, "Koszty powoda", "powod",
            ["Opłata sądowa", "Zaliczka", "Wydatek (inne)", "Wynagrodzenie pełnomocnika"])

        # ── Karta: koszty pozwanego
        self.pozwany_items = []
        self._build_costs_card(frame, "Koszty pozwanego", "pozwany",
            ["Wynagrodzenie pełnomocnika", "Zaliczka", "Wydatek (inne)"])

        # ── Karta: Skarb Państwa
        self.sp_items = []
        self._build_costs_card(frame, "Wydatki Skarbu Państwa", "sp",
            ["Wynagrodzenie biegłego", "Koszty doręczeń", "Inne"])

        btn_frame = tk.Frame(frame, bg=CREAM)
        btn_frame.pack(fill="x", padx=20, pady=12)
        
        row1 = tk.Frame(btn_frame, bg=CREAM)
        row1.pack(fill="x")
        self._btn(row1, "⚖  Oblicz rozliczenie kosztów",
                  self._oblicz_koszty, gold=True).pack(side="left", pady=4, padx=(0,8))
        self._btn(row1, "🖨  Drukuj tabelę kosztów",
                  self._drukuj_koszty).pack(side="left", pady=4, padx=(0,8))
        self._btn(row1, "💾  Zapisz sprawę",
                  self._zapisz_sprawe).pack(side="left", pady=4, padx=(0,8))
        self._btn(row1, "📂  Wczytaj / zarządzaj sprawami",
                  self._wczytaj_sprawy).pack(side="left", pady=4)

        self.k_result_frame = tk.Frame(frame, bg=CREAM)
        self.k_result_frame.pack(fill="x", padx=20, pady=(0, 20))

    def _build_costs_card(self, parent, title, prefix, types):
        c = self._card(parent, title)
        c.columnconfigure(1, weight=2); c.columnconfigure(3, weight=1); c.columnconfigure(5, weight=1)

        self._lbl(c, "Opis:", 0, 0)
        desc_e = self._entry(c, 0, 1, width=22)

        self._lbl(c, "Kwota (PLN):", 2, 0)
        amt_e = self._entry(c, 0, 3, width=12)

        self._lbl(c, "Rodzaj:", 4, 0)
        type_cb = self._combo(c, types, row=0, col=5, width=26)

        list_frame = tk.Frame(c, bg=PANEL)
        list_frame.grid(row=2, column=0, columnspan=6, sticky="ew", pady=(8, 0))

        suma_var = tk.StringVar(value="0,00 PLN")
        suma_lbl = tk.Label(c, textvariable=suma_var, font=self.f_bold,
                            bg=PANEL, fg=TEXT)
        suma_lbl.grid(row=3, column=5, sticky="e", pady=(4, 0))
        tk.Label(c, text="Łącznie:", font=self.f_small, bg=PANEL, fg=MUTED).grid(
            row=3, column=4, sticky="e")

        items = getattr(self, f"{prefix}_items")

        # ── AUTO-WYPEŁNIANIE: wynagrodzenie pełnomocnika ──────────────────────
        def on_type_selected(event=None):
            """
            Gdy użytkownik wybierze 'Wynagrodzenie pełnomocnika', automatycznie:
            - wstawia minimalne wynagrodzenie z rozp. MS z 22.10.2015 na podstawie WPS
            - wstawia opis 'Koszty zastępstwa procesowego'
            """
            if type_cb.get() == "Wynagrodzenie pełnomocnika":
                wps = safe_float(self.k_wps)
                if wps > 0:
                    w = wynagrodzenie_pelnomocnika(wps)
                    amt_e.delete(0, "end")
                    amt_e.insert(0, f"{w:.2f}".replace(".", ","))
                desc_e.delete(0, "end")
                desc_e.insert(0, "Koszty zastępstwa procesowego")

        type_cb.bind("<<ComboboxSelected>>", on_type_selected)
        # ─────────────────────────────────────────────────────────────────────

        def refresh():
            for w in list_frame.winfo_children():
                w.destroy()
            total = 0.0
            for i, item in enumerate(items):
                row = tk.Frame(list_frame, bg="#f9f9f9",
                               highlightthickness=1, highlightbackground=BORDER)
                row.pack(fill="x", pady=1)
                tk.Label(row, text=item['desc'], font=self.f_body,
                         bg="#f9f9f9", fg=TEXT, anchor="w").pack(side="left", padx=8, pady=4)
                tk.Label(row, text=f"[{item['type']}]", font=self.f_small,
                         bg="#f9f9f9", fg=MUTED).pack(side="left")
                tk.Label(row, text=fmt(item['amt']), font=self.f_bold,
                         bg="#f9f9f9", fg=TEXT).pack(side="right", padx=12)
                idx = i
                tk.Button(row, text="✕", command=lambda i=idx: remove(i),
                          bg="#f9f9f9", fg=RED, font=self.f_small,
                          relief="flat", cursor="hand2", padx=6).pack(side="right")
                total += item['amt']
            suma_var.set(fmt(total))

        def add():
            desc = desc_e.get().strip() or "Koszt"
            try:
                amt = float(amt_e.get().replace(",", ".").replace(" ", ""))
            except ValueError:
                messagebox.showerror("Błąd", "Wpisz poprawną kwotę.")
                return
            if amt <= 0:
                messagebox.showerror("Błąd", "Kwota musi być większa od zera.")
                return
            items.append({'desc': desc, 'amt': amt,
                          'type': type_cb.get()})
            desc_e.delete(0, "end")
            amt_e.delete(0, "end")
            refresh()

        def remove(i):
            items.pop(i)
            refresh()

        add_btn = self._btn(c, f"+ Dodaj", add)
        add_btn.grid(row=1, column=0, columnspan=2, sticky="w", pady=(6, 0))
        setattr(self, f"{prefix}_refresh", refresh)

    def _update_koszty_info(self):
        wps = safe_float(self.k_wps)
        if not wps:
            self.k_info_var.set("")
            self.k_oplata_var.set("")
            return
        rodzaj_map = {0: "cywilna", 1: "gospodarcza", 2: "pracownicza", 3: "upominawcze"}
        rodzaj = rodzaj_map.get(self.k_rodzaj.current(), "cywilna")
        repr_idx = self.k_repr.current()
        o = oplata_sadowa(wps, rodzaj, "1")
        w = wynagrodzenie_pelnomocnika(wps) if repr_idx == 0 else 0

        self.k_oplata_var.set(f"{o:.2f}".replace(".", ","))

        info = f"Min. wynagrodzenie pełnomocnika: {fmt(w)}" if w else ""
        if rodzaj == "pracownicza":
            self.k_oplata_var.set("0,00")
            info = "Pracownik zwolniony z opłat sądowych — opłata wynosi 0 PLN."
        elif rodzaj == "upominawcze":
            info = f"¼ opłaty stosunkowej w postępowaniu upominawczym. Min. wynagrodzenie pełnomocnika: {fmt(w)}" if w else "¼ opłaty stosunkowej w postępowaniu upominawczym."
        self.k_info_var.set(info)

    def _set_pctP(self, p: float):
        self.k_pctP.config(state="normal")
        self.k_pctP.delete(0, "end")
        self.k_pctP.insert(0, f"{p:.2f}")
        self.k_pctP.config(state="disabled")

    def _on_zasadzone_change(self, event=None):
        zasadzone_str = self.k_zasadzone.get().replace(",", ".").replace(" ", "")
        wps = safe_float(self.k_wps)
        if not zasadzone_str or not wps:
            self.k_wynik_info_var.set("")
            return
        try:
            zasadzone = float(zasadzone_str)
        except ValueError:
            self.k_wynik_info_var.set("")
            return

        zasadzone = max(0.0, min(zasadzone, wps))
        pctW = round(zasadzone / wps * 100, 4) if wps else 0.0
        pctP = round(100.0 - pctW, 4)

        self.k_pctW.delete(0, "end")
        self.k_pctW.insert(0, f"{pctW:.2f}")
        self._set_pctP(pctP)

        self.k_wynik_info_var.set(
            f"Zasądzono {fmt(zasadzone)} z dochodzonego {fmt(wps)}  →  "
            f"Powód wygrał {pctW:.2f}%  |  Powód przegrał {pctP:.2f}%"
        )

    def _on_pct_change(self, event=None):
        try:
            w = float(self.k_pctW.get())
            p = max(0.0, min(100.0, 100.0 - w))
        except ValueError:
            p = 0.0
        self._set_pctP(p)

        wps = safe_float(self.k_wps)
        if wps:
            zasadzone = wps * (w / 100.0) if 0 <= w <= 100 else 0
            self.k_wynik_info_var.set(
                f"Odpowiada zasądzeniu kwoty {fmt(zasadzone)} z {fmt(wps)}"
            )
            self.k_zasadzone.delete(0, "end")
            self.k_zasadzone.insert(0, f"{zasadzone:.2f}")
        else:
            self.k_wynik_info_var.set("")


    # ═══════════════════════════════════════════════════════════════════════
    # DRUKOWANIE I ZAPIS SPRAW
    # ═══════════════════════════════════════════════════════════════════════

    def _get_koszty_data(self):
        """Zbiera wszystkie dane kosztów do słownika."""
        wps = safe_float(self.k_wps)
        try:
            pctW = float(self.k_pctW.get()) / 100.0
        except ValueError:
            pctW = 1.0
        pctP = 1.0 - pctW

        sum_powod   = sum(i['amt'] for i in self.powod_items)
        sum_pozwany = sum(i['amt'] for i in self.pozwany_items)
        sum_sp      = sum(i['amt'] for i in self.sp_items)

        zwrot_powodowi  = sum_powod   * pctW
        zwrot_pozwanemu = sum_pozwany * pctP
        sp_na_powoda    = sum_sp * pctP
        sp_na_pozwanego = sum_sp * pctW

        if zwrot_powodowi > zwrot_pozwanemu:
            netto_pozwany = zwrot_powodowi - zwrot_pozwanemu
            netto_powod   = 0.0
        else:
            netto_powod   = zwrot_pozwanemu - zwrot_powodowi
            netto_pozwany = 0.0

        return {
            'sygnatura': self.k_sygnatura.get().strip(),
            'wps': wps,
            'rodzaj': self.k_rodzaj.get(),
            'instancja': self.k_instancja.get(),
            'pelnomocnik': self.k_repr.get(),
            'pct_powod': pctW * 100,
            'pct_pozwany': pctP * 100,
            'powod_items': list(self.powod_items),
            'pozwany_items': list(self.pozwany_items),
            'sp_items': list(self.sp_items),
            'sum_powod': sum_powod,
            'sum_pozwany': sum_pozwany,
            'sum_sp': sum_sp,
            'zwrot_powodowi': zwrot_powodowi,
            'zwrot_pozwanemu': zwrot_pozwanemu,
            'sp_na_powoda': sp_na_powoda,
            'sp_na_pozwanego': sp_na_pozwanego,
            'netto_pozwany': netto_pozwany,
            'netto_powod': netto_powod,
            'data_zapisu': datetime.now().strftime("%Y-%m-%d %H:%M"),
        }

    def _drukuj_koszty(self):
        """Generuje plik Word z tabelą kosztów – gotowy do druku i uzupełnienia długopisem."""
        import subprocess, tempfile, shutil

        data = self._get_koszty_data()
        sygn = data['sygnatura'] or 'sprawa'

        # Bezpieczna nazwa pliku
        safe_sygn = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in sygn)
        default_name = f"koszty_{safe_sygn}.docx".replace(' ', '_')

        path = filedialog.asksaveasfilename(
            title="Zapisz wydruk kosztów",
            defaultextension=".docx",
            filetypes=[("Word Document", "*.docx"), ("Wszystkie pliki", "*.*")],
            initialfile=default_name,
        )
        if not path:
            return

        # Sprawdź czy node i docx są dostępne
        node_ok = shutil.which('node') is not None
        _docx_candidates = [
            '/home/claude/.npm-global/lib/node_modules/docx',
            os.path.expanduser('~/.npm-global/lib/node_modules/docx'),
            '/usr/lib/node_modules/docx',
        ]
        npm_global = next((p for p in _docx_candidates if os.path.isdir(p)), _docx_candidates[0])
        docx_ok = os.path.isdir(npm_global)

        if not node_ok:
            messagebox.showerror("Brak Node.js",
                "Do generowania dokumentu Word wymagany jest Node.js.\n"
                "Zainstaluj Node.js (nodejs.org) i uruchom ponownie.")
            return

        if not docx_ok:
            try:
                subprocess.run(['npm', 'install', '-g', 'docx'], check=True,
                               capture_output=True, timeout=60)
            except Exception:
                messagebox.showerror("Instalacja nieudana",
                    "Nie udało się zainstalować modułu 'docx'.\n"
                    "Uruchom ręcznie: npm install -g docx")
                return

        def f2(v): return f"{v:,.2f}".replace(',', ' ').replace('.', ',')

        def make_items_js(items):
            if not items:
                return "[]"
            rows = []
            for it in items:
                rows.append(
                    f'{{desc: {json.dumps(it["desc"], ensure_ascii=False)}, '
                    f'amt: {json.dumps(f2(it["amt"]), ensure_ascii=False)}, '
                    f'type_: {json.dumps(it["type"], ensure_ascii=False)}}}'
                )
            return "[" + ",\n".join(rows) + "]"

        script = f"""
const fs = require('fs');
const path = require('path');

// Try to find docx module
let docxPath;
const homeCandidates = [
  process.env.HOME,
  '/home/claude',
  '/root',
].filter(Boolean);
const candidates = [
  ...homeCandidates.map(h => path.join(h, '.npm-global/lib/node_modules/docx')),
  '/usr/lib/node_modules/docx',
  '/usr/local/lib/node_modules/docx',
];
for (const c of candidates) {{
  if (fs.existsSync(c)) {{ docxPath = c; break; }}
}}
if (!docxPath) {{ console.error('docx not found'); process.exit(1); }}

const {{
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  AlignmentType, BorderStyle, WidthType, ShadingType, VerticalAlign,
  HeadingLevel
}} = require(docxPath);

const thin  = {{ style: BorderStyle.SINGLE, size: 4,  color: 'AAAAAA' }};
const thick = {{ style: BorderStyle.SINGLE, size: 8,  color: '1a1a3a' }};
const none  = {{ style: BorderStyle.NONE,   size: 0,  color: 'FFFFFF' }};
const borderAll  = {{ top: thin,  bottom: thin,  left: thin,  right: thin  }};
const borderHdr  = {{ top: thick, bottom: thick, left: thick, right: thick }};

const W = 9360;  // A4 content width DXA
const col_widths_4 = [3800, 2200, 1680, 1680];
const col_widths_3 = [4200, 3000, 2160];

function hdrCell(text, w) {{
  return new TableCell({{
    width: {{ size: w, type: WidthType.DXA }},
    borders: borderHdr,
    shading: {{ fill: '1a1a3a', type: ShadingType.CLEAR }},
    margins: {{ top: 100, bottom: 100, left: 120, right: 120 }},
    verticalAlign: VerticalAlign.CENTER,
    children: [new Paragraph({{
      alignment: AlignmentType.CENTER,
      children: [new TextRun({{ text, bold: true, color: 'F4C842', size: 20, font: 'Arial' }})]
    }})]
  }});
}}

function dataCell(text, w, bold=false, align=AlignmentType.LEFT, bg='FFFFFF') {{
  return new TableCell({{
    width: {{ size: w, type: WidthType.DXA }},
    borders: borderAll,
    shading: {{ fill: bg, type: ShadingType.CLEAR }},
    margins: {{ top: 80, bottom: 80, left: 120, right: 120 }},
    children: [new Paragraph({{
      alignment: align,
      children: [new TextRun({{ text: text || '', bold, size: 20, font: 'Arial' }})]
    }})]
  }});
}}

function blankCell(w) {{
  return new TableCell({{
    width: {{ size: w, type: WidthType.DXA }},
    borders: borderAll,
    margins: {{ top: 80, bottom: 300, left: 120, right: 120 }},
    children: [new Paragraph({{ children: [new TextRun({{ text: '', size: 20 }})] }})]
  }});
}}

function itemsTable(items, label) {{
  const rows = [
    new TableRow({{ children: [
      hdrCell(label + ' - pozycja', col_widths_4[0]),
      hdrCell('Rodzaj kosztu', col_widths_4[1]),
      hdrCell('Kwota (PLN)', col_widths_4[2]),
      hdrCell('Zatwierdzone', col_widths_4[3]),
    ]}})
  ];
  if (items.length === 0) {{
    rows.push(new TableRow({{ children: [
      dataCell('(brak pozycji)', col_widths_4[0]),
      dataCell('', col_widths_4[1]),
      dataCell('', col_widths_4[2]),
      blankCell(col_widths_4[3]),
    ]}}));
  }} else {{
    items.forEach(it => {{
      rows.push(new TableRow({{ children: [
        dataCell(it.desc, col_widths_4[0]),
        dataCell(it.type_, col_widths_4[1]),
        dataCell(it.amt, col_widths_4[2], false, AlignmentType.RIGHT),
        blankCell(col_widths_4[3]),
      ]}}));
    }});
    // blank row for manual additions
    rows.push(new TableRow({{ children: [
      blankCell(col_widths_4[0]),
      blankCell(col_widths_4[1]),
      blankCell(col_widths_4[2]),
      blankCell(col_widths_4[3]),
    ]}}));
    rows.push(new TableRow({{ children: [
      blankCell(col_widths_4[0]),
      blankCell(col_widths_4[1]),
      blankCell(col_widths_4[2]),
      blankCell(col_widths_4[3]),
    ]}}));
  }}
  return new Table({{ width: {{ size: W, type: WidthType.DXA }}, columnWidths: col_widths_4, rows }});
}}

function p(text, opts={{}}) {{
  return new Paragraph({{
    ...opts,
    children: [new TextRun({{ text, font: 'Arial', size: 22, ...opts.run }})]
  }});
}}

function h1(text) {{
  return new Paragraph({{
    spacing: {{ before: 280, after: 120 }},
    children: [new TextRun({{ text, font: 'Arial', size: 28, bold: true, color: '1a1a3a' }})]
  }});
}}

function h2(text) {{
  return new Paragraph({{
    spacing: {{ before: 200, after: 80 }},
    border: {{ bottom: {{ style: BorderStyle.SINGLE, size: 4, color: '1a1a3a', space: 1 }} }},
    children: [new TextRun({{ text, font: 'Arial', size: 22, bold: true, color: '1a1a3a' }})]
  }});
}}

function summaryTable(rows_data) {{
  const rows = rows_data.map((([label, val, bold, bg]) => new TableRow({{ children: [
    dataCell(label, col_widths_3[0], bold, AlignmentType.LEFT, bg || 'FFFFFF'),
    dataCell(val,   col_widths_3[1], bold, AlignmentType.RIGHT, bg || 'FFFFFF'),
    blankCell(col_widths_3[2]),
  ]}})));
  return new Table({{ width: {{ size: W, type: WidthType.DXA }}, columnWidths: col_widths_3,
    rows: [
      new TableRow({{ children: [
        hdrCell('Pozycja rozliczenia', col_widths_3[0]),
        hdrCell('Kwota (PLN)', col_widths_3[1]),
        hdrCell('Zatwierdzone / uwagi', col_widths_3[2]),
      ]}}),
      ...rows,
    ]
  }});
}}

const sygnatura = {json.dumps(data['sygnatura'] or '(nie podano)', ensure_ascii=False)};
const wps       = {json.dumps(f2(data['wps']), ensure_ascii=False)};
const rodzaj    = {json.dumps(data['rodzaj'], ensure_ascii=False)};
const instancja = {json.dumps(data['instancja'], ensure_ascii=False)};
const pelnomocnik = {json.dumps(data['pelnomocnik'], ensure_ascii=False)};
const pctW = {json.dumps(f"{data['pct_powod']:.2f} %", ensure_ascii=False)};
const pctP = {json.dumps(f"{data['pct_pozwany']:.2f} %", ensure_ascii=False)};

const powod_items   = {make_items_js(data['powod_items'])};
const pozwany_items = {make_items_js(data['pozwany_items'])};
const sp_items      = {make_items_js(data['sp_items'])};

const sum_powod   = {json.dumps(f2(data['sum_powod']), ensure_ascii=False)};
const sum_pozwany = {json.dumps(f2(data['sum_pozwany']), ensure_ascii=False)};
const sum_sp      = {json.dumps(f2(data['sum_sp']), ensure_ascii=False)};
const zwrot_pow   = {json.dumps(f2(data['zwrot_powodowi']), ensure_ascii=False)};
const zwrot_poz   = {json.dumps(f2(data['zwrot_pozwanemu']), ensure_ascii=False)};
const sp_na_pow   = {json.dumps(f2(data['sp_na_powoda']), ensure_ascii=False)};
const sp_na_poz   = {json.dumps(f2(data['sp_na_pozwanego']), ensure_ascii=False)};
const netto_poz   = {json.dumps(f2(data['netto_pozwany']), ensure_ascii=False)};
const netto_pow   = {json.dumps(f2(data['netto_powod']), ensure_ascii=False)};

let wynikLabel, wynikVal;
if ({data['netto_pozwany']:.4f} > 0) {{
  wynikLabel = 'Pozwany zapłaci na rzecz powoda (kompensata):';
  wynikVal   = netto_poz;
}} else if ({data['netto_powod']:.4f} > 0) {{
  wynikLabel = 'Powód zapłaci na rzecz pozwanego (kompensata):';
  wynikVal   = netto_pow;
}} else {{
  wynikLabel = 'Koszty wzajemnie zniesione (równy wynik):';
  wynikVal   = '—';
}}

const doc = new Document({{
  styles: {{
    default: {{ document: {{ run: {{ font: 'Arial', size: 22 }} }} }},
  }},
  sections: [{{
    properties: {{
      page: {{
        size: {{ width: 11906, height: 16838 }},
        margin: {{ top: 1134, right: 1134, bottom: 1134, left: 1134 }},
      }}
    }},
    children: [
      h1('Zestawienie kosztów postępowania sądowego'),

      // meta tabela
      new Table({{
        width: {{ size: W, type: WidthType.DXA }},
        columnWidths: [2400, 4000, 1500, 1460],
        rows: [
          new TableRow({{ children: [
            dataCell('Sygnatura / sprawa:', 2400, true, AlignmentType.LEFT, 'F0F0F8'),
            dataCell(sygnatura, 4000, false),
            dataCell('Data wydruku:', 1500, true, AlignmentType.LEFT, 'F0F0F8'),
            dataCell({json.dumps(data['data_zapisu'], ensure_ascii=False)}, 1460),
          ]}}),
          new TableRow({{ children: [
            dataCell('Wartość przedmiotu sporu:', 2400, true, AlignmentType.LEFT, 'F0F0F8'),
            dataCell(wps + ' PLN', 4000),
            dataCell('Instancja:', 1500, true, AlignmentType.LEFT, 'F0F0F8'),
            dataCell(instancja, 1460),
          ]}}),
          new TableRow({{ children: [
            dataCell('Rodzaj sprawy:', 2400, true, AlignmentType.LEFT, 'F0F0F8'),
            dataCell(rodzaj, 4000),
            dataCell('Pełnomocnik:', 1500, true, AlignmentType.LEFT, 'F0F0F8'),
            dataCell(pelnomocnik, 1460),
          ]}}),
          new TableRow({{ children: [
            dataCell('Powód wygrał:', 2400, true, AlignmentType.LEFT, 'F0F0F8'),
            dataCell(pctW, 4000),
            dataCell('Pozwany wygrał:', 1500, true, AlignmentType.LEFT, 'F0F0F8'),
            dataCell(pctP, 1460),
          ]}}),
        ]
      }}),

      new Paragraph({{ spacing: {{ before: 180, after: 0 }} }}),
      h2('Koszty powoda'),
      itemsTable(powod_items, 'Powód'),

      new Paragraph({{ spacing: {{ before: 180, after: 0 }} }}),
      h2('Koszty pozwanego'),
      itemsTable(pozwany_items, 'Pozwany'),

      new Paragraph({{ spacing: {{ before: 180, after: 0 }} }}),
      h2('Wydatki Skarbu Państwa'),
      itemsTable(sp_items, 'Skarb Państwa'),

      new Paragraph({{ spacing: {{ before: 220, after: 0 }} }}),
      h2('Rozliczenie kosztów (art. 98–100 KPC)'),
      summaryTable([
        ['Koszty poniesione przez powoda łącznie',    sum_powod,   false],
        ['Koszty poniesione przez pozwanego łącznie', sum_pozwany, false],
        ['Wydatki Skarbu Państwa łącznie',            sum_sp,      false],
        ['Zwrot kosztów należny powodowi (' + pctW + ')',    zwrot_pow, false, 'EEF8EE'],
        ['Zwrot kosztów należny pozwanemu (' + pctP + ')',   zwrot_poz, false, 'EEF8EE'],
        ['Wydatki SP obciążające powoda (' + pctP + ')',     sp_na_pow, false, 'FFF0F0'],
        ['Wydatki SP obciążające pozwanego (' + pctW + ')',  sp_na_poz, false, 'FFF0F0'],
      ]),

      new Paragraph({{ spacing: {{ before: 140, after: 0 }} }}),
      new Table({{
        width: {{ size: W, type: WidthType.DXA }},
        columnWidths: col_widths_3,
        rows: [
          new TableRow({{ children: [
            new TableCell({{
              width: {{ size: col_widths_3[0], type: WidthType.DXA }},
              borders: {{ top: {{ style: BorderStyle.SINGLE, size: 8, color: 'F4C842' }},
                          bottom: {{ style: BorderStyle.SINGLE, size: 8, color: 'F4C842' }},
                          left:   {{ style: BorderStyle.SINGLE, size: 8, color: 'F4C842' }},
                          right:  {{ style: BorderStyle.SINGLE, size: 8, color: 'F4C842' }} }},
              shading: {{ fill: '1a1a3a', type: ShadingType.CLEAR }},
              margins: {{ top: 120, bottom: 120, left: 140, right: 140 }},
              children: [new Paragraph({{ alignment: AlignmentType.LEFT,
                children: [new TextRun({{ text: wynikLabel, bold: true, color: 'F4C842', size: 22, font: 'Arial' }})]
              }})]
            }}),
            new TableCell({{
              width: {{ size: col_widths_3[1], type: WidthType.DXA }},
              borders: {{ top: {{ style: BorderStyle.SINGLE, size: 8, color: 'F4C842' }},
                          bottom: {{ style: BorderStyle.SINGLE, size: 8, color: 'F4C842' }},
                          left:   {{ style: BorderStyle.SINGLE, size: 8, color: 'F4C842' }},
                          right:  {{ style: BorderStyle.SINGLE, size: 8, color: 'F4C842' }} }},
              shading: {{ fill: '1a1a3a', type: ShadingType.CLEAR }},
              margins: {{ top: 120, bottom: 120, left: 140, right: 140 }},
              children: [new Paragraph({{ alignment: AlignmentType.RIGHT,
                children: [new TextRun({{ text: wynikVal, bold: true, color: 'F4C842', size: 24, font: 'Arial' }})]
              }})]
            }}),
            blankCell(col_widths_3[2]),
          ]}})
        ]
      }}),

      new Paragraph({{ spacing: {{ before: 400, after: 0 }} }}),
      h2('Podpisy'),
      new Table({{
        width: {{ size: W, type: WidthType.DXA }},
        columnWidths: [3600, 400, 3600, 1760],
        rows: [
          new TableRow({{ children: [
            new TableCell({{
              width: {{ size: 3600, type: WidthType.DXA }},
              borders: {{ top: none, bottom: thin, left: none, right: none }},
              margins: {{ top: 600, bottom: 80, left: 120, right: 120 }},
              children: [new Paragraph({{ alignment: AlignmentType.CENTER,
                children: [new TextRun({{ text: 'Pełnomocnik powoda', size: 18, font: 'Arial', color: '777777' }})]
              }})]
            }}),
            new TableCell({{
              width: {{ size: 400, type: WidthType.DXA }},
              borders: {{ top: none, bottom: none, left: none, right: none }},
              children: [new Paragraph({{ children: [] }})]
            }}),
            new TableCell({{
              width: {{ size: 3600, type: WidthType.DXA }},
              borders: {{ top: none, bottom: thin, left: none, right: none }},
              margins: {{ top: 600, bottom: 80, left: 120, right: 120 }},
              children: [new Paragraph({{ alignment: AlignmentType.CENTER,
                children: [new TextRun({{ text: 'Pełnomocnik pozwanego', size: 18, font: 'Arial', color: '777777' }})]
              }})]
            }}),
            new TableCell({{
              width: {{ size: 1760, type: WidthType.DXA }},
              borders: {{ top: none, bottom: none, left: none, right: none }},
              children: [new Paragraph({{ children: [] }})]
            }}),
          ]}})
        ]
      }}),
    ]
  }}]
}});

Packer.toBuffer(doc).then(buf => {{
  fs.writeFileSync({json.dumps(path, ensure_ascii=False)}, buf);
  console.log('OK');
}}).catch(err => {{
  console.error(err);
  process.exit(1);
}});
"""

        tmp = tempfile.NamedTemporaryFile(suffix='.js', mode='w', encoding='utf-8', delete=False)
        tmp.write(script)
        tmp.close()

        try:
            env = os.environ.copy()
            _npm_candidates = ['/home/claude/.npm-global', os.path.expanduser('~/.npm-global')]
            npm_prefix = next((p for p in _npm_candidates if os.path.isdir(p)), _npm_candidates[0])
            env['NODE_PATH'] = os.path.join(npm_prefix, 'lib', 'node_modules')
            result = subprocess.run(['node', tmp.name], capture_output=True, text=True,
                                    timeout=30, env=env)
            if result.returncode == 0 and 'OK' in result.stdout:
                messagebox.showinfo("Gotowe",
                    f"Wydruk zapisany:\n{path}\n\nMożesz otworzyć go w Word / LibreOffice i wydrukować.")
            else:
                messagebox.showerror("Błąd generowania",
                    f"Nie udało się wygenerować dokumentu.\n{result.stderr[:400]}")
        except subprocess.TimeoutExpired:
            messagebox.showerror("Timeout", "Node.js nie odpowiedział w ciągu 30 sekund.")
        except Exception as e:
            messagebox.showerror("Błąd", str(e))
        finally:
            os.unlink(tmp.name)

    def _zapisz_sprawe(self):
        """Zapisuje koszty bieżącej sprawy do pliku JSON."""
        data = self._get_koszty_data()
        sygn = data['sygnatura'] or 'sprawa'
        safe_sygn = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in sygn)
        default = f"sprawa_{safe_sygn}.json".replace(' ', '_')

        path = filedialog.asksaveasfilename(
            title="Zapisz koszty sprawy",
            defaultextension=".json",
            filetypes=[("Pliki JSON", "*.json"), ("Wszystkie pliki", "*.*")],
            initialfile=default,
        )
        if not path:
            return

        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            messagebox.showinfo("Zapisano",
                f"Sprawa zapisana do:\n{path}")
        except Exception as e:
            messagebox.showerror("Błąd zapisu", str(e))

    def _wczytaj_sprawy(self):
        """Okno menedżera spraw – wczytywanie, podgląd i ładowanie do kalkulatora."""
        path = filedialog.askopenfilename(
            title="Wybierz plik sprawy",
            filetypes=[("Pliki JSON", "*.json"), ("Wszystkie pliki", "*.*")],
        )
        if not path:
            return

        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            messagebox.showerror("Błąd odczytu", str(e))
            return

        # Podgląd + pytanie czy wczytać
        sygn = data.get('sygnatura', '?')
        wps  = data.get('wps', 0)
        n_p  = len(data.get('powod_items', []))
        n_pz = len(data.get('pozwany_items', []))
        n_sp = len(data.get('sp_items', []))
        dt   = data.get('data_zapisu', '?')

        msg = (
            f"Sprawa: {sygn}\n"
            f"WPS: {wps:,.2f} PLN\n"
            f"Koszty powoda: {n_p} pozycji\n"
            f"Koszty pozwanego: {n_pz} pozycji\n"
            f"Wydatki SP: {n_sp} pozycji\n"
            f"Zapisano: {dt}\n\n"
            f"Wczytać dane do kalkulatora?\n"
            f"(zastąpi bieżące dane kosztów)"
        )
        if not messagebox.askyesno("Wczytaj sprawę", msg):
            return

        # Załaduj dane do interfejsu
        self.k_sygnatura.delete(0, "end")
        self.k_sygnatura.insert(0, data.get('sygnatura', ''))

        self.k_wps.delete(0, "end")
        self.k_wps.insert(0, str(data.get('wps', 0)))

        # powod_items
        self.powod_items.clear()
        self.powod_items.extend(data.get('powod_items', []))

        # pozwany_items
        self.pozwany_items.clear()
        self.pozwany_items.extend(data.get('pozwany_items', []))

        # sp_items
        self.sp_items.clear()
        self.sp_items.extend(data.get('sp_items', []))

        # procenty
        self.k_pctW.delete(0, "end")
        self.k_pctW.insert(0, f"{data.get('pct_powod', 100):.2f}")
        self._set_pctP(data.get('pct_pozwany', 0))

        # Odśwież listy
        self.powod_refresh()
        self.pozwany_refresh()
        self.sp_refresh()
        self._update_koszty_info()

        messagebox.showinfo("Wczytano",
            f"Dane sprawy '{sygn}' zostały wczytane do kalkulatora.")

    def _oblicz_koszty(self):
        wps = safe_float(self.k_wps)
        try:
            pctW = float(self.k_pctW.get()) / 100.0
        except ValueError:
            messagebox.showerror("Błąd", "Wpisz poprawny procent wygranej.")
            return
        pctP = 1.0 - pctW

        sum_powod   = sum(i['amt'] for i in self.powod_items)
        sum_pozwany = sum(i['amt'] for i in self.pozwany_items)
        sum_sp      = sum(i['amt'] for i in self.sp_items)

        zwrot_powodowi   = sum_powod   * pctW
        zwrot_pozwanemu  = sum_pozwany * pctP
        sp_na_powoda     = sum_sp * pctP
        sp_na_pozwanego  = sum_sp * pctW

        if zwrot_powodowi > zwrot_pozwanemu:
            netto_pozwany = zwrot_powodowi - zwrot_pozwanemu
            netto_powod   = 0.0
        else:
            netto_powod   = zwrot_pozwanemu - zwrot_powodowi
            netto_pozwany = 0.0

        for w in self.k_result_frame.winfo_children():
            w.destroy()

        rb = tk.Frame(self.k_result_frame, bg=BG)
        rb.pack(fill="x")

        tk.Label(rb, text="  ⚖  Rozliczenie kosztów (art. 98–100 KPC)",
                 font=self.f_sub, bg=BG, fg=GOLD).pack(anchor="w", padx=16, pady=(12, 8))

        pbar_frame = tk.Frame(rb, bg=BG)
        pbar_frame.pack(fill="x", padx=16, pady=(0, 10))

        info_row = tk.Frame(pbar_frame, bg=BG)
        info_row.pack(fill="x")
        tk.Label(info_row,
                 text=f"Powód wygrał: {pctW*100:.1f}%  ({fmt(wps*pctW)})",
                 font=self.f_bold, bg=BG, fg="#6fcf97").pack(side="left")
        tk.Label(info_row,
                 text=f"Pozwany wygrał: {pctP*100:.1f}%  ({fmt(wps*pctP)})",
                 font=self.f_bold, bg=BG, fg="#eb5757").pack(side="right")

        bar_bg = tk.Frame(pbar_frame, bg="#2d2d4a", height=10)
        bar_bg.pack(fill="x", pady=6)
        bar_bg.update_idletasks()
        w_total = bar_bg.winfo_width() or 600
        fill_w = max(1, int(w_total * pctW))
        tk.Frame(bar_bg, bg=GOLD, width=fill_w, height=10).place(x=0, y=0)

        tk.Frame(rb, bg="#2d2d4a", height=1).pack(fill="x", padx=16)

        rows = [
            ("Koszty poniesione przez powoda",            fmt(sum_powod),   None),
            ("Koszty poniesione przez pozwanego",         fmt(sum_pozwany),  None),
            ("Wydatki Skarbu Państwa łącznie",            fmt(sum_sp),       None),
            None,
            (f"Zwrot kosztów należny powodowi ({pctW*100:.1f}%)",    fmt(zwrot_powodowi),  "#6fcf97"),
            (f"Zwrot kosztów należny pozwanemu ({pctP*100:.1f}%)",   fmt(zwrot_pozwanemu), "#6fcf97"),
            None,
            (f"Wydatki SP obciążające powoda ({pctP*100:.1f}%)",     fmt(sp_na_powoda),    "#eb5757"),
            (f"Wydatki SP obciążające pozwanego ({pctW*100:.1f}%)",  fmt(sp_na_pozwanego), "#eb5757"),
        ]
        for r in rows:
            if r is None:
                tk.Frame(rb, bg="#333355", height=1).pack(fill="x", padx=16, pady=4)
                continue
            self._res_row(rb, r[0], r[1], color=r[2])

        tk.Frame(rb, bg=GOLD, height=2).pack(fill="x", padx=16, pady=8)

        if netto_pozwany > 0:
            self._res_row(rb,
                "✅  Pozwany zapłaci na rzecz powoda (kompensata):",
                fmt(netto_pozwany), color=GOLD_LT, big=True)
        elif netto_powod > 0:
            self._res_row(rb,
                "✅  Powód zapłaci na rzecz pozwanego (kompensata):",
                fmt(netto_powod), color=GOLD_LT, big=True)
        else:
            self._res_row(rb,
                "⚖  Koszty wzajemnie zniesione (równy wynik):",
                "—", color=GOLD_LT, big=True)

        tk.Label(rb, text="", bg=BG, height=1).pack()

    # ═══════════════════════════════════════════════════════════════════════
    # ZAKŁADKA 2 – RATY
    # ═══════════════════════════════════════════════════════════════════════
    def _tab_raty(self, nb):
        outer = tk.Frame(nb, bg=CREAM)
        nb.add(outer, text="📋  Rozłożenie na raty")
        frame, _ = self._scrollable(outer)

        tk.Label(frame, text="Rozłożenie świadczenia na raty",
                 font=self.f_sub, bg=CREAM, fg=TEXT).pack(anchor="w", padx=20, pady=(14, 2))
        tk.Label(frame,
                 text="Raty równe; pierwsza wyrównuje różnicę groszy jeśli kwota nie dzieli się bez reszty",
                 font=self.f_small, bg=CREAM, fg=MUTED).pack(anchor="w", padx=20)

        c = self._card(frame, "Parametry świadczenia", pady=14)
        c.columnconfigure(1, weight=1); c.columnconfigure(3, weight=1)

        self._lbl(c, "Łączna kwota świadczenia (PLN):", 0, 0)
        self.r_kwota = self._entry(c, 0, 1)
        self.r_kwota.insert(0, "12345.67")

        self._lbl(c, "Częstotliwość rat:", 2, 0)
        self.r_czest = self._combo(c,
            ["Miesięczne", "Kwartalne", "Roczne", "Tygodniowe"],
            row=0, col=3)

        self._lbl(c, "Data pierwszej raty (RRRR-MM-DD):", 0, 1)
        self.r_data = self._entry(c, 1, 1)
        self.r_data.insert(0, date.today().strftime("%Y-%m-%d"))

        self._lbl(c, "Sposób podziału:", 2, 1)
        self.r_mode = tk.StringVar(value="ilosc")
        mode_frame = tk.Frame(c, bg=PANEL)
        mode_frame.grid(row=1, column=3, sticky="w", padx=(4, 0))
        tk.Radiobutton(mode_frame, text="Znana liczba rat",
                       variable=self.r_mode, value="ilosc",
                       command=self._toggle_rata_mode,
                       bg=PANEL, font=self.f_body).pack(side="left")
        tk.Radiobutton(mode_frame, text="Znana kwota raty",
                       variable=self.r_mode, value="kwota",
                       command=self._toggle_rata_mode,
                       bg=PANEL, font=self.f_body).pack(side="left", padx=(12, 0))

        self._lbl(c, "Liczba rat:", 0, 2)
        self.r_ilosc_lbl = tk.Label(c, text="Liczba rat:", font=self.f_small,
                                     bg=PANEL, fg=MUTED)
        self.r_ilosc_lbl.grid(row=2, column=0, sticky="w", pady=(6, 1))
        self.r_ilosc = self._entry(c, 2, 1, width=10)
        self.r_ilosc.insert(0, "12")

        self.r_kwota_j_lbl = tk.Label(c, text="Kwota jednej raty (PLN):", font=self.f_small,
                                       bg=PANEL, fg=MUTED)
        self.r_kwota_j_lbl.grid(row=3, column=0, sticky="w", pady=(6, 1))
        self.r_kwota_j = self._entry(c, 3, 1, width=10)
        self.r_kwota_j.insert(0, "1000")
        self._toggle_rata_mode()

        btn_frame = tk.Frame(frame, bg=CREAM)
        btn_frame.pack(fill="x", padx=20, pady=10)
        self._btn(btn_frame, "📋  Oblicz harmonogram rat",
                  self._oblicz_raty, gold=True).pack(pady=4)

        self.r_result_frame = tk.Frame(frame, bg=CREAM)
        self.r_result_frame.pack(fill="x", padx=20, pady=(0, 20))

    def _toggle_rata_mode(self):
        mode = self.r_mode.get()
        if mode == "ilosc":
            self.r_ilosc_lbl.grid(row=2, column=0, sticky="w")
            self.r_ilosc.grid(row=2, column=1, sticky="ew", padx=(4, 8), pady=2, ipady=4)
            self.r_kwota_j_lbl.grid_remove()
            self.r_kwota_j.grid_remove()
        else:
            self.r_ilosc_lbl.grid_remove()
            self.r_ilosc.grid_remove()
            self.r_kwota_j_lbl.grid(row=2, column=0, sticky="w")
            self.r_kwota_j.grid(row=2, column=1, sticky="ew", padx=(4, 8), pady=2, ipady=4)

    def _oblicz_raty(self):
        kwota = safe_float(self.r_kwota)
        if kwota <= 0:
            messagebox.showerror("Błąd", "Wpisz łączną kwotę świadczenia.")
            return

        czest_map = {0: "miesiac", 1: "kwartal", 2: "rok", 3: "tydzien"}
        czest = czest_map.get(self.r_czest.current(), "miesiac")

        try:
            data_start = datetime.strptime(self.r_data.get().strip(), "%Y-%m-%d").date()
        except ValueError:
            data_start = None

        mode = self.r_mode.get()
        if mode == "ilosc":
            ilosc = safe_int(self.r_ilosc)
            if ilosc < 1:
                messagebox.showerror("Błąd", "Liczba rat musi być co najmniej 1.")
                return
        else:
            kwota_j = safe_float(self.r_kwota_j)
            if kwota_j <= 0 or kwota_j >= kwota:
                messagebox.showerror("Błąd", "Kwota raty musi być > 0 i < kwoty świadczenia.")
                return
            ilosc = math.ceil(kwota / kwota_j)

        rata_base = math.floor(kwota / ilosc * 100) / 100
        suma_bez_pierwszej = round(rata_base * (ilosc - 1), 2)
        pierwsza = round(kwota - suma_bez_pierwszej, 2)

        raty = [{'nr': 1, 'kwota': pierwsza,
                 'wyrownujaca': abs(pierwsza - rata_base) > 0.005}]
        for i in range(2, ilosc + 1):
            raty.append({'nr': i, 'kwota': rata_base, 'wyrownujaca': False})

        def next_date(n):
            if not data_start:
                return "—"
            if czest == "miesiac":
                d = data_start + relativedelta(months=n)
            elif czest == "kwartal":
                d = data_start + relativedelta(months=n * 3)
            elif czest == "rok":
                d = data_start + relativedelta(years=n)
            else:
                from datetime import timedelta
                d = data_start + timedelta(weeks=n)
            return d.strftime("%d.%m.%Y")

        for r in raty:
            r['termin'] = next_date(r['nr'] - 1)

        suma_kontrolna = round(sum(r['kwota'] for r in raty), 2)

        for w in self.r_result_frame.winfo_children():
            w.destroy()

        rb = tk.Frame(self.r_result_frame, bg=BG)
        rb.pack(fill="x")
        tk.Label(rb, text="  📋  Harmonogram rat",
                 font=self.f_sub, bg=BG, fg=GOLD).pack(anchor="w", padx=16, pady=(12, 6))
        self._res_row(rb, "Łączna kwota świadczenia:", fmt(kwota), big=True)
        self._res_row(rb, "Liczba rat:", str(ilosc))
        self._res_row(rb, "Standardowa rata:", fmt(rata_base), color="#6fcf97")
        if abs(pierwsza - rata_base) > 0.005:
            self._res_row(rb, "Pierwsza rata wyrównująca:", fmt(pierwsza), color=GOLD_LT)
        ok_color = "#6fcf97" if abs(suma_kontrolna - kwota) < 0.01 else "#eb5757"
        self._res_row(rb, "Suma kontrolna:", fmt(suma_kontrolna), color=ok_color)
        tk.Label(rb, text="", bg=BG, height=1).pack()

        table_frame = tk.Frame(self.r_result_frame, bg=PANEL,
                               highlightthickness=1, highlightbackground=BORDER)
        table_frame.pack(fill="x", pady=(10, 0))

        hdr = tk.Frame(table_frame, bg=BG)
        hdr.pack(fill="x")
        for col, txt, w in [("Nr raty", 8, 0), ("Termin płatności", 18, 1), ("Kwota raty", 18, 2)]:
            tk.Label(hdr, text=col, font=self.f_small, bg=BG, fg=GOLD,
                     width=w, anchor="w").pack(side="left", padx=10, pady=6)

        for r in raty:
            bg_row = "#fffbf0" if r['wyrownujaca'] else PANEL
            row_f = tk.Frame(table_frame, bg=bg_row,
                             highlightthickness=0)
            row_f.pack(fill="x")
            tk.Frame(table_frame, bg=BORDER, height=1).pack(fill="x")

            nr_txt = f"{r['nr']}"
            if r['wyrownujaca']:
                nr_txt += "  ★"
            tk.Label(row_f, text=nr_txt, font=self.f_body if not r['wyrownujaca'] else self.f_bold,
                     bg=bg_row, fg=TEXT, width=8, anchor="w").pack(side="left", padx=10, pady=5)
            tk.Label(row_f, text=r['termin'], font=self.f_body,
                     bg=bg_row, fg=TEXT, width=18, anchor="w").pack(side="left", padx=10)
            tk.Label(row_f, text=fmt(r['kwota']), font=self.f_bold,
                     bg=bg_row, fg=GREEN if not r['wyrownujaca'] else RED,
                     width=18, anchor="w").pack(side="left", padx=10)

        foot = tk.Frame(table_frame, bg=BG)
        foot.pack(fill="x")
        tk.Label(foot, text="RAZEM", font=self.f_bold, bg=BG, fg=GOLD,
                 width=26, anchor="w").pack(side="left", padx=10, pady=6)
        tk.Label(foot, text=fmt(suma_kontrolna), font=self.f_bold,
                 bg=BG, fg=GOLD_LT).pack(side="left", padx=10)

        if abs(pierwsza - rata_base) > 0.005:
            tk.Label(self.r_result_frame,
                     text="★  Pierwsza rata wyrównuje resztę z podziału kwoty przez liczbę rat.",
                     font=self.f_small, bg=CREAM, fg=MUTED).pack(anchor="w", pady=(6, 0))

    # ═══════════════════════════════════════════════════════════════════════
    # ZAKŁADKA 3 – POZAODSETKOWE KOSZTY KREDYTU (art. 36a UKK)
    # ═══════════════════════════════════════════════════════════════════════
    def _tab_pkk(self, nb):
        outer = tk.Frame(nb, bg=CREAM)
        nb.add(outer, text="🏦  Koszty kredytu (art. 36a)")
        frame, _ = self._scrollable(outer)

        tk.Label(frame, text="Maksymalne pozaodsetkowe koszty kredytu",
                 font=self.f_sub, bg=CREAM, fg=TEXT).pack(anchor="w", padx=20, pady=(14, 2))
        tk.Label(frame,
                 text="Art. 36a ustawy z dnia 12 maja 2011 r. o kredycie konsumenckim (Dz.U. 2011 nr 126 poz. 715)",
                 font=self.f_small, bg=CREAM, fg=MUTED).pack(anchor="w", padx=20)

        info_card = self._card(frame, "Podstawa prawna i wzór", pady=14)
        info_card.columnconfigure(0, weight=1)

        ustawa_text = (
            "Art. 36a ust. 1 UKK:  MPKK ≤  (K × 25%)  +  (K × n/R × 30%)\n"
            "Art. 36a ust. 2 UKK:  dla umów ≤ 30 dni:  MPKK ≤  K × 5%\n"
            "Art. 36a ust. 3 UKK:  MPKK nie może przekroczyć całkowitej kwoty kredytu (K)\n\n"
            "gdzie:  K = całkowita kwota kredytu,  n = okres kredytowania w dniach,  R = liczba dni w roku (365)"
        )
        tk.Label(info_card, text=ustawa_text, font=self.f_small,
                 bg="#f0f4ff", fg="#2a2a5a", justify="left",
                 relief="flat", bd=0, padx=12, pady=10,
                 wraplength=820).grid(row=0, column=0, columnspan=4, sticky="ew")

        c = self._card(frame, "Dane umowy kredytowej", pady=10)
        c.columnconfigure(1, weight=1); c.columnconfigure(3, weight=1)

        self._lbl(c, "Całkowita kwota kredytu — K (PLN):", 0, 0)
        self.pkk_kwota = self._entry(c, 0, 1, width=16)
        self.pkk_kwota.insert(0, "10000")

        self._lbl(c, "Rodzaj umowy (okres):", 2, 0)
        self.pkk_rodzaj = self._combo(c,
            ["Powyżej 30 dni (art. 36a ust. 1)",
             "Do 30 dni włącznie (art. 36a ust. 2)"],
            row=0, col=3, width=32)
        self.pkk_rodzaj.bind("<<ComboboxSelected>>", lambda e: self._toggle_pkk_mode())

        self.pkk_okres_lbl = tk.Label(c, text="Okres kredytowania — n (dni):",
                                       font=self.f_small, bg=PANEL, fg=MUTED)
        self.pkk_okres_lbl.grid(row=1, column=0, sticky="w", pady=(6, 1))
        self.pkk_okres = self._entry(c, 1, 1, width=10)
        self.pkk_okres.insert(0, "365")

        self.pkk_okres_hint = tk.Label(c,
            text="Wpisz liczbę dni trwania umowy (np. 365 = 1 rok, 180 = pół roku)",
            font=self.f_small, bg=PANEL, fg=MUTED)
        self.pkk_okres_hint.grid(row=1, column=2, columnspan=2, sticky="w", padx=(8, 0))

        tk.Frame(c, bg=BORDER, height=1).grid(
            row=2, column=0, columnspan=4, sticky="ew", pady=(12, 8))

        self._lbl(c, "Rzeczywiście pobrane PKK (PLN):", 0, 3)
        self.pkk_pobrane = self._entry(c, 3, 1, width=16)
        self.pkk_pobrane.insert(0, "")
        tk.Label(c, text="(opcjonalnie — do oceny czy koszty nie przekraczają limitu)",
                 font=self.f_small, bg=PANEL, fg=MUTED).grid(
            row=3, column=2, columnspan=2, sticky="w", padx=(8, 0))

        btn_frame = tk.Frame(frame, bg=CREAM)
        btn_frame.pack(fill="x", padx=20, pady=10)
        self._btn(btn_frame, "🏦  Oblicz maksymalne koszty kredytu",
                  self._oblicz_pkk, gold=True).pack(pady=4)

        self.pkk_result_frame = tk.Frame(frame, bg=CREAM)
        self.pkk_result_frame.pack(fill="x", padx=20, pady=(0, 20))

        self._toggle_pkk_mode()

    def _toggle_pkk_mode(self):
        if self.pkk_rodzaj.current() == 1:
            self.pkk_okres_lbl.grid_remove()
            self.pkk_okres.grid_remove()
            self.pkk_okres_hint.grid_remove()
        else:
            self.pkk_okres_lbl.grid(row=1, column=0, sticky="w", pady=(6, 1))
            self.pkk_okres.grid(row=1, column=1, sticky="ew", padx=(4, 8), pady=2, ipady=4)
            self.pkk_okres_hint.grid(row=1, column=2, columnspan=2, sticky="w", padx=(8, 0))

    def _oblicz_pkk(self):
        try:
            K = float(self.pkk_kwota.get().replace(",", ".").replace(" ", ""))
        except ValueError:
            messagebox.showerror("Błąd", "Wpisz poprawną całkowitą kwotę kredytu.")
            return
        if K <= 0:
            messagebox.showerror("Błąd", "Kwota kredytu musi być większa od zera.")
            return

        do_30_dni = (self.pkk_rodzaj.current() == 1)

        pobrane_str = self.pkk_pobrane.get().replace(",", ".").replace(" ", "")
        pobrane = None
        if pobrane_str:
            try:
                pobrane = float(pobrane_str)
            except ValueError:
                messagebox.showerror("Błąd", "Wpisz poprawną kwotę rzeczywiście pobranych kosztów.")
                return

        R = 365

        if do_30_dni:
            skladnik_staly   = K * 0.05
            skladnik_zmienny = 0.0
            mpkk_przed_cap   = skladnik_staly
            n                = 30
            wzor_opis        = "MPKK = K × 5%"
        else:
            try:
                n = int(self.pkk_okres.get().strip())
            except ValueError:
                messagebox.showerror("Błąd", "Wpisz liczbę dni okresu kredytowania.")
                return
            if n <= 0:
                messagebox.showerror("Błąd", "Okres kredytowania musi być większy od zera.")
                return

            skladnik_staly   = K * 0.25
            skladnik_zmienny = K * (n / R) * 0.30
            mpkk_przed_cap   = skladnik_staly + skladnik_zmienny
            wzor_opis        = "MPKK = (K × 25%) + (K × n/R × 30%)"

        mpkk = min(mpkk_przed_cap, K)
        cap_zastosowany = mpkk_przed_cap > K

        for w in self.pkk_result_frame.winfo_children():
            w.destroy()

        rb = tk.Frame(self.pkk_result_frame, bg=BG)
        rb.pack(fill="x")

        tryb_txt = "do 30 dni (art. 36a ust. 2)" if do_30_dni else f"powyżej 30 dni — {n} dni (art. 36a ust. 1)"
        tk.Label(rb, text=f"  🏦  Wynik — umowa {tryb_txt}",
                 font=self.f_sub, bg=BG, fg=GOLD).pack(anchor="w", padx=16, pady=(12, 6))

        wzor_frame = tk.Frame(rb, bg="#0d0d1f")
        wzor_frame.pack(fill="x", padx=16, pady=(0, 8))
        tk.Label(wzor_frame, text=f"  {wzor_opis}",
                 font=font.Font(family="Courier New", size=11, weight="bold"),
                 bg="#0d0d1f", fg=GOLD_LT, pady=8).pack(anchor="w")

        self._res_row(rb, "Całkowita kwota kredytu (K):", fmt(K))
        if not do_30_dni:
            self._res_row(rb, "Okres kredytowania (n):", f"{n} dni")
            self._res_row(rb, f"Składnik stały  (K × 25%):", fmt(skladnik_staly), color="#aaaaff")
            self._res_row(rb, f"Składnik zmienny  (K × {n}/{R} × 30%):", fmt(skladnik_zmienny), color="#aaaaff")
            self._res_row(rb, "Suma przed limitem (ust. 3):", fmt(mpkk_przed_cap))
        else:
            self._res_row(rb, f"Składnik (K × 5%):", fmt(skladnik_staly), color="#aaaaff")

        tk.Frame(rb, bg=GOLD, height=2).pack(fill="x", padx=16, pady=8)

        if cap_zastosowany:
            self._res_row(rb,
                "⚠  Limit z art. 36a ust. 3 — MPKK obniżone do K:",
                fmt(mpkk), color="#eb5757", big=True)
            tk.Label(rb,
                     text="  Wyliczona kwota przekroczyła całkowitą kwotę kredytu — zastosowano cap z art. 36a ust. 3.",
                     font=self.f_small, bg=BG, fg="#eb5757", pady=4).pack(anchor="w", padx=16)
        else:
            self._res_row(rb,
                "✅  Maksymalne pozaodsetkowe koszty kredytu (MPKK):",
                fmt(mpkk), color=GOLD_LT, big=True)

        if pobrane is not None:
            tk.Frame(rb, bg="#333355", height=1).pack(fill="x", padx=16, pady=8)
            nadwyzka = pobrane - mpkk
            if nadwyzka > 0:
                self._res_row(rb, "Rzeczywiście pobrane PKK:", fmt(pobrane), color="#eb5757")
                self._res_row(rb,
                    "❌  PRZEKROCZENIE limitu o:",
                    fmt(nadwyzka), color="#eb5757")
                tk.Label(rb,
                         text="  Pobrane koszty PRZEKRACZAJĄ ustawowy limit z art. 36a UKK.",
                         font=self.f_bold, bg=BG, fg="#eb5757", pady=6).pack(anchor="w", padx=16)
            elif abs(nadwyzka) < 0.005:
                self._res_row(rb, "Rzeczywiście pobrane PKK:", fmt(pobrane), color="#6fcf97")
                tk.Label(rb,
                         text="  Pobrane koszty równają się dokładnie ustawowemu limitowi.",
                         font=self.f_bold, bg=BG, fg="#6fcf97", pady=6).pack(anchor="w", padx=16)
            else:
                self._res_row(rb, "Rzeczywiście pobrane PKK:", fmt(pobrane), color="#6fcf97")
                self._res_row(rb, "Margines poniżej limitu:", fmt(-nadwyzka), color="#6fcf97")
                tk.Label(rb,
                         text="  Pobrane koszty mieszczą się w ustawowym limicie z art. 36a UKK.",
                         font=self.f_bold, bg=BG, fg="#6fcf97", pady=6).pack(anchor="w", padx=16)

        tk.Label(rb, text="", bg=BG, height=1).pack()

    # ═══════════════════════════════════════════════════════════════════════
    # ZAKŁADKA 4 – AKTUALIZACJA OPŁATY ROCZNEJ (art. 77 UGN)
    # ═══════════════════════════════════════════════════════════════════════
    def _tab_oplata_roczna(self, nb):
        outer = tk.Frame(nb, bg=CREAM)
        nb.add(outer, text="📅  Aktualizacja opłaty rocznej")
        frame, _ = self._scrollable(outer)

        tk.Label(frame, text="Aktualizacja opłaty rocznej z tytułu użytkowania wieczystego",
                 font=self.f_sub, bg=CREAM, fg=TEXT).pack(anchor="w", padx=20, pady=(14, 2))
        tk.Label(frame,
                 text="Art. 77–81 ustawy z dnia 21 sierpnia 1997 r. o gospodarce nieruchomościami (Dz.U. 1997 nr 115 poz. 741)",
                 font=self.f_small, bg=CREAM, fg=MUTED).pack(anchor="w", padx=20)

        ic = self._card(frame, "Zasady aktualizacji (art. 77–81 UGN)", pady=14)
        ic.columnconfigure(0, weight=1)
        ustawa_text = (
            "Art. 77 ust. 1:  Właściciel może zaktualizować opłatę roczną z urzędu lub na wniosek, "
            "nie częściej niż raz na 3 lata, jeżeli wartość nieruchomości uległa zmianie.\n\n"
            "Art. 77 ust. 2a:  Wzrost opłaty rocznej w wyniku aktualizacji nie może przekroczyć:\n"
            "    • w 1. roku po aktualizacji: dotychczasowej opłaty + różnica × 1/3  (próg I)\n"
            "    • w 2. roku po aktualizacji: dotychczasowej opłaty + różnica × 2/3  (próg II)\n"
            "    • od 3. roku: pełna nowa opłata\n\n"
            "Art. 77 ust. 2b:  Jeżeli zaktualizowana opłata jest niższa od dotychczasowej — nową stosuje się od razu.\n"
            "Art. 77 ust. 3:   Nowa opłata = wartość nieruchomości × stawka procentowa."
        )
        tk.Label(ic, text=ustawa_text, font=self.f_small,
                 bg="#f0f4ff", fg="#2a2a5a", justify="left",
                 relief="flat", bd=0, padx=12, pady=10,
                 wraplength=820).grid(row=0, column=0, sticky="ew")

        c = self._card(frame, "Dane nieruchomości i opłaty", pady=10)
        c.columnconfigure(1, weight=1); c.columnconfigure(3, weight=1)

        self._lbl(c, "Dotychczasowa opłata roczna (PLN):", 0, 0)
        self.or_oplata_dotychczasowa = self._entry(c, 0, 1, width=16)
        self.or_oplata_dotychczasowa.insert(0, "")

        self._lbl(c, "Data ostatniej aktualizacji / ustanowienia:", 2, 0)
        self.or_data_ostatniej = self._entry(c, 0, 3, width=16)
        self.or_data_ostatniej.insert(0, "")
        tk.Label(c, text="(RRRR-MM-DD, opcjonalnie — do weryfikacji 3-letniego okresu)",
                 font=self.f_small, bg=PANEL, fg=MUTED).grid(
            row=1, column=2, columnspan=2, sticky="w", padx=(8, 0), pady=(0, 4))

        tk.Frame(c, bg=BORDER, height=1).grid(
            row=2, column=0, columnspan=4, sticky="ew", pady=(8, 8))

        self._lbl(c, "Nowa wartość nieruchomości wg operatu (PLN):", 0, 3)
        self.or_wartosc = self._entry(c, 3, 1, width=16)
        self.or_wartosc.insert(0, "")

        self._lbl(c, "Dotychczasowa wartość nieruchomości (PLN):", 2, 3)
        self.or_wartosc_stara = self._entry(c, 3, 3, width=16)
        self.or_wartosc_stara.insert(0, "")
        tk.Label(c, text="(opcjonalnie — do weryfikacji zgodności dotychczasowej opłaty ze stawką)",
                 font=self.f_small, bg=PANEL, fg=MUTED).grid(
            row=4, column=0, columnspan=4, sticky="w", padx=(0, 0), pady=(0, 4))

        tk.Frame(c, bg=BORDER, height=1).grid(
            row=5, column=0, columnspan=4, sticky="ew", pady=(4, 8))

        self._lbl(c, "Stawka procentowa opłaty (%):", 0, 6)

        stawka_frame = tk.Frame(c, bg=PANEL)
        stawka_frame.grid(row=6, column=1, columnspan=3, sticky="ew", padx=(4, 0))
        stawka_frame.columnconfigure(2, weight=1)

        self.or_stawka = tk.Entry(stawka_frame, font=self.f_body, relief="flat", bd=0,
                                   bg=CREAM, fg=TEXT, width=8,
                                   highlightthickness=1, highlightbackground=BORDER)
        self.or_stawka.grid(row=0, column=0, sticky="w", ipady=4, padx=(0, 10))
        self.or_stawka.insert(0, "1")

        tk.Label(stawka_frame, text="Szybki wybór:", font=self.f_small,
                 bg=PANEL, fg=MUTED).grid(row=0, column=1, sticky="w", padx=(0, 6))

        stawki_btn_frame = tk.Frame(stawka_frame, bg=PANEL)
        stawki_btn_frame.grid(row=0, column=2, sticky="w")

        stawki = [
            ("0,3% — ochrona przyrody", "0.3"),
            ("1% — mieszkaniowy", "1"),
            ("2% — usługowy/rekreacja", "2"),
            ("3% — działalność gosp.", "3"),
        ]
        for txt, val in stawki:
            def make_cmd(v=val):
                def cmd():
                    self.or_stawka.delete(0, "end")
                    self.or_stawka.insert(0, v)
                return cmd
            tk.Button(stawki_btn_frame, text=txt, command=make_cmd(),
                      bg="#eeeeee", fg=TEXT, font=self.f_small,
                      relief="flat", cursor="hand2", padx=8, pady=3,
                      activebackground=GOLD_LT).pack(side="left", padx=(0, 4))

        tk.Frame(c, bg=BORDER, height=1).grid(
            row=7, column=0, columnspan=4, sticky="ew", pady=(10, 8))
        self._lbl(c, "Data aktualizacji (RRRR-MM-DD):", 0, 8)
        self.or_data_aktualizacji = self._entry(c, 8, 1, width=16)
        self.or_data_aktualizacji.insert(0, date.today().strftime("%Y-%m-%d"))
        tk.Label(c, text="Używana do wyliczenia harmonogramu stopniowania opłaty",
                 font=self.f_small, bg=PANEL, fg=MUTED).grid(
            row=8, column=2, columnspan=2, sticky="w", padx=(8, 0))

        btn_frame = tk.Frame(frame, bg=CREAM)
        btn_frame.pack(fill="x", padx=20, pady=10)
        self._btn(btn_frame, "📅  Oblicz zaktualizowaną opłatę",
                  self._oblicz_oplata_roczna, gold=True).pack(pady=4)

        self.or_result_frame = tk.Frame(frame, bg=CREAM)
        self.or_result_frame.pack(fill="x", padx=20, pady=(0, 20))

    def _oblicz_oplata_roczna(self):
        def parse_num(entry, nazwa):
            s = entry.get().replace(",", ".").replace(" ", "").replace("\xa0", "")
            if not s:
                return None
            try:
                v = float(s)
                if v < 0:
                    raise ValueError
                return v
            except ValueError:
                messagebox.showerror("Błąd", f"Wpisz poprawną wartość: {nazwa}")
                return "ERR"

        oplata_dotychczasowa = parse_num(self.or_oplata_dotychczasowa, "Dotychczasowa opłata roczna")
        if oplata_dotychczasowa == "ERR": return
        if oplata_dotychczasowa is None:
            messagebox.showerror("Błąd", "Podaj dotychczasową opłatę roczną.")
            return

        wartosc_nowa = parse_num(self.or_wartosc, "Nowa wartość nieruchomości")
        if wartosc_nowa == "ERR": return
        if wartosc_nowa is None:
            messagebox.showerror("Błąd", "Podaj nową wartość nieruchomości wg operatu.")
            return

        wartosc_stara = parse_num(self.or_wartosc_stara, "Dotychczasowa wartość nieruchomości")
        if wartosc_stara == "ERR": return

        stawka_str = self.or_stawka.get().replace(",", ".").replace(" ", "")
        try:
            stawka = float(stawka_str)
            if stawka <= 0 or stawka > 100:
                raise ValueError
        except ValueError:
            messagebox.showerror("Błąd", "Wpisz poprawną stawkę procentową (np. 1 lub 1,5).")
            return

        data_akt_str = self.or_data_aktualizacji.get().strip()
        try:
            data_akt = datetime.strptime(data_akt_str, "%Y-%m-%d").date()
        except ValueError:
            data_akt = date.today()

        data_ostatniej_str = self.or_data_ostatniej.get().strip()
        data_ostatniej = None
        if data_ostatniej_str:
            try:
                data_ostatniej = datetime.strptime(data_ostatniej_str, "%Y-%m-%d").date()
            except ValueError:
                pass

        stawka_ulamek = stawka / 100.0
        oplata_nowa = wartosc_nowa * stawka_ulamek

        oplata_z_wartosci_starej = None
        if wartosc_stara is not None:
            oplata_z_wartosci_starej = wartosc_stara * stawka_ulamek

        roznica = oplata_nowa - oplata_dotychczasowa
        spadek = oplata_nowa <= oplata_dotychczasowa

        if not spadek:
            prog1 = oplata_dotychczasowa + roznica * (1 / 3)
            prog2 = oplata_dotychczasowa + roznica * (2 / 3)
        else:
            prog1 = oplata_nowa
            prog2 = oplata_nowa

        weryfikacja_3lat = None
        if data_ostatniej is not None:
            delta = relativedelta(data_akt, data_ostatniej)
            lata = delta.years
            miesiace_extra = delta.months
            weryfikacja_3lat = (lata, miesiace_extra, lata >= 3)

        for w in self.or_result_frame.winfo_children():
            w.destroy()

        rb = tk.Frame(self.or_result_frame, bg=BG)
        rb.pack(fill="x")

        tk.Label(rb, text="  📅  Wynik aktualizacji opłaty rocznej (art. 77 UGN)",
                 font=self.f_sub, bg=BG, fg=GOLD).pack(anchor="w", padx=16, pady=(12, 6))

        if weryfikacja_3lat is not None:
            l, m, ok = weryfikacja_3lat
            kolor_3lat = "#6fcf97" if ok else "#eb5757"
            znak = "✅" if ok else "⚠"
            msg = f"{znak}  Od ostatniej aktualizacji minęło {l} lat i {m} mies. — {'warunek 3 lat spełniony' if ok else 'warunek 3 lat NIE spełniony (art. 77 ust. 1)'}"
            tk.Label(rb, text=f"  {msg}", font=self.f_bold,
                     bg=BG, fg=kolor_3lat, pady=4).pack(anchor="w", padx=16)
            tk.Frame(rb, bg="#333355", height=1).pack(fill="x", padx=16, pady=4)

        self._res_row(rb, "Nowa wartość nieruchomości (operat):", fmt(wartosc_nowa))
        self._res_row(rb, f"Stawka procentowa:", f"{stawka:.2f}%".replace(".", ","))
        if oplata_z_wartosci_starej is not None:
            kol = "#6fcf97" if abs(oplata_z_wartosci_starej - oplata_dotychczasowa) < 0.05 else "#eb5757"
            self._res_row(rb,
                f"Opłata wynikająca z wartości poprzedniej ({fmt(wartosc_stara)} × {stawka:.2f}%):",
                fmt(oplata_z_wartosci_starej), color=kol)
        self._res_row(rb, "Dotychczasowa opłata roczna:", fmt(oplata_dotychczasowa))

        tk.Frame(rb, bg=GOLD, height=2).pack(fill="x", padx=16, pady=8)

        self._res_row(rb,
            f"Nowa opłata roczna  ({fmt(wartosc_nowa)} × {stawka:.2f}%):",
            fmt(oplata_nowa), color=GOLD_LT, big=True)

        kolor_diff = "#6fcf97" if roznica <= 0 else "#eb5757"
        znak_diff = "▼" if roznica <= 0 else "▲"
        self._res_row(rb, f"{znak_diff}  Zmiana opłaty:",
                      f"{'+' if roznica > 0 else ''}{fmt(roznica)}", color=kolor_diff)

        tk.Frame(rb, bg="#333355", height=1).pack(fill="x", padx=16, pady=10)

        if spadek:
            tk.Label(rb,
                     text="  ℹ  Nowa opłata jest niższa od dotychczasowej — stosuje się ją w pełnej wysokości od razu (art. 77 ust. 2b).",
                     font=self.f_bold, bg=BG, fg="#6fcf97", wraplength=820,
                     justify="left", pady=6).pack(anchor="w", padx=16)
        else:
            tk.Label(rb,
                     text="  📆  Harmonogram stopniowania wzrostu opłaty (art. 77 ust. 2a):",
                     font=self.f_bold, bg=BG, fg=GOLD, pady=4).pack(anchor="w", padx=16)

            tbl = tk.Frame(rb, bg="#0d0d1f")
            tbl.pack(fill="x", padx=16, pady=(4, 8))

            hdr = tk.Frame(tbl, bg="#2d2d4a")
            hdr.pack(fill="x")
            for txt, w in [("Rok", 6), ("Rok kalendarzowy", 18), ("Opłata roczna", 20), ("Zmiana względem dotychcz.", 26)]:
                tk.Label(hdr, text=txt, font=self.f_small, bg="#2d2d4a", fg=GOLD,
                         width=w, anchor="w").pack(side="left", padx=10, pady=6)

            rok_akt = data_akt.year

            wiersze = [
                (1, rok_akt + 1, prog1,     oplata_dotychczasowa, "I — wzrost do 1/3 różnicy"),
                (2, rok_akt + 2, prog2,     oplata_dotychczasowa, "II — wzrost do 2/3 różnicy"),
                (3, rok_akt + 3, oplata_nowa, oplata_dotychczasowa, "III+ — pełna nowa opłata"),
            ]

            for nr, rok_kal, oplata_w, baza, opis in wiersze:
                bg_w = PANEL if nr % 2 == 0 else "#f9f9f9"
                row_f = tk.Frame(tbl, bg=bg_w)
                row_f.pack(fill="x")
                tk.Frame(tbl, bg=BORDER, height=1).pack(fill="x")

                diff_w = oplata_w - baza
                tk.Label(row_f, text=str(nr), font=self.f_bold,
                         bg=bg_w, fg=TEXT, width=6, anchor="w").pack(side="left", padx=10, pady=6)
                tk.Label(row_f, text=f"{rok_kal}  ({opis})", font=self.f_body,
                         bg=bg_w, fg=TEXT, width=18, anchor="w").pack(side="left", padx=10)
                tk.Label(row_f, text=fmt(oplata_w), font=self.f_bold,
                         bg=bg_w, fg=GREEN, width=20, anchor="w").pack(side="left", padx=10)
                tk.Label(row_f, text=f"+{fmt(diff_w)}", font=self.f_body,
                         bg=bg_w, fg="#888888", width=26, anchor="w").pack(side="left", padx=10)

        tk.Label(rb, text="", bg=BG, height=1).pack()

    # ═══════════════════════════════════════════════════════════════════════
    # ZAKŁADKA 5 – KALKULATOR DAT
    # ═══════════════════════════════════════════════════════════════════════
    def _tab_daty(self, nb):
        outer = tk.Frame(nb, bg=CREAM)
        nb.add(outer, text="🗓  Kalkulator dat")
        frame, _ = self._scrollable(outer)

        tk.Label(frame, text="Kalkulator terminów procesowych",
                 font=self.f_sub, bg=CREAM, fg=TEXT).pack(anchor="w", padx=20, pady=(14, 2))
        tk.Label(frame,
                 text="KPC · KC · art. 115 KC — koniec terminu w dniu wolnym przesuwa się na najbliższy dzień roboczy",
                 font=self.f_small, bg=CREAM, fg=MUTED).pack(anchor="w", padx=20)

        DNI_PL = ["poniedziałek", "wtorek", "środa", "czwartek",
                  "piątek", "sobota", "niedziela"]

        def fmt_date(d):
            return f"{d.strftime('%d.%m.%Y')}  ({DNI_PL[d.weekday()]})"

        def parse_date_field(entry, name):
            s = entry.get().strip()
            for fs in ("%Y-%m-%d", "%d.%m.%Y", "%d-%m-%Y", "%d/%m/%Y"):
                try:
                    return datetime.strptime(s, fs).date()
                except ValueError:
                    continue
            messagebox.showerror("Błąd daty",
                f"Nieprawidłowa data: {name}\nWpisz w formacie RRRR-MM-DD lub DD.MM.RRRR")
            return None

        def next_workday(d):
            while d.weekday() >= 5:
                d += relativedelta(days=1)
            return d

        def add_days_115(start, days):
            return next_workday(start + relativedelta(days=days))

        def add_months_115(start, months):
            return next_workday(start + relativedelta(months=months))

        def add_years_115(start, years):
            return next_workday(start + relativedelta(years=years))

        self.dt_result_frame = tk.Frame(frame, bg=CREAM)

        def clear_results():
            for w in self.dt_result_frame.winfo_children():
                w.destroy()
            self.dt_result_frame.pack(fill="x", padx=20, pady=(4, 20))

        def show_result(title, rows_data):
            clear_results()
            rb = tk.Frame(self.dt_result_frame, bg=BG)
            rb.pack(fill="x")
            tk.Label(rb, text=f"  🗓  {title}",
                     font=self.f_sub, bg=BG, fg=GOLD).pack(anchor="w", padx=16, pady=(12, 6))

            for label, val, note, color in rows_data:
                row_f = tk.Frame(rb, bg=BG)
                row_f.pack(fill="x", padx=16, pady=2)
                tk.Label(row_f, text=label, font=self.f_body,
                         bg=BG, fg="#aaaaaa", anchor="w").pack(side="left")
                val_str = fmt_date(val) if isinstance(val, date) else str(val)
                fc = color if color else GOLD_LT
                tk.Label(row_f, text=val_str, font=self.f_result,
                         bg=BG, fg=fc).pack(side="right")
                tk.Frame(rb, bg="#2d2d4a", height=1).pack(fill="x", padx=16)
                if note:
                    tk.Label(rb, text=f"    ↳ {note}",
                             font=self.f_small, bg=BG, fg="#888888",
                             justify="left", wraplength=800).pack(
                        anchor="w", padx=16, pady=(0, 3))
            tk.Label(rb, text="", bg=BG, height=1).pack()

        def date_row(parent, row, label, hint="RRRR-MM-DD lub DD.MM.RRRR"):
            tk.Label(parent, text=label, font=self.f_small,
                     bg=PANEL, fg=MUTED).grid(
                row=row, column=0, sticky="w", pady=(6, 1), padx=(0, 8))
            e = tk.Entry(parent, font=self.f_body, relief="flat", bd=0,
                         bg=CREAM, fg=TEXT, width=17,
                         highlightthickness=1, highlightbackground=BORDER)
            e.grid(row=row, column=1, sticky="w", padx=(4, 8), pady=2, ipady=4)
            e.insert(0, date.today().strftime("%Y-%m-%d"))
            tk.Label(parent, text=hint, font=self.f_small,
                     bg=PANEL, fg="#aaaaaa").grid(row=row, column=2, sticky="w")
            return e

        def combo_row(parent, row, label, values, default=0):
            tk.Label(parent, text=label, font=self.f_small,
                     bg=PANEL, fg=MUTED).grid(
                row=row, column=0, sticky="w", pady=(6, 1))
            cb = ttk.Combobox(parent, values=values, state="readonly",
                              font=self.f_body, width=46)
            cb.current(default)
            cb.grid(row=row, column=1, columnspan=2, sticky="w",
                    padx=(4, 8), pady=2, ipady=2)
            return cb

        def calc_btn(parent, row, text, cmd):
            self._btn(parent, text, cmd, gold=True).grid(
                row=row, column=0, columnspan=3, sticky="w", pady=(10, 4))

        # KARTA 1 — PRAWOMOCNOŚĆ
        c1 = self._card(frame, "1.  Termin prawomocności orzeczenia  (art. 363 §1 KPC)", pady=14)
        c1.columnconfigure(2, weight=1)

        info1 = tk.Frame(c1, bg="#f0f4ff")
        info1.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 8))
        tk.Label(info1, text=(
            "Prawomocność zależy od tego, czy strona złożyła wniosek o uzasadnienie:\n"
            "• Brak wniosku o uzasadnienie → termin 7 dni od ogłoszenia / doręczenia orzeczenia  (art. 369 §2 KPC)\n"
            "• Złożono wniosek o uzasadnienie → termin biegnie od doręczenia orzeczenia z uzasadnieniem:\n"
            "     – apelacja: 14 dni  (art. 369 §1 KPC)\n"
            "     – zażalenie: 7 dni  (art. 394 §2 KPC)\n"
            "We wszystkich przypadkach stosuje się art. 115 KC.\n"
            "Uwaga: orzeczenia sądu II instancji są prawomocne z chwilą wydania (art. 363 §1 KPC).\n"
            "Skarga kasacyjna i skarga o wznowienie postępowania nie wstrzymują prawomocności — nie są objęte tym kalkulatorem."
        ), font=self.f_small, bg="#f0f4ff", fg="#2a2a5a",
           justify="left", wraplength=840, padx=12, pady=8).pack(anchor="w")

        tk.Label(c1, text="Czy złożono wniosek o uzasadnienie?",
                 font=self.f_small, bg=PANEL, fg=MUTED).grid(
            row=1, column=0, sticky="w", pady=(4, 2))

        p1_tryb = tk.StringVar(value="bez_uzas")
        tryb_frame = tk.Frame(c1, bg=PANEL)
        tryb_frame.grid(row=1, column=1, columnspan=2, sticky="w", padx=(4, 0))
        tk.Radiobutton(tryb_frame, text="NIE — termin 7 dni od ogłoszenia/doręczenia",
                       variable=p1_tryb, value="bez_uzas",
                       bg=PANEL, font=self.f_body,
                       command=lambda: _toggle_p1()).pack(side="left")
        tk.Radiobutton(tryb_frame, text="TAK — termin od doręczenia z uzasadnieniem",
                       variable=p1_tryb, value="z_uzas",
                       bg=PANEL, font=self.f_body,
                       command=lambda: _toggle_p1()).pack(side="left", padx=(20, 0))

        p1_frame_a = tk.Frame(c1, bg=PANEL)
        p1_frame_a.grid(row=2, column=0, columnspan=3, sticky="ew")
        p1_frame_a.columnconfigure(2, weight=1)

        tk.Label(p1_frame_a, text="Data ogłoszenia / doręczenia orzeczenia:",
                 font=self.f_small, bg=PANEL, fg=MUTED).grid(
            row=0, column=0, sticky="w", pady=(6, 1), padx=(0, 8))
        e1a = tk.Entry(p1_frame_a, font=self.f_body, relief="flat", bd=0,
                       bg=CREAM, fg=TEXT, width=17,
                       highlightthickness=1, highlightbackground=BORDER)
        e1a.grid(row=0, column=1, sticky="w", padx=(4, 8), pady=2, ipady=4)
        e1a.insert(0, date.today().strftime("%Y-%m-%d"))
        tk.Label(p1_frame_a, text="RRRR-MM-DD lub DD.MM.RRRR",
                 font=self.f_small, bg=PANEL, fg="#aaaaaa").grid(row=0, column=2, sticky="w")

        p1_frame_b = tk.Frame(c1, bg=PANEL)
        p1_frame_b.grid(row=2, column=0, columnspan=3, sticky="ew")
        p1_frame_b.columnconfigure(2, weight=1)

        tk.Label(p1_frame_b, text="Data doręczenia orzeczenia z uzasadnieniem:",
                 font=self.f_small, bg=PANEL, fg=MUTED).grid(
            row=0, column=0, sticky="w", pady=(6, 1), padx=(0, 8))
        e1b = tk.Entry(p1_frame_b, font=self.f_body, relief="flat", bd=0,
                       bg=CREAM, fg=TEXT, width=17,
                       highlightthickness=1, highlightbackground=BORDER)
        e1b.grid(row=0, column=1, sticky="w", padx=(4, 8), pady=2, ipady=4)
        e1b.insert(0, date.today().strftime("%Y-%m-%d"))
        tk.Label(p1_frame_b, text="RRRR-MM-DD lub DD.MM.RRRR",
                 font=self.f_small, bg=PANEL, fg="#aaaaaa").grid(row=0, column=2, sticky="w")

        tk.Label(p1_frame_b, text="Rodzaj środka zaskarżenia:",
                 font=self.f_small, bg=PANEL, fg=MUTED).grid(
            row=1, column=0, sticky="w", pady=(6, 1))
        cb1b = ttk.Combobox(p1_frame_b, state="readonly", font=self.f_body, width=46,
                             values=[
                                 "Apelacja — 14 dni  (art. 369 §1 KPC)",
                                 "Zażalenie — 7 dni  (art. 394 §2 KPC)",
                             ])
        cb1b.current(0)
        cb1b.grid(row=1, column=1, columnspan=2, sticky="w", padx=(4, 8), pady=2, ipady=2)

        def _toggle_p1():
            if p1_tryb.get() == "bez_uzas":
                p1_frame_b.grid_remove()
                p1_frame_a.grid(row=2, column=0, columnspan=3, sticky="ew")
            else:
                p1_frame_a.grid_remove()
                p1_frame_b.grid(row=2, column=0, columnspan=3, sticky="ew")

        _toggle_p1()

        def oblicz_prawomocnosc():
            tryb = p1_tryb.get()
            rows = []

            if tryb == "bez_uzas":
                d = parse_date_field(e1a, "data ogłoszenia/doręczenia orzeczenia")
                if not d: return
                surowy = d + relativedelta(days=7)
                po_115 = next_workday(surowy)
                prawomocny = po_115 + relativedelta(days=1)
                rows = [
                    ("Ogłoszenie / doręczenie orzeczenia:", d, None, None),
                    ("Ostatni dzień terminu na środek zaskarżenia (7 dni):", surowy,
                     "Art. 369 §2 KPC — gdy strona nie wniosła o uzasadnienie, termin do zaskarżenia wynosi 7 dni od ogłoszenia/doręczenia.", None),
                ]
                if po_115 != surowy:
                    rows.append(("Po art. 115 KC (dzień wolny → roboczy):", po_115,
                                 "Koniec terminu przesunięty na pierwszy dzień roboczy.", GOLD_LT))
                rows.append(("Dzień uprawomocnienia się orzeczenia:", prawomocny,
                             "Orzeczenie prawomocne z upływem dnia następnego po ostatnim dniu terminu.",
                             "#6fcf97"))
                show_result("Prawomocność — brak wniosku o uzasadnienie", rows)

            else:
                d = parse_date_field(e1b, "data doręczenia orzeczenia z uzasadnieniem")
                if not d: return
                idx = cb1b.current()
                if idx == 0:
                    surowy = d + relativedelta(days=14)
                    opis = "14 dni — apelacja (art. 369 §1 KPC)"
                else:
                    surowy = d + relativedelta(days=7)
                    opis = "7 dni — zażalenie (art. 394 §2 KPC)"
                po_115 = next_workday(surowy)
                prawomocny = po_115 + relativedelta(days=1)
                rows = [
                    ("Doręczenie orzeczenia z uzasadnieniem:", d, None, None),
                    (f"Ostatni dzień terminu na środek zaskarżenia ({opis}):", surowy,
                     "Termin biegnie od daty doręczenia odpisu orzeczenia wraz z uzasadnieniem.", None),
                ]
                if po_115 != surowy:
                    rows.append(("Po art. 115 KC (dzień wolny → roboczy):", po_115,
                                 "Koniec terminu przesunięty na pierwszy dzień roboczy.", GOLD_LT))
                rows.append(("Dzień uprawomocnienia się orzeczenia:", prawomocny,
                             "Orzeczenie prawomocne z upływem dnia następnego po ostatnim dniu terminu.",
                             "#6fcf97"))
                show_result("Prawomocność — wniosek o uzasadnienie złożony", rows)

        calc_btn(c1, 3, "🗓  Oblicz prawomocność", oblicz_prawomocnosc)

        # KARTA 3 — WYMAGALNOŚĆ
        c3 = self._card(frame, "2.  Termin wymagalności roszczenia  (art. 455 KC)", pady=10)
        c3.columnconfigure(2, weight=1)

        e3 = date_row(c3, 0, "Ostatni dzień terminu zapłaty:",
                      hint="data wskazana w wezwaniu / fakturze / orzeczeniu")

        def oblicz_wymagalnosc():
            d = parse_date_field(e3, "termin zapłaty")
            if not d: return
            wymagalnosc = d + relativedelta(days=1)
            wymagalnosc_rb = next_workday(wymagalnosc)
            rows = [
                ("Ostatni dzień terminu zapłaty:", d, None, None),
                ("Wymagalność roszczenia od:", wymagalnosc,
                 "Art. 455 KC — jeżeli termin nie został oznaczony, świadczenie powinno być spełnione niezwłocznie; "
                 "roszczenie staje się wymagalne nazajutrz po upływie terminu.", None),
                ("Pierwszy dzień naliczania odsetek za opóźnienie:", wymagalnosc,
                 "Art. 481 §1 KC — odsetki za opóźnienie należą się od dnia wymagalności, tj. dnia następnego po terminie zapłaty.",
                 "#6fcf97"),
            ]
            if wymagalnosc_rb != wymagalnosc:
                rows.append(("Uwaga — art. 115 KC (termin zapłaty w dzień wolny):", wymagalnosc_rb,
                             "Jeżeli sam termin zapłaty był wyznaczony na dzień wolny, dłużnik może spełnić świadczenie "
                             "w pierwszym dniu roboczym — odsetki nalicza się od tego dnia.", GOLD_LT))
            show_result("Termin wymagalności", rows)

        calc_btn(c3, 1, "🗓  Oblicz wymagalność", oblicz_wymagalnosc)

        # KARTA 4 — KOMORNIK
        c4 = self._card(frame, "3.  Zawieszenie i umorzenie postępowania sądowego (art. 177 k.p.c.)", pady=10)
        c4.columnconfigure(2, weight=1)

        e4 = date_row(c4, 0, "Data doręczenia powodowi zobowiązania:",
                      hint="data skutecznego doręczenia wezwania komorniczego")

        tk.Label(c4,
                 text="(art. 177 KPC w zw. z art. 139(1) k.p.c.: zawieszenie po 2 mies.; art. 182 pkt 1 KPC: umorzenie po 3 mies. od zawieszenia)",
                 font=self.f_small, bg=PANEL, fg=MUTED).grid(
            row=1, column=0, columnspan=3, sticky="w", pady=(2, 6))

        def oblicz_komornik():
            d = parse_date_field(e4, "data doręczenia zobowiązania")
            if not d: return
            zauieszenie_raw = d + relativedelta(months=2)
            zawieszenie     = next_workday(zauieszenie_raw)
            umorzenie_raw   = zawieszenie + relativedelta(months=3)
            umorzenie       = next_workday(umorzenie_raw)
            rows = [
                ("Data doręczenia zobowiązania dłużnikowi:", d, None, None),
                ("Termin zawieszenia egzekucji:", zawieszenie,
                 "Art. 823 KPC — komornik zawiesza postępowanie z urzędu, jeżeli wierzyciel w ciągu 2 miesięcy "
                 "od doręczenia dłużnikowi zobowiązania nie złożył wniosku o podjęcie egzekucji.", "#eb5757"),
            ]
            if zawieszenie != zauieszenie_raw:
                rows.append(("  (surowy termin zawieszenia):", zauieszenie_raw,
                             "Przesunięty wg art. 115 KC.", None))
            rows.append(("Termin umorzenia egzekucji:", umorzenie,
                         "Art. 825 pkt 4 KPC — sąd lub komornik umarza postępowanie, "
                         "jeśli wierzyciel w ciągu 3 miesięcy od daty zawieszenia "
                         "nie złożył wniosku o podjęcie.", "#eb5757"))
            if umorzenie != umorzenie_raw:
                rows.append(("  (surowy termin umorzenia):", umorzenie_raw,
                             "Przesunięty wg art. 115 KC.", None))
            show_result("Terminy egzekucji komorniczej", rows)

        calc_btn(c4, 2, "🗓  Oblicz terminy", oblicz_komornik)

        # KARTA 5 — ZASIEDZENIE
        c5 = self._card(frame, "4.  Termin zasiedzenia  (art. 172–176 KC + przepisy intertemporalne)", pady=10)
        c5.columnconfigure(2, weight=1)

        info_frame = tk.Frame(c5, bg="#f0f4ff")
        info_frame.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 8))
        tk.Label(info_frame,
                 text=(
                     "Przepisy intertemporalne — nowelizacja KC z 1.10.1990 r. (Dz.U. 1990 nr 55 poz. 321):\n"
                     "• Przed 1.10.1990 r. (stare KC):  nieruchomość: dobra wiara 10 lat / zła wiara 20 lat\n"
                     "• Od 1.10.1990 r. (nowe KC art. 172):  nieruchomość: dobra wiara 20 lat / zła wiara 30 lat\n"
                     "• Art. XLII §2 przepisów wprowadzających KC (PWKC):  jeżeli zasiedzenie rozpoczęło się przed wejściem w życie KC (1.01.1965), "
                     "stosuje się nowe przepisy; jeżeli jednak dawniejszy termin upływa wcześniej — stosuje się termin dawny.\n"
                     "• Reguła z uchwały SN (dot. nowelizacji 1990 r.):  do biegu terminu który rozpoczął się przed 1.10.1990 r. "
                     "stosuje się nowe, dłuższe terminy; jeżeli jednak stary (krótszy) termin upłynąłby przed 1.10.1990 r. — zasiedzenie nastąpiło już wtedy.\n"
                     "• Kalkulator pokazuje OBA warianty i wskazuje który ma zastosowanie."
                 ),
                 font=self.f_small, bg="#f0f4ff", fg="#2a2a5a",
                 justify="left", wraplength=840, padx=12, pady=8).pack(anchor="w")

        e5 = date_row(c5, 1, "Data objęcia w posiadanie samoistne:")

        cb5_rodzaj = combo_row(c5, 2, "Przedmiot i rodzaj posiadania:", [
            "Nieruchomość — dobra wiara",
            "Nieruchomość — zła wiara",
            "Ruchomość — dobra wiara  (art. 174 KC: 3 lata)",
        ])

        tk.Label(c5,
                 text="(dla ruchomości nie stosuje się przepisów intertemporalnych 1990 r. — tylko 3 lata dobrej wiary)",
                 font=self.f_small, bg=PANEL, fg=MUTED).grid(
            row=3, column=0, columnspan=3, sticky="w", pady=(0, 4))

        GRANICA_1990 = date(1990, 10, 1)

        def oblicz_zasiedzenie():
            d = parse_date_field(e5, "data objęcia w posiadanie")
            if not d: return
            idx = cb5_rodzaj.current()

            if idx == 2:
                termin = add_years_115(d, 3)
                rows = [
                    ("Data objęcia w posiadanie samoistne:", d, None, None),
                    ("Termin zasiedzenia ruchomości (3 lata, art. 174 KC):", termin,
                     "Posiadacz w dobrej wierze nabywa własność ruchomości po 3 latach nieprzerwanego posiadania samoistnego.",
                     "#6fcf97"),
                ]
                show_result("Zasiedzenie ruchomości", rows)
                return

            dobra_wiara = (idx == 0)

            stary_lat = 10 if dobra_wiara else 20
            termin_stary_raw = d + relativedelta(years=stary_lat)
            termin_stary     = next_workday(termin_stary_raw)

            nowy_lat = 20 if dobra_wiara else 30
            termin_nowy_raw = d + relativedelta(years=nowy_lat)
            termin_nowy     = next_workday(termin_nowy_raw)

            rows = [
                ("Data objęcia w posiadanie samoistne:", d, None, None),
            ]

            if d >= GRANICA_1990:
                wierz = "dobra wiara" if dobra_wiara else "zła wiara"
                rows += [
                    (f"Termin zasiedzenia ({nowy_lat} lat, {wierz}, art. 172 KC):", termin_nowy,
                     f"Posiadanie rozpoczęte po 1.10.1990 r. — stosuje się wyłącznie art. 172 KC w brzmieniu po nowelizacji.",
                     "#6fcf97"),
                ]
            else:
                rows.append(("Granica nowelizacji KC:", GRANICA_1990,
                              "Ustawa z 28.07.1990 r. zmieniająca KC — nowe terminy zasiedzenia nieruchomości.", None))

                if termin_stary <= GRANICA_1990:
                    rows += [
                        (f"✅ Termin wg starych przepisów ({stary_lat} lat):", termin_stary,
                         f"Stary termin ({stary_lat} lat) upłynął PRZED 1.10.1990 r. — zasiedzenie nastąpiło już na podstawie "
                         f"dawnych przepisów KC. Nowelizacja nie ma znaczenia.",
                         "#6fcf97"),
                        (f"Termin wg nowych przepisów ({nowy_lat} lat) [NIE ma zastosowania]:", termin_nowy,
                         "Nowy termin jest dłuższy i skończyłby się po starym — nie ma zastosowania.",
                         "#888888"),
                    ]
                else:
                    rows += [
                        (f"Termin wg starych przepisów ({stary_lat} lat) [NIE ma zastosowania]:", termin_stary,
                         f"Stary termin upłynąłby dopiero po 1.10.1990 r. — zgodnie z regułą intertemporalną "
                         f"stosuje się nowe, dłuższe terminy z art. 172 KC.",
                         "#888888"),
                        (f"✅ Termin wg nowych przepisów ({nowy_lat} lat, art. 172 KC):", termin_nowy,
                         f"Posiadanie rozpoczęte przed 1.10.1990 r., ale stary termin nie upłynął przed nowelizacją — "
                         f"stosuje się nowe terminy. Zasiedzenie nastąpi po {nowy_lat} latach od objęcia w posiadanie.",
                         "#6fcf97"),
                    ]

            rows.append(("Uwaga:", "— bieg zasiedzenia może być przerwany lub zawieszony",
                          "Art. 175 KC — do biegu zasiedzenia stosuje się odpowiednio przepisy o biegu przedawnienia, "
                          "w tym art. 123 KC (przerwanie) i art. 121 KC (zawieszenie). "
                          "Kalkulator zakłada nieprzerwany bieg terminu.", MUTED))

            show_result("Zasiedzenie nieruchomości", rows)

        calc_btn(c5, 4, "🗓  Oblicz termin zasiedzenia", oblicz_zasiedzenie)

        self.dt_result_frame.pack(fill="x", padx=20, pady=(4, 20))

    # ═══════════════════════════════════════════════════════════════════════
    # ZAKŁADKA 6 – KALKULATOR SPADKOWY
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

        def _btn_t(text, cmd):
            b = tk.Button(toolbar, text=text, command=cmd,
                          bg=GOLD, fg=BG, font=self.f_bold, relief="flat",
                          padx=12, pady=4, cursor="hand2",
                          activebackground=GOLD_LT, activeforeground=BG)
            b.pack(side="left", padx=4)
            return b

        _btn_t("+ Dodaj osobę", lambda: _dodaj_osobe())
        _btn_t("✏ Edytuj", lambda: _edytuj_wybrana())
        _btn_t("🗑 Usuń", lambda: _usun_wybrana())

        tk.Frame(toolbar, bg=GOLD, width=2).pack(side="left", fill="y", padx=6)

        _btn_t("💾 Zapisz bazę", lambda: _zapisz())
        _btn_t("📂 Wczytaj bazę", lambda: _wczytaj())

        tk.Frame(toolbar, bg=GOLD, width=2).pack(side="left", fill="y", padx=6)

        tk.Label(toolbar, text="Spadkodawca:", font=self.f_small,
                 bg=BG, fg="#aaaaaa").pack(side="left", padx=(6, 2))
        sp_combo_var = tk.StringVar()
        sp_combo = ttk.Combobox(toolbar, textvariable=sp_combo_var,
                                values=[], width=26, font=self.f_body,
                                state="readonly")
        sp_combo.pack(side="left", padx=4)

        _btn_t("⚖ Oblicz udziały", lambda: _oblicz())
        _btn_t("📄 Eksport PDF", lambda: _pdf())

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
            drzewo._scale = 1.0
            drzewo._offset = [50, 50]
            drzewo.odrysuj()

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

        def _odswiez():
            for w in lista_frame.winfo_children():
                w.destroy()
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
                                command=lambda oid=o.id: _wybierz(oid))
                btn.pack(fill="x", pady=1, padx=2, ipady=3)
                btn.bind("<Double-Button-1>", lambda e, oid=o.id: _edytuj_id(oid))
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
                messagebox.showinfo("Sukces", f"Raport PDF zapisano:\n{plik}")
            except RuntimeError as ex:
                messagebox.showerror("Brak biblioteki", str(ex))
            except Exception as ex:
                messagebox.showerror("Błąd PDF", str(ex))

        drzewo.on_select = _wybierz
        drzewo.on_edit = _edytuj_id
        drzewo.on_delete = _usun_id

        szuk_var.trace_add("write", lambda *a: _odswiez())

        _odswiez()

    def _tab_coming(self, nb, label):
        outer = tk.Frame(nb, bg=CREAM)
        nb.add(outer, text=label)
        tk.Label(outer, text=label.replace("  ", " "),
                 font=self.f_sub, bg=CREAM, fg=TEXT).pack(pady=(80, 10))
        tk.Label(outer,
                 text="Ta funkcjonalność zostanie wdrożona w kolejnym etapie.",
                 font=self.f_body, bg=CREAM, fg=MUTED).pack()


