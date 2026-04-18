# -*- coding: utf-8 -*-
"""
tab_pkk.py — Zakładka 'Koszty kredytu (art. 36a)'.
Klasa TabPKK(tk.Frame) — przeniesiona z app.py (_tab_pkk i _oblicz_pkk).
"""

import tkinter as tk
from tkinter import messagebox, font as tkfont

from constants import (BG, PANEL, CREAM, GOLD, GOLD_LT, TEXT, MUTED,
                       BORDER, fmt)
from tab_base import TabBase


class TabPKK(TabBase):
    """Zakładka kalkulatora maksymalnych pozaodsetkowych kosztów kredytu (art. 36a UKK)."""

    def __init__(self, master, app):
        super().__init__(master, app)
        self._build()

    # ── budowanie UI ─────────────────────────────────────────────────────────

    def _build(self):
        frame, _ = self._scrollable(self)

        tk.Label(frame, text="Maksymalne pozaodsetkowe koszty kredytu",
                 font=self.app.f_sub, bg=CREAM, fg=TEXT).pack(anchor="w", padx=20, pady=(14, 2))
        tk.Label(frame,
                 text="Art. 36a ustawy z dnia 12 maja 2011 r. o kredycie konsumenckim (Dz.U. 2011 nr 126 poz. 715)",
                 font=self.app.f_small, bg=CREAM, fg=MUTED).pack(anchor="w", padx=20)

        info_card = self._card(frame, "Podstawa prawna i wzór", pady=14)
        info_card.columnconfigure(0, weight=1)

        ustawa_text = (
            "Art. 36a ust. 1  UKK:  dla umów o okresie spłaty ≥ 30 dni:  MPKK ≤  (K × 10%)  +  (K × n/R × 10%)\n"
            "Art. 36a ust. 1a UKK:  dla umów o okresie spłaty < 30 dni:  MPKK ≤  K × 5%\n"
            "Art. 36a ust. 2  UKK:  MPKK nie może przekroczyć 45% całkowitej kwoty kredytu (K)\n\n"
            "gdzie:  K = całkowita kwota kredytu,  n = okres kredytowania w dniach,  R = liczba dni w roku (365)"
        )
        tk.Label(info_card, text=ustawa_text, font=self.app.f_small,
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
            ["30 dni lub więcej (art. 36a ust. 1)",
             "Poniżej 30 dni (art. 36a ust. 1a)"],
            row=0, col=3, width=32)
        self.pkk_rodzaj.bind("<<ComboboxSelected>>", lambda e: self._toggle_pkk_mode())

        self.pkk_okres_lbl = tk.Label(c, text="Okres kredytowania — n (dni):",
                                       font=self.app.f_small, bg=PANEL, fg=MUTED)
        self.pkk_okres_lbl.grid(row=1, column=0, sticky="w", pady=(6, 1))
        self.pkk_okres = self._entry(c, 1, 1, width=10)
        self.pkk_okres.insert(0, "365")

        self.pkk_okres_hint = tk.Label(c,
            text="Wpisz liczbę dni trwania umowy (np. 365 = 1 rok, 180 = pół roku)",
            font=self.app.f_small, bg=PANEL, fg=MUTED)
        self.pkk_okres_hint.grid(row=1, column=2, columnspan=2, sticky="w", padx=(8, 0))

        tk.Frame(c, bg=BORDER, height=1).grid(
            row=2, column=0, columnspan=4, sticky="ew", pady=(12, 8))

        self._lbl(c, "Rzeczywiście pobrane PKK (PLN):", 0, 3)
        self.pkk_pobrane = self._entry(c, 3, 1, width=16)
        self.pkk_pobrane.insert(0, "")
        tk.Label(c, text="(opcjonalnie — do oceny czy koszty nie przekraczają limitu)",
                 font=self.app.f_small, bg=PANEL, fg=MUTED).grid(
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

            skladnik_staly   = K * 0.10
            skladnik_zmienny = K * (n / R) * 0.10
            mpkk_przed_cap   = skladnik_staly + skladnik_zmienny
            wzor_opis        = "MPKK = (K × 10%) + (K × n/R × 10%)"

        mpkk = min(mpkk_przed_cap, K * 0.45)
        cap_zastosowany = mpkk_przed_cap > K * 0.45

        self._clear_frame(self.pkk_result_frame)

        rb = tk.Frame(self.pkk_result_frame, bg=BG)
        rb.pack(fill="x")

        tryb_txt = "poniżej 30 dni (art. 36a ust. 1a)" if do_30_dni else f"30 dni lub więcej — {n} dni (art. 36a ust. 1)"
        tk.Label(rb, text=f"  🏦  Wynik — umowa {tryb_txt}",
                 font=self.app.f_sub, bg=BG, fg=GOLD).pack(anchor="w", padx=16, pady=(12, 6))

        wzor_frame = tk.Frame(rb, bg="#0d0d1f")
        wzor_frame.pack(fill="x", padx=16, pady=(0, 8))
        tk.Label(wzor_frame, text=f"  {wzor_opis}",
                 font=tkfont.Font(family="Courier New", size=11, weight="bold"),
                 bg="#0d0d1f", fg=GOLD_LT, pady=8).pack(anchor="w")

        self._res_row(rb, "Całkowita kwota kredytu (K):", fmt(K))
        if not do_30_dni:
            self._res_row(rb, "Okres kredytowania (n):", f"{n} dni")
            self._res_row(rb, f"Składnik stały  (K × 10%):", fmt(skladnik_staly), color="#aaaaff")
            self._res_row(rb, f"Składnik zmienny  (K × {n}/{R} × 10%):", fmt(skladnik_zmienny), color="#aaaaff")
            self._res_row(rb, "Suma przed limitem (ust. 2):", fmt(mpkk_przed_cap))
        else:
            self._res_row(rb, f"Składnik (K × 5%):", fmt(skladnik_staly), color="#aaaaff")

        tk.Frame(rb, bg=GOLD, height=2).pack(fill="x", padx=16, pady=8)

        if cap_zastosowany:
            self._res_row(rb,
                "⚠  Limit z art. 36a ust. 2 — MPKK obniżone do 45% K:",
                fmt(mpkk), color="#eb5757", big=True)
            tk.Label(rb,
                     text="  Wyliczona kwota przekroczyła 45% całkowitej kwoty kredytu — zastosowano cap z art. 36a ust. 2.",
                     font=self.app.f_small, bg=BG, fg="#eb5757", pady=4).pack(anchor="w", padx=16)
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
                         font=self.app.f_bold, bg=BG, fg="#eb5757", pady=6).pack(anchor="w", padx=16)
            elif abs(nadwyzka) < 0.005:
                self._res_row(rb, "Rzeczywiście pobrane PKK:", fmt(pobrane), color="#6fcf97")
                tk.Label(rb,
                         text="  Pobrane koszty równają się dokładnie ustawowemu limitowi.",
                         font=self.app.f_bold, bg=BG, fg="#6fcf97", pady=6).pack(anchor="w", padx=16)
            else:
                self._res_row(rb, "Rzeczywiście pobrane PKK:", fmt(pobrane), color="#6fcf97")
                self._res_row(rb, "Margines poniżej limitu:", fmt(-nadwyzka), color="#6fcf97")
                tk.Label(rb,
                         text="  Pobrane koszty mieszczą się w ustawowym limicie z art. 36a UKK.",
                         font=self.app.f_bold, bg=BG, fg="#6fcf97", pady=6).pack(anchor="w", padx=16)

        tk.Label(rb, text="", bg=BG, height=1).pack()
