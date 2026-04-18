# -*- coding: utf-8 -*-
"""
tab_koszty.py — Zakładka 'Koszty postępowania sądowego'.
Klasa TabKoszty(tk.Frame) — przeniesiona z app.py (_tab_koszty i metody pomocnicze).
"""

import tkinter as tk
from tkinter import messagebox, filedialog
import json
import os
import subprocess
import tempfile
from datetime import datetime

from constants import (BG, PANEL, CREAM, GOLD, GOLD_LT, TEXT, MUTED, RED,
                       BORDER, fmt, safe_float,
                       oplata_sadowa, wynagrodzenie_pelnomocnika)
from tab_base import TabBase


class TabKoszty(TabBase):
    """Zakładka kalkulatora kosztów postępowania sądowego (art. 98–110 KPC)."""

    _RODZAJ_MAP = {0: "cywilna", 1: "gospodarcza", 2: "pracownicza", 3: "nakazowe"}

    def __init__(self, master, app):
        super().__init__(master, app)
        self._build()

    # ── budowanie UI ─────────────────────────────────────────────────────────

    def _build(self):
        frame, _ = self._scrollable(self)

        tk.Label(frame, text="Koszty postępowania sądowego",
                 font=self.app.f_sub, bg=CREAM, fg=TEXT).pack(anchor="w", padx=20, pady=(14, 2))
        tk.Label(frame,
                 text="Art. 98–110 KPC · rozp. MS z 22.10.2015 · UKSC - aktualne na dzień 14.04.2026",
                 font=self.app.f_small, bg=CREAM, fg=MUTED).pack(anchor="w", padx=20)

        c = self._card(frame, "Parametry sprawy", pady=14)
        c.columnconfigure(1, weight=1); c.columnconfigure(3, weight=1)

        self._lbl(c, "Wartość przedmiotu sporu (PLN):", 0, 0)
        self.k_wps = self._entry(c, 0, 1)
        self.k_wps.insert(0, "50000")

        self._lbl(c, "Rodzaj sprawy:", 2, 0)
        self.k_rodzaj = self._combo(c,
            ["Cywilna / majątkowa", "Gospodarcza",
             "Pracownicza (wariant uproszczony: powód-pracownik)",
             "Nakazowe / EPU (¼ opłaty)"],
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
                 font=self.app.f_small, bg=PANEL, fg=MUTED).grid(
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
            font=self.app.f_body, relief="flat", bd=0,
            bg=CREAM, fg=TEXT, width=14,
            highlightthickness=1, highlightbackground=BORDER)
        self.k_oplata_entry.grid(row=0, column=0, sticky="ew", ipady=4, padx=(0, 8))

        tk.Label(oplata_frame, text="(możesz edytować przed dodaniem)",
                 font=self.app.f_small, bg=PANEL, fg=MUTED).grid(
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

        self._btn_oplata = tk.Button(
            c, text="➕  Dodaj do kosztów powoda",
            command=dodaj_opiate_do_powoda,
            bg=GOLD, fg=BG, font=self.app.f_bold, relief="flat",
            activebackground=GOLD_LT, activeforeground=BG,
            cursor="hand2", padx=14, pady=5)
        self._btn_oplata.grid(row=4, column=0, sticky="w", pady=(2, 0))

        self.k_info_var = tk.StringVar()
        tk.Label(c, textvariable=self.k_info_var, font=self.app.f_small,
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
                 font=self.app.f_small, bg=PANEL, fg=MUTED,
                 ).grid(row=0, column=2, columnspan=2, sticky="w", padx=(8, 0))

        tk.Frame(c2, bg=BORDER, height=1).grid(
            row=1, column=0, columnspan=4, sticky="ew", pady=(10, 8))

        self._lbl(c2, "Powód wygrał (%):", 0, 2)
        self.k_pctW = self._entry(c2, 2, 1, width=10)
        self.k_pctW.insert(0, "100")

        self._lbl(c2, "Powód przegrał (%):", 2, 2)
        self.k_pctP = tk.Entry(c2, font=self.app.f_body, width=10, state="disabled",
                                relief="flat", bg="#eeeeee", fg=MUTED,
                                highlightthickness=1, highlightbackground=BORDER,
                                disabledbackground="#eeeeee", disabledforeground=MUTED)
        self.k_pctP.grid(row=2, column=3, sticky="ew", padx=(4, 8), pady=2, ipady=4)

        self.k_wynik_info_var = tk.StringVar()
        tk.Label(c2, textvariable=self.k_wynik_info_var, font=self.app.f_small,
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
                  self._oblicz_koszty, gold=True).pack(side="left", pady=4, padx=(0, 8))
        self._btn(row1, "🖨  Drukuj tabelę kosztów",
                  self._drukuj_koszty).pack(side="left", pady=4, padx=(0, 8))
        self._btn(row1, "💾  Zapisz sprawę",
                  self._zapisz_sprawe).pack(side="left", pady=4, padx=(0, 8))
        self._btn(row1, "📂  Wczytaj / zarządzaj sprawami",
                  self._wczytaj_sprawy).pack(side="left", pady=4)

        self.k_result_frame = tk.Frame(frame, bg=CREAM)
        self.k_result_frame.pack(fill="x", padx=20, pady=(0, 20))

    # ── Obsługa typów pozycji kosztowych ─────────────────────────────────────

    def _on_type_selected(self, type_cb, amt_e, desc_e, event=None):
        """Gdy użytkownik wybierze 'Wynagrodzenie pełnomocnika', automatycznie
        wstawia minimalne wynagrodzenie."""
        if type_cb.get() == "Wynagrodzenie pełnomocnika":
            wps = safe_float(self.k_wps)
            if wps > 0:
                rodzaj = self._RODZAJ_MAP.get(self.k_rodzaj.current(), "cywilna")
                w = (self._wynagrodzenie_pracownicze(wps)
                     if rodzaj == "pracownicza"
                     else wynagrodzenie_pelnomocnika(wps))
                amt_e.delete(0, "end")
                amt_e.insert(0, f"{w:.2f}".replace(".", ","))
            desc_e.delete(0, "end")
            desc_e.insert(0, "Koszty zastępstwa procesowego")

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
        suma_lbl = tk.Label(c, textvariable=suma_var, font=self.app.f_bold,
                            bg=PANEL, fg=TEXT)
        suma_lbl.grid(row=3, column=5, sticky="e", pady=(4, 0))
        tk.Label(c, text="Łącznie:", font=self.app.f_small, bg=PANEL, fg=MUTED).grid(
            row=3, column=4, sticky="e")

        items = getattr(self, f"{prefix}_items")

        type_cb.bind("<<ComboboxSelected>>",
                     lambda e, tc=type_cb, ae=amt_e, de=desc_e:
                         self._on_type_selected(tc, ae, de, e))

        def refresh():
            for w in list_frame.winfo_children():
                w.destroy()
            total = 0.0
            for i, item in enumerate(items):
                row = tk.Frame(list_frame, bg="#f9f9f9",
                               highlightthickness=1, highlightbackground=BORDER)
                row.pack(fill="x", pady=1)
                tk.Label(row, text=item['desc'], font=self.app.f_body,
                         bg="#f9f9f9", fg=TEXT, anchor="w").pack(side="left", padx=8, pady=4)
                tk.Label(row, text=f"[{item['type']}]", font=self.app.f_small,
                         bg="#f9f9f9", fg=MUTED).pack(side="left")
                tk.Label(row, text=fmt(item['amt']), font=self.app.f_bold,
                         bg="#f9f9f9", fg=TEXT).pack(side="right", padx=12)
                idx = i
                tk.Button(row, text="✕", command=lambda i=idx: remove(i),
                          bg="#f9f9f9", fg=RED, font=self.app.f_small,
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

        if prefix in ("powod", "pozwany"):
            def add_oplata_skarbowa(items=items, refresh=refresh):
                items.append({
                    'desc': 'Opłata skarbowa od pełnomocnictwa',
                    'amt': 17.0,
                    'type': 'Wydatek (inne)'
                })
                refresh()

            def add_wynagrodzenie(items=items, refresh=refresh):
                wps = safe_float(self.k_wps)
                if wps <= 0:
                    messagebox.showerror("Błąd", "Najpierw wpisz wartość przedmiotu sporu (WPS).")
                    return
                rodzaj = self._RODZAJ_MAP.get(self.k_rodzaj.current(), "cywilna")
                if rodzaj == "pracownicza":
                    w = self._wynagrodzenie_pracownicze(wps)
                else:
                    w = wynagrodzenie_pelnomocnika(wps)
                items.append({
                    'desc': 'Koszty zastępstwa procesowego',
                    'amt': w,
                    'type': 'Wynagrodzenie pełnomocnika'
                })
                refresh()

            tk.Button(
                c, text="+ Opłata skarbowa (17 zł)",
                command=add_oplata_skarbowa,
                bg=PANEL, fg=TEXT, font=self.app.f_body, relief="flat",
                activebackground=GOLD_LT, activeforeground=BG,
                cursor="hand2", padx=10, pady=4,
                highlightthickness=1, highlightbackground=BORDER
            ).grid(row=1, column=2, columnspan=2, sticky="w", padx=(8, 0), pady=(6, 0))

            tk.Button(
                c, text="+ Wynagrodzenie pełnomocnika",
                command=add_wynagrodzenie,
                bg=PANEL, fg=TEXT, font=self.app.f_body, relief="flat",
                activebackground=GOLD_LT, activeforeground=BG,
                cursor="hand2", padx=10, pady=4,
                highlightthickness=1, highlightbackground=BORDER
            ).grid(row=1, column=4, columnspan=2, sticky="w", padx=(8, 0), pady=(6, 0))

        setattr(self, f"{prefix}_refresh", refresh)

    # ── Metody pomocnicze ─────────────────────────────────────────────────────

    def _pokaz_btn_oplaty(self, pokaz: bool):
        """Pokazuje lub ukrywa przycisk 'Dodaj do kosztów powoda' dla opłaty sądowej."""
        if not hasattr(self, '_btn_oplata'):
            return
        visible = bool(self._btn_oplata.winfo_ismapped())
        if pokaz and not visible:
            self._btn_oplata.grid(row=4, column=0, sticky="w", pady=(2, 0))
        elif not pokaz and visible:
            self._btn_oplata.grid_remove()

    def _wynagrodzenie_pracownicze(self, wps: float) -> float:
        """Stawki minimalne zastępstwa w sprawach z zakresu prawa pracy
        wg § 9 rozp. MS z 22.10.2015 r."""
        stawka_ogolna = wynagrodzenie_pelnomocnika(wps)
        return max(180.0, stawka_ogolna)

    def _update_koszty_info(self):
        wps = safe_float(self.k_wps)
        if not wps:
            self.k_info_var.set("")
            self.k_oplata_var.set("")
            if hasattr(self, '_btn_oplata'):
                self._pokaz_btn_oplaty(True)
            return
        rodzaj = self._RODZAJ_MAP.get(self.k_rodzaj.current(), "cywilna")
        repr_idx = self.k_repr.current()
        o = oplata_sadowa(wps, rodzaj, "1")

        if rodzaj == "pracownicza":
            self.k_oplata_var.set("0,00")
            self._pokaz_btn_oplaty(False)
            if repr_idx == 0:
                w = self._wynagrodzenie_pracownicze(wps)
                info = (
                    f"⚖ Sprawa pracownicza: ta opcja przyjmuje wariant uproszczony, w którym powodem "
                    f"jest pracownik zwolniony z opłaty przy pozwie (art. 96 ust. 1 pkt 4 UKSC, z "
                    f"zastrzeżeniem art. 35 UKSC).\n"
                    f"Min. wynagrodzenie pełnomocnika wg § 9 rozp. MS z 22.10.2015: {fmt(w)} "
                    f"(stawka pracownicza, nie stawka § 2)."
                )
            else:
                info = (
                    "⚖ Sprawa pracownicza: ta opcja zakłada wariant powód-pracownik. W praktyce "
                    "opłata zależy także od rodzaju pisma i wyjątków z art. 35 UKSC."
                )
        else:
            self._pokaz_btn_oplaty(True)
            w = wynagrodzenie_pelnomocnika(wps) if repr_idx == 0 else 0
            self.k_oplata_var.set(f"{o:.2f}".replace(".", ","))
            if rodzaj == "nakazowe":
                info = (
                    f"¼ opłaty od pozwu w postępowaniu nakazowym albo EPU (art. 19 ust. 2 UKSC)."
                    + (f"  Min. wynagrodzenie pełnomocnika: {fmt(w)}" if w else "")
                )
            else:
                info = f"Min. wynagrodzenie pełnomocnika: {fmt(w)}" if w else ""
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
        w = 0.0
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

    # ── Obliczenia i zbieranie danych ─────────────────────────────────────────

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

    def _oblicz_koszty(self):
        try:
            float(self.k_pctW.get())
        except ValueError:
            messagebox.showerror("Błąd", "Wpisz poprawny procent wygranej.")
            return

        d = self._get_koszty_data()
        wps             = d['wps']
        pctW            = d['pct_powod'] / 100.0
        pctP            = d['pct_pozwany'] / 100.0
        sum_powod       = d['sum_powod']
        sum_pozwany     = d['sum_pozwany']
        sum_sp          = d['sum_sp']
        zwrot_powodowi  = d['zwrot_powodowi']
        zwrot_pozwanemu = d['zwrot_pozwanemu']
        sp_na_powoda    = d['sp_na_powoda']
        sp_na_pozwanego = d['sp_na_pozwanego']
        netto_pozwany   = d['netto_pozwany']
        netto_powod     = d['netto_powod']

        self._clear_frame(self.k_result_frame)

        rb = tk.Frame(self.k_result_frame, bg=BG)
        rb.pack(fill="x")

        tk.Label(rb, text="  ⚖  Rozliczenie kosztów (art. 98–100 KPC)",
                 font=self.app.f_sub, bg=BG, fg=GOLD).pack(anchor="w", padx=16, pady=(12, 8))

        pbar_frame = tk.Frame(rb, bg=BG)
        pbar_frame.pack(fill="x", padx=16, pady=(0, 10))

        info_row = tk.Frame(pbar_frame, bg=BG)
        info_row.pack(fill="x")
        tk.Label(info_row,
                 text=f"Powód wygrał: {pctW*100:.1f}%  ({fmt(wps*pctW)})",
                 font=self.app.f_bold, bg=BG, fg="#6fcf97").pack(side="left")
        tk.Label(info_row,
                 text=f"Pozwany wygrał: {pctP*100:.1f}%  ({fmt(wps*pctP)})",
                 font=self.app.f_bold, bg=BG, fg="#eb5757").pack(side="right")

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

        # Informacja szczególna dla spraw pracowniczych
        rodzaj2 = self._RODZAJ_MAP.get(self.k_rodzaj.current(), "cywilna")
        if rodzaj2 == "pracownicza":
            o2 = oplata_sadowa(wps, "pracownicza", "1")
            nota_frame = tk.Frame(rb, bg="#1a2a1a")
            nota_frame.pack(fill="x", padx=16, pady=(0, 8))
            tk.Label(nota_frame,
                     text=(
                        f"⚖ Sprawa pracownicza — ten wynik zakłada wariant powód-pracownik.\n"
                        f"Rozliczenie opłaty może zależeć od art. 35, art. 96 ust. 1 pkt 4 i art. 113 UKSC; "
                        f"przy innym układzie stron lub środku zaskarżenia opłata może być inna.\n"
                        f"Wynagrodzenie pełnomocnika powoda naliczane wg § 9 rozp. MS z 22.10.2015."
                     ),
                     font=self.app.f_small, bg="#1a2a1a", fg="#90ee90",
                     justify="left", wraplength=820, padx=12, pady=8,
                     anchor="w").pack(fill="x")

    # ── Drukowanie i zapis spraw ──────────────────────────────────────────────

    def _drukuj_koszty(self):
        """Generuje plik Word z tabelą kosztów – gotowy do druku."""
        import shutil

        data = self._get_koszty_data()
        sygn = data['sygnatura'] or 'sprawa'

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

const W = 9360;
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

        self.k_sygnatura.delete(0, "end")
        self.k_sygnatura.insert(0, data.get('sygnatura', ''))

        self.k_wps.delete(0, "end")
        self.k_wps.insert(0, str(data.get('wps', 0)))

        for attr in ('powod_items', 'pozwany_items', 'sp_items'):
            lst = getattr(self, attr)
            lst.clear()
            lst.extend(data.get(attr, []))

        self.k_pctW.delete(0, "end")
        self.k_pctW.insert(0, f"{data.get('pct_powod', 100):.2f}")
        self._set_pctP(data.get('pct_pozwany', 0))

        self.powod_refresh()
        self.pozwany_refresh()
        self.sp_refresh()
        self._update_koszty_info()

        messagebox.showinfo("Wczytano",
            f"Dane sprawy '{sygn}' zostały wczytane do kalkulatora.")
