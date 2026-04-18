# -*- coding: utf-8 -*-
"""
tab_raty.py — Zakładka 'Rozłożenie na raty'.
Klasa TabRaty(tk.Frame) — przeniesiona z app.py (_tab_raty i _oblicz_raty).
"""

import tkinter as tk
from tkinter import messagebox
import math
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta

from constants import (BG, PANEL, CREAM, GOLD, GOLD_LT, TEXT, MUTED,
                       BORDER, RED, GREEN, fmt, safe_float, safe_int)
from tab_base import TabBase


class TabRaty(TabBase):
    """Zakładka kalkulatora rozłożenia świadczenia na raty."""

    def __init__(self, master, app):
        super().__init__(master, app)
        self._build()

    # ── budowanie UI ─────────────────────────────────────────────────────────

    def _build(self):
        frame, _ = self._scrollable(self)

        tk.Label(frame, text="Rozłożenie świadczenia na raty",
                 font=self.app.f_sub, bg=CREAM, fg=TEXT).pack(anchor="w", padx=20, pady=(14, 2))
        tk.Label(frame,
                 text="Raty równe; pierwsza wyrównuje różnicę groszy jeśli kwota nie dzieli się bez reszty",
                 font=self.app.f_small, bg=CREAM, fg=MUTED).pack(anchor="w", padx=20)

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
                       bg=PANEL, font=self.app.f_body).pack(side="left")
        tk.Radiobutton(mode_frame, text="Znana kwota raty",
                       variable=self.r_mode, value="kwota",
                       command=self._toggle_rata_mode,
                       bg=PANEL, font=self.app.f_body).pack(side="left", padx=(12, 0))

        self.r_ilosc_lbl = tk.Label(c, text="Liczba rat:", font=self.app.f_small,
                                     bg=PANEL, fg=MUTED)
        self.r_ilosc_lbl.grid(row=2, column=0, sticky="w", pady=(6, 1))
        self.r_ilosc = self._entry(c, 2, 1, width=10)
        self.r_ilosc.insert(0, "12")

        self.r_kwota_j_lbl = tk.Label(c, text="Kwota jednej raty (PLN):", font=self.app.f_small,
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
                d = data_start + timedelta(weeks=n)
            return d.strftime("%d.%m.%Y")

        for r in raty:
            r['termin'] = next_date(r['nr'] - 1)

        suma_kontrolna = round(sum(r['kwota'] for r in raty), 2)

        self._clear_frame(self.r_result_frame)

        rb = tk.Frame(self.r_result_frame, bg=BG)
        rb.pack(fill="x")
        tk.Label(rb, text="  📋  Harmonogram rat",
                 font=self.app.f_sub, bg=BG, fg=GOLD).pack(anchor="w", padx=16, pady=(12, 6))
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
        for col, w in [("Nr raty", 8), ("Termin płatności", 18), ("Kwota raty", 18)]:
            tk.Label(hdr, text=col, font=self.app.f_small, bg=BG, fg=GOLD,
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
            tk.Label(row_f, text=nr_txt,
                     font=self.app.f_body if not r['wyrownujaca'] else self.app.f_bold,
                     bg=bg_row, fg=TEXT, width=8, anchor="w").pack(side="left", padx=10, pady=5)
            tk.Label(row_f, text=r['termin'], font=self.app.f_body,
                     bg=bg_row, fg=TEXT, width=18, anchor="w").pack(side="left", padx=10)
            tk.Label(row_f, text=fmt(r['kwota']), font=self.app.f_bold,
                     bg=bg_row, fg=GREEN if not r['wyrownujaca'] else RED,
                     width=18, anchor="w").pack(side="left", padx=10)

        foot = tk.Frame(table_frame, bg=BG)
        foot.pack(fill="x")
        tk.Label(foot, text="RAZEM", font=self.app.f_bold, bg=BG, fg=GOLD,
                 width=26, anchor="w").pack(side="left", padx=10, pady=6)
        tk.Label(foot, text=fmt(suma_kontrolna), font=self.app.f_bold,
                 bg=BG, fg=GOLD_LT).pack(side="left", padx=10)

        if abs(pierwsza - rata_base) > 0.005:
            tk.Label(self.r_result_frame,
                     text="★  Pierwsza rata wyrównuje resztę z podziału kwoty przez liczbę rat.",
                     font=self.app.f_small, bg=CREAM, fg=MUTED).pack(anchor="w", pady=(6, 0))
