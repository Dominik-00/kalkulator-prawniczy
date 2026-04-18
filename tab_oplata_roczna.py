# -*- coding: utf-8 -*-
"""
tab_oplata_roczna.py — Zakładka 'Aktualizacja opłaty rocznej (art. 77 UGN)'.
Klasa TabOplataRoczna(tk.Frame) — przeniesiona z app.py.
"""

import tkinter as tk
from tkinter import messagebox
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

from constants import (BG, PANEL, CREAM, GOLD, GOLD_LT, TEXT, MUTED,
                       BORDER, GREEN, fmt)
from tab_base import TabBase


class TabOplataRoczna(TabBase):
    """Zakładka kalkulatora aktualizacji opłaty rocznej z tytułu użytkowania wieczystego."""

    def __init__(self, master, app):
        super().__init__(master, app)
        self._build()

    # ── budowanie UI ─────────────────────────────────────────────────────────

    def _build(self):
        frame, _ = self._scrollable(self)

        tk.Label(frame, text="Aktualizacja opłaty rocznej z tytułu użytkowania wieczystego",
                 font=self.app.f_sub, bg=CREAM, fg=TEXT).pack(anchor="w", padx=20, pady=(14, 2))
        tk.Label(frame,
                 text="Art. 77–81 ustawy z dnia 21 sierpnia 1997 r. o gospodarce nieruchomościami (Dz.U. 1997 nr 115 poz. 741)",
                 font=self.app.f_small, bg=CREAM, fg=MUTED).pack(anchor="w", padx=20)

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
        tk.Label(ic, text=ustawa_text, font=self.app.f_small,
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
                 font=self.app.f_small, bg=PANEL, fg=MUTED).grid(
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
                 font=self.app.f_small, bg=PANEL, fg=MUTED).grid(
            row=4, column=0, columnspan=4, sticky="w", padx=(0, 0), pady=(0, 4))

        tk.Frame(c, bg=BORDER, height=1).grid(
            row=5, column=0, columnspan=4, sticky="ew", pady=(4, 8))

        self._lbl(c, "Stawka procentowa opłaty (%):", 0, 6)

        stawka_frame = tk.Frame(c, bg=PANEL)
        stawka_frame.grid(row=6, column=1, columnspan=3, sticky="ew", padx=(4, 0))
        stawka_frame.columnconfigure(2, weight=1)

        self.or_stawka = tk.Entry(stawka_frame, font=self.app.f_body, relief="flat", bd=0,
                                   bg=CREAM, fg=TEXT, width=8,
                                   highlightthickness=1, highlightbackground=BORDER)
        self.or_stawka.grid(row=0, column=0, sticky="w", ipady=4, padx=(0, 10))
        self.or_stawka.insert(0, "1")

        tk.Label(stawka_frame, text="Szybki wybór:", font=self.app.f_small,
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
                      bg="#eeeeee", fg=TEXT, font=self.app.f_small,
                      relief="flat", cursor="hand2", padx=8, pady=3,
                      activebackground=GOLD_LT).pack(side="left", padx=(0, 4))

        tk.Frame(c, bg=BORDER, height=1).grid(
            row=7, column=0, columnspan=4, sticky="ew", pady=(10, 8))
        self._lbl(c, "Data aktualizacji (RRRR-MM-DD):", 0, 8)
        self.or_data_aktualizacji = self._entry(c, 8, 1, width=16)
        self.or_data_aktualizacji.insert(0, date.today().strftime("%Y-%m-%d"))
        tk.Label(c, text="Używana do wyliczenia harmonogramu stopniowania opłaty",
                 font=self.app.f_small, bg=PANEL, fg=MUTED).grid(
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

        self._clear_frame(self.or_result_frame)

        rb = tk.Frame(self.or_result_frame, bg=BG)
        rb.pack(fill="x")

        tk.Label(rb, text="  📅  Wynik aktualizacji opłaty rocznej (art. 77 UGN)",
                 font=self.app.f_sub, bg=BG, fg=GOLD).pack(anchor="w", padx=16, pady=(12, 6))

        if weryfikacja_3lat is not None:
            l, m, ok = weryfikacja_3lat
            kolor_3lat = "#6fcf97" if ok else "#eb5757"
            znak = "✅" if ok else "⚠"
            msg = f"{znak}  Od ostatniej aktualizacji minęło {l} lat i {m} mies. — {'warunek 3 lat spełniony' if ok else 'warunek 3 lat NIE spełniony (art. 77 ust. 1)'}"
            tk.Label(rb, text=f"  {msg}", font=self.app.f_bold,
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
                     font=self.app.f_bold, bg=BG, fg="#6fcf97", wraplength=820,
                     justify="left", pady=6).pack(anchor="w", padx=16)
        else:
            tk.Label(rb,
                     text="  📆  Harmonogram stopniowania wzrostu opłaty (art. 77 ust. 2a):",
                     font=self.app.f_bold, bg=BG, fg=GOLD, pady=4).pack(anchor="w", padx=16)

            tbl = tk.Frame(rb, bg="#0d0d1f")
            tbl.pack(fill="x", padx=16, pady=(4, 8))

            hdr = tk.Frame(tbl, bg="#2d2d4a")
            hdr.pack(fill="x")
            for txt, w in [("Rok", 6), ("Rok kalendarzowy", 18), ("Opłata roczna", 20), ("Zmiana względem dotychcz.", 26)]:
                tk.Label(hdr, text=txt, font=self.app.f_small, bg="#2d2d4a", fg=GOLD,
                         width=w, anchor="w").pack(side="left", padx=10, pady=6)

            rok_akt = data_akt.year

            wiersze = [
                (1, rok_akt + 1, prog1,       oplata_dotychczasowa, "I — wzrost do 1/3 różnicy"),
                (2, rok_akt + 2, prog2,       oplata_dotychczasowa, "II — wzrost do 2/3 różnicy"),
                (3, rok_akt + 3, oplata_nowa, oplata_dotychczasowa, "III+ — pełna nowa opłata"),
            ]

            for nr, rok_kal, oplata_w, baza, opis in wiersze:
                bg_w = PANEL if nr % 2 == 0 else "#f9f9f9"
                row_f = tk.Frame(tbl, bg=bg_w)
                row_f.pack(fill="x")
                tk.Frame(tbl, bg=BORDER, height=1).pack(fill="x")

                diff_w = oplata_w - baza
                tk.Label(row_f, text=str(nr), font=self.app.f_bold,
                         bg=bg_w, fg=TEXT, width=6, anchor="w").pack(side="left", padx=10, pady=6)
                tk.Label(row_f, text=f"{rok_kal}  ({opis})", font=self.app.f_body,
                         bg=bg_w, fg=TEXT, width=18, anchor="w").pack(side="left", padx=10)
                tk.Label(row_f, text=fmt(oplata_w), font=self.app.f_bold,
                         bg=bg_w, fg=GREEN, width=20, anchor="w").pack(side="left", padx=10)
                tk.Label(row_f, text=f"+{fmt(diff_w)}", font=self.app.f_body,
                         bg=bg_w, fg="#888888", width=26, anchor="w").pack(side="left", padx=10)

        tk.Label(rb, text="", bg=BG, height=1).pack()
