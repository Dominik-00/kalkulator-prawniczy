# -*- coding: utf-8 -*-
"""
tab_przedawnienie.py — Zakładka 'Kalkulator przedawnienia'.
Klasa TabPrzedawnienie(tk.Frame) — przeniesiona z app.py (_tab_przedawnienie).
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta

from constants import (BG, PANEL, CREAM, GOLD, GOLD_LT, TEXT, MUTED,
                       BORDER)
from tab_base import TabBase
from logika_przedawnienie import (uplyw as _uplyw_fn, lata_str as _lata_str_fn,
                                   oblicz_przejsciowe as _oblicz_przejsciowe_fn)


class TabPrzedawnienie(TabBase):
    """Zakładka kalkulatora przedawnienia roszczeń (art. 118–125 KC)."""

    def __init__(self, master, app):
        super().__init__(master, app)
        self._build()

    # ── budowanie UI ─────────────────────────────────────────────────────────

    def _build(self):
        frame, _ = self._scrollable(self)

        tk.Label(frame, text="Kalkulator przedawnienia roszczeń",
                 font=self.app.f_sub, bg=CREAM, fg=TEXT).pack(anchor="w", padx=20, pady=(14, 2))
        tk.Label(frame,
                 text="Art. 118–125 KC · uwzględnia regułę końca roku kalendarzowego (nowelizacja z 9.07.2018 r.)",
                 font=self.app.f_small, bg=CREAM, fg=MUTED).pack(anchor="w", padx=20)

        # ── Słownik terminów przedawnienia ────────────────────────────────
        _TERMINY = [
            ("3 lata — ogólny / działalność gospodarcza (art. 118 KC)",                                3),
            ("6 lat — ogólny (art. 118 KC)",                                                            6),
            ("Inne — podaj ręcznie",                                                                 None),
            ("Alimenty — 3 lata (art. 137 §2 KRiO)",                                                   3),
            ("Czek — 3 lata od terminu płatności (art. 52 Prawa czekowego)",                           3),
            ("Czyn niedozwolony — maks. 10 lat od zdarzenia (art. 442¹ §1 KC)",                       10),
            ("Czyn niedozwolony (zbrodnia/występek) — 20 lat (art. 442¹ §2 KC)",                      20),
            ("Dzierżawa — roszczenia po zwrocie przedmiotu — 1 rok (art. 694 KC w zw. z art. 677 KC)",  1),
            ("Kredyt bankowy — 3 lata (art. 118 KC)",                                                   3),
            ("Najem — roszczenia po zwrocie rzeczy — 1 rok (art. 677 KC)",                              1),
            ("Pożyczka — 3 lata / działalność gospodarcza (art. 118 KC)",                               3),
            ("Prawo pracy — roszczenia ze stosunku pracy — 3 lata (art. 291 §1 KP)",                   3),
            ("Rękojmia — nieruchomość — 5 lat (art. 568 §1 KC)",                                       5),
            ("Rękojmia — rzecz ruchoma — 2 lata (art. 568 §1 KC)",                                     2),
            ("Transport / przewóz — 1 rok (art. 778 KC)",                                               1),
            ("Ubezpieczenie — 3 lata (art. 819 §1 KC)",                                                3),
            ("Umowa o dzieło — 2 lata (art. 646 KC)",                                                  2),
            ("Weksel własny — 3 lata od terminu płatności (art. 70 Prawa wekslowego)",                 3),
            ("Zachowek — 5 lat od ogłoszenia testamentu / otwarcia spadku (art. 1007 §1 KC)",          5),
            ("Zlecenie — wynagrodzenie i zwrot wydatków — 2 lata (art. 751 KC)",                        2),
        ]
        _t_labels = [t[0] for t in _TERMINY]
        _t_values  = {t[0]: t[1] for t in _TERMINY}

        # ── Dawne terminy przed nowelizacją z 9.07.2018 r. ───────────────
        _STARE_TERMINY = {
            "3 lata — ogólny / działalność gospodarcza (art. 118 KC)":                                3,
            "6 lat — ogólny (art. 118 KC)":                                                           10,
            "Alimenty — 3 lata (art. 137 §2 KRiO)":                                                   3,
            "Czek — 3 lata od terminu płatności (art. 52 Prawa czekowego)":                           3,
            "Czyn niedozwolony — maks. 10 lat od zdarzenia (art. 442¹ §1 KC)":                       10,
            "Czyn niedozwolony (zbrodnia/występek) — 20 lat (art. 442¹ §2 KC)":                      20,
            "Dzierżawa — roszczenia po zwrocie przedmiotu — 1 rok (art. 694 KC w zw. z art. 677 KC)":  1,
            "Kredyt bankowy — 3 lata (art. 118 KC)":                                                   3,
            "Najem — roszczenia po zwrocie rzeczy — 1 rok (art. 677 KC)":                              1,
            "Pożyczka — 3 lata / działalność gospodarcza (art. 118 KC)":                               3,
            "Prawo pracy — roszczenia ze stosunku pracy — 3 lata (art. 291 §1 KP)":                   3,
            "Rękojmia — nieruchomość — 5 lat (art. 568 §1 KC)":                                       5,
            "Rękojmia — rzecz ruchoma — 2 lata (art. 568 §1 KC)":                                     2,
            "Transport / przewóz — 1 rok (art. 778 KC)":                                               1,
            "Ubezpieczenie — 3 lata (art. 819 §1 KC)":                                                3,
            "Umowa o dzieło — 2 lata (art. 646 KC)":                                                  2,
            "Weksel własny — 3 lata od terminu płatności (art. 70 Prawa wekslowego)":                 3,
            "Zachowek — 5 lat od ogłoszenia testamentu / otwarcia spadku (art. 1007 §1 KC)":          5,
            "Zlecenie — wynagrodzenie i zwrot wydatków — 2 lata (art. 751 KC)":                        2,
        }

        # ── Funkcje pomocnicze ────────────────────────────────────────────

        def _parse_d(widget, field):
            s = widget.get().strip()
            for fmt_str in ("%d.%m.%Y", "%Y-%m-%d", "%d-%m-%Y"):
                try:
                    return datetime.strptime(s, fmt_str).date()
                except ValueError:
                    pass
            messagebox.showerror("Błąd daty",
                f"Nieprawidłowy format: '{s}'\nPole: {field}\nUżyj DD.MM.RRRR lub RRRR-MM-DD")
            return None

        def _upływ(wymagalnosc, lata):
            """Zwraca (surowa, ostateczna) zgodnie z nowym art. 118 KC."""
            surowa = wymagalnosc + relativedelta(years=lata)
            ostateczna = date(surowa.year, 12, 31) if lata >= 2 else surowa
            return surowa, ostateczna

        def _lata_str(n):
            if n == 1:          return "1 rok"
            if n in (2, 3, 4):  return f"{n} lata"
            return f"{n} lat"

        def _link_termin(cb, e_lata):
            """Łączy combobox terminu z polem ręcznym."""
            def _on(event=None):
                v = _t_values.get(cb.get())
                e_lata.config(state="normal", bg=CREAM)
                e_lata.delete(0, "end")
                if v is not None:
                    e_lata.insert(0, str(v))
                    e_lata.config(state="disabled",
                                  disabledbackground="#eeeeee",
                                  disabledforeground=MUTED)
            cb.bind("<<ComboboxSelected>>", _on)
            _on()

        def _oblicz_przejsciowe(wymagalnosc, lata_nowe, lata_stare, konsument):
            """Przepisy przejściowe ustawy z 13.04.2018 r. (Dz.U. 2018 poz. 1104)."""
            DATA_NOW   = date(2018, 7, 9)
            DATA_MIN_K = date(2020, 7, 9)

            stare_uplyw = wymagalnosc + relativedelta(years=lata_stare)

            if stare_uplyw < DATA_NOW:
                return stare_uplyw, {
                    'tryb': 'stare_pred_now',
                    'stare_uplyw': stare_uplyw,
                    'nowe_uplyw': None,
                    'nowe_od_now': False,
                    'wybrany': 'stare',
                    'konsument_korekta': False,
                }

            if lata_nowe < lata_stare:
                nowe_s = DATA_NOW + relativedelta(years=lata_nowe)
                nowe_o = date(nowe_s.year, 12, 31) if lata_nowe >= 2 else nowe_s
                nowe_od_now = True
                if stare_uplyw <= nowe_o:
                    wynik   = stare_uplyw
                    wybrany = 'stare'
                else:
                    wynik   = nowe_o
                    wybrany = 'nowe'
            else:
                nowe_s = wymagalnosc + relativedelta(years=lata_nowe)
                nowe_o = date(nowe_s.year, 12, 31) if lata_nowe >= 2 else nowe_s
                nowe_od_now = False
                wynik   = nowe_o
                wybrany = 'nowe'

            konsument_korekta = False
            if konsument and wynik < DATA_MIN_K:
                wynik = DATA_MIN_K
                konsument_korekta = True

            return wynik, {
                'tryb': 'przejsciowy',
                'stare_uplyw': stare_uplyw,
                'nowe_uplyw': nowe_o,
                'nowe_od_now': nowe_od_now,
                'wybrany': wybrany,
                'konsument_korekta': konsument_korekta,
                'DATA_MIN_K': DATA_MIN_K,
            }

        def _przej_sub(card, row_start, col_span, cb_main):
            """Dodaje sekcję przepisów przejściowych do karty."""
            tk.Frame(card, bg=BORDER, height=1).grid(
                row=row_start, column=0, columnspan=col_span,
                sticky="ew", pady=(10, 4))

            przej_var = tk.BooleanVar(value=False)
            chk = tk.Checkbutton(
                card,
                text=("☐  Zastosuj przepisy przejściowe — roszczenie powstało przed"
                      " 9.07.2018 r.  (ustawa z 13.04.2018, Dz.U. 2018 poz. 1104)"),
                variable=przej_var,
                bg=PANEL, fg=TEXT, font=self.app.f_small,
                activebackground=PANEL, selectcolor=PANEL,
                anchor="w", cursor="hand2")
            chk.grid(row=row_start + 1, column=0, columnspan=col_span,
                     sticky="ew", padx=(0, 8), pady=(0, 2))

            sub = tk.Frame(card, bg="#fffbf0",
                           highlightthickness=1, highlightbackground="#c8b880")
            sub.columnconfigure(1, weight=1); sub.columnconfigure(3, weight=1)

            tk.Label(sub, text="Dawny termin wg poprzedniego brzmienia (lat):",
                     font=self.app.f_small, bg="#fffbf0", fg=MUTED).grid(
                row=0, column=0, sticky="w", padx=(8, 4), pady=(6, 3))
            e_stare = tk.Entry(sub, font=self.app.f_body, width=6, relief="flat", bd=0,
                               bg=CREAM, fg=TEXT,
                               highlightthickness=1, highlightbackground=BORDER)
            e_stare.grid(row=0, column=1, sticky="w",
                         padx=(4, 8), pady=(6, 3), ipady=4)
            tk.Label(sub,
                     text="← auto-wypełniane na podstawie wybranego terminu; zmień ręcznie jeśli znasz inny",
                     font=self.app.f_small, bg="#fffbf0", fg=MUTED).grid(
                row=0, column=2, columnspan=2, sticky="w", padx=(0, 8))

            tk.Label(sub, text="Podmiot uprawniony:",
                     font=self.app.f_small, bg="#fffbf0", fg=MUTED).grid(
                row=1, column=0, sticky="w", padx=(8, 4), pady=(0, 6))
            cb_podmiot = ttk.Combobox(
                sub,
                values=["Przedsiębiorca",
                        "Konsument — ochrona min. 2-letnia (art. 5 ust. 3 ustawy z 2018 r.)"],
                state="readonly", font=self.app.f_body, width=56)
            cb_podmiot.current(0)
            cb_podmiot.grid(row=1, column=1, columnspan=3,
                            sticky="ew", padx=(4, 8), pady=(0, 6), ipady=2)

            sub.grid(row=row_start + 2, column=0, columnspan=col_span,
                     sticky="ew", padx=(0, 8), pady=(0, 4))
            sub.grid_remove()

            def _toggle(event=None):
                (sub.grid() if przej_var.get() else sub.grid_remove())

            chk.config(command=_toggle)

            def _sync_stare(event=None):
                v = _STARE_TERMINY.get(cb_main.get())
                e_stare.delete(0, "end")
                e_stare.insert(0, str(v) if v is not None else "")

            cb_main.bind("<<ComboboxSelected>>", _sync_stare, "+")
            _sync_stare()

            return {'var': przej_var, 'e_stare': e_stare, 'cb_podmiot': cb_podmiot}

        # ════════════════════════════════════════════════════════════════
        # SEKCJA 1 — świadczenie jednorazowe
        # ════════════════════════════════════════════════════════════════
        c1 = self._card(frame, "1.  Świadczenie jednorazowe — termin przedawnienia", pady=14)
        c1.columnconfigure(1, weight=1)

        self._lbl(c1, "Data wymagalności (DD.MM.RRRR):", col=0, row=0)
        jed_e_data = self._entry(c1, row=0, col=1, width=20)
        jed_e_data.insert(0, date.today().strftime("%d.%m.%Y"))

        self._lbl(c1, "Termin przedawnienia:", col=0, row=1)
        jed_cb = ttk.Combobox(c1, values=_t_labels, state="readonly",
                               font=self.app.f_body, width=70)
        jed_cb.current(0)
        jed_cb.grid(row=1, column=1, sticky="ew", padx=(4, 8), pady=2, ipady=2)

        self._lbl(c1, "Liczba lat (ręcznie):", col=0, row=2)
        jed_e_lata = self._entry(c1, row=2, col=1, width=8)
        tk.Label(c1, text="(edytowalne tylko przy wyborze 'Inne — podaj ręcznie')",
                 font=self.app.f_small, bg=PANEL, fg=MUTED).grid(
            row=2, column=1, sticky="e", padx=(0, 8))
        _link_termin(jed_cb, jed_e_lata)

        jed_p = _przej_sub(c1, row_start=3, col_span=2, cb_main=jed_cb)

        jed_result = tk.Frame(frame, bg=CREAM)

        def oblicz_jednorazowe():
            d = _parse_d(jed_e_data, "data wymagalności")
            if not d: return
            try:
                lata = int(jed_e_lata.get().strip())
                if lata < 1: raise ValueError
            except ValueError:
                messagebox.showerror("Błąd", "Termin przedawnienia: podaj liczbę całkowitą ≥ 1.")
                return

            surowa, std_ost = _upływ(d, lata)
            dzis = date.today()

            przej = jed_p['var'].get()
            if przej:
                try:
                    lata_st = int(jed_p['e_stare'].get().strip())
                    if lata_st < 1: raise ValueError
                except ValueError:
                    messagebox.showerror("Błąd",
                        "Dawny termin: podaj liczbę całkowitą ≥ 1.")
                    return
                konsument = jed_p['cb_podmiot'].current() == 1
                ostateczna, pinfo = _oblicz_przejsciowe(d, lata, lata_st, konsument)
            else:
                ostateczna = std_ost
                pinfo      = None

            przed = dzis > ostateczna

            self._clear_frame(jed_result)
            rb = tk.Frame(jed_result, bg=BG)
            rb.pack(fill="x")

            nagl = "  ⏳  Przedawnienie — świadczenie jednorazowe"
            if przej:
                nagl += "  [przepisy przejściowe art. 5 ustawy z 2018 r.]"
            tk.Label(rb, text=nagl, font=self.app.f_sub,
                     bg=BG, fg=GOLD).pack(anchor="w", padx=16, pady=(12, 8))

            self._res_row(rb, "Termin przedawnienia (nowy):",
                          f"{_lata_str(lata)}  ·  {jed_cb.get()[:60]}")
            self._res_row(rb, "Data wymagalności (bieg od):", d.strftime("%d.%m.%Y"))

            if przej and pinfo:
                if pinfo['tryb'] == 'stare_pred_now':
                    self._res_row(rb,
                        f"Stary termin ({_lata_str(lata_st)}, bez zasady k.r.) — "
                        f"wygasł PRZED nowelizacją:",
                        pinfo['stare_uplyw'].strftime("%d.%m.%Y"), color="#eb5757")
                else:
                    self._res_row(rb,
                        f"Stary termin ({_lata_str(lata_st)}, bez zasady k.r.):",
                        pinfo['stare_uplyw'].strftime("%d.%m.%Y"), color="#888888")
                    if pinfo['nowe_od_now']:
                        skad = f"bieg od 9.07.2018 (art. 5 ust. 2)"
                    else:
                        skad = f"bieg od wymagalności (art. 5 ust. 1)"
                    self._res_row(rb,
                        f"Nowy termin ({_lata_str(lata)} + zasada k.r., {skad}):",
                        pinfo['nowe_uplyw'].strftime("%d.%m.%Y"), color="#888888")

                    wybr_txt = ("stare prawo — upływa wcześniej ✓"
                                if pinfo['wybrany'] == 'stare'
                                else "nowe prawo + zasada k.r. — upływa wcześniej ✓")
                    self._res_row(rb, "Zastosowano:", wybr_txt, color=GOLD_LT)

                    if pinfo['konsument_korekta']:
                        self._res_row(rb,
                            "Przedłużono do min. terminu konsumenckiego (art. 5 ust. 3):",
                            pinfo['DATA_MIN_K'].strftime("%d.%m.%Y"), color="#6fcf97")
            else:
                self._res_row(rb, "Upływ terminu (rachunek surowy):", surowa.strftime("%d.%m.%Y"))
                nota = ("Upływ terminu po art. 118 KC (koniec roku kalendarzowego):"
                        if lata >= 2
                        else "Upływ terminu (termin < 2 lat — art. 118 zd. 2 KC nie przesuwa):")
                self._res_row(rb, nota, ostateczna.strftime("%d.%m.%Y"), color=GOLD_LT)

            tk.Frame(rb, bg=GOLD, height=2).pack(fill="x", padx=16, pady=8)

            if przed:
                self._res_row(rb, "⚠  STATUS:", "ROSZCZENIE PRZEDAWNIONE",
                              color="#eb5757", big=True)
                dni = (dzis - ostateczna).days
                self._res_row(rb, "Przedawnione od:",
                              f"{ostateczna.strftime('%d.%m.%Y')}  "
                              f"({dni} {'dzień' if dni == 1 else 'dni'} temu)",
                              color="#eb5757")
            else:
                dni = (ostateczna - dzis).days
                self._res_row(rb, "✅  STATUS:", "Roszczenie NIEPRZEDAWNIONE",
                              color="#6fcf97", big=True)
                self._res_row(rb, "Pozostało do przedawnienia:",
                              f"{dni} {'dzień' if dni == 1 else 'dni'}"
                              f"  (do {ostateczna.strftime('%d.%m.%Y')})",
                              color="#6fcf97")
            tk.Label(rb, text="", bg=BG, height=1).pack()

        bf1 = tk.Frame(frame, bg=CREAM)
        bf1.pack(fill="x", padx=20, pady=(4, 0))
        self._btn(bf1, "⏳  Oblicz przedawnienie",
                  oblicz_jednorazowe, gold=True).pack(side="left", pady=4)
        jed_result.pack(fill="x", padx=20, pady=(0, 8))

        # ════════════════════════════════════════════════════════════════
        # SEKCJA 2 — świadczenia w ratach / świadczenia okresowe
        # ════════════════════════════════════════════════════════════════
        c2 = self._card(frame, "2.  Świadczenia w ratach / świadczenia okresowe", pady=14)
        c2.columnconfigure(1, weight=1); c2.columnconfigure(3, weight=1)

        self._lbl(c2, "Data pierwszej raty (DD.MM.RRRR):", col=0, row=0)
        rat_e_data = self._entry(c2, row=0, col=1, width=20)
        rat_e_data.insert(0, date.today().strftime("%d.%m.%Y"))

        self._lbl(c2, "Liczba rat:", col=2, row=0)
        rat_e_ilosc = self._entry(c2, row=0, col=3, width=8)
        rat_e_ilosc.insert(0, "12")

        self._lbl(c2, "Częstotliwość rat:", col=0, row=1)
        rat_cb_czest = self._combo(c2,
            ["Miesięczna", "Kwartalna", "Półroczna", "Roczna", "Tygodniowa"],
            row=1, col=1, width=22)

        self._lbl(c2, "Termin przedawnienia:", col=0, row=2)
        rat_cb = ttk.Combobox(c2, values=_t_labels, state="readonly",
                               font=self.app.f_body, width=70)
        rat_cb.current(0)
        rat_cb.grid(row=2, column=1, columnspan=3, sticky="ew", padx=(4, 8), pady=2, ipady=2)

        self._lbl(c2, "Liczba lat (ręcznie):", col=0, row=3)
        rat_e_lata = self._entry(c2, row=3, col=1, width=8)
        tk.Label(c2, text='(edytowalne tylko przy wyborze \u201eInne \u2014 podaj r\u0119cznie\u201d)',
                 font=self.app.f_small, bg=PANEL, fg=MUTED).grid(
            row=3, column=1, sticky="e", padx=(0, 8))
        _link_termin(rat_cb, rat_e_lata)

        rat_p = _przej_sub(c2, row_start=4, col_span=4, cb_main=rat_cb)

        rat_result = tk.Frame(frame, bg=CREAM)

        def oblicz_raty_pf():
            d0 = _parse_d(rat_e_data, "data pierwszej raty")
            if not d0: return
            try:
                n = int(rat_e_ilosc.get().strip())
                if not (1 <= n <= 600): raise ValueError
            except ValueError:
                messagebox.showerror("Błąd", "Liczba rat: liczba całkowita 1–600.")
                return
            try:
                lata = int(rat_e_lata.get().strip())
                if lata < 1: raise ValueError
            except ValueError:
                messagebox.showerror("Błąd", "Termin przedawnienia: liczba całkowita ≥ 1.")
                return

            przej = rat_p['var'].get()
            if przej:
                try:
                    lata_st = int(rat_p['e_stare'].get().strip())
                    if lata_st < 1: raise ValueError
                except ValueError:
                    messagebox.showerror("Błąd",
                        "Dawny termin: podaj liczbę całkowitą ≥ 1.")
                    return
                konsument  = rat_p['cb_podmiot'].current() == 1
                DATA_GRAN  = date(2018, 7, 9)
            else:
                lata_st   = lata
                konsument = False
                DATA_GRAN = None

            czest_map = {0: "mies", 1: "kw", 2: "pol", 3: "rok", 4: "tydz"}
            czest = czest_map.get(rat_cb_czest.current(), "mies")

            def _next(i):
                if czest == "mies": return d0 + relativedelta(months=i)
                if czest == "kw":   return d0 + relativedelta(months=i * 3)
                if czest == "pol":  return d0 + relativedelta(months=i * 6)
                if czest == "rok":  return d0 + relativedelta(years=i)
                return d0 + timedelta(weeks=i)

            dzis = date.today()
            raty = []
            for i in range(n):
                wym = _next(i)
                if przej and wym < DATA_GRAN:
                    ost, pi = _oblicz_przejsciowe(wym, lata, lata_st, konsument)
                    if pi['tryb'] == 'stare_pred_now':
                        podst = "stare (pred 2018)"
                    elif pi['konsument_korekta']:
                        podst = "konsument ★"
                    elif pi['wybrany'] == 'stare':
                        podst = "stare prawo"
                    else:
                        podst = "nowe + k.r."
                else:
                    _, ost = _upływ(wym, lata)
                    podst  = "nowe prawo"
                przed     = dzis > ost
                pozostalo = (ost - dzis).days if not przed else None
                raty.append({'nr': i + 1, 'wym': wym, 'ost': ost,
                             'przed': przed, 'pozostalo': pozostalo,
                             'podst': podst})

            self._clear_frame(rat_result)
            rb = tk.Frame(rat_result, bg=BG)
            rb.pack(fill="x")

            nagl = "  ⏳  Przedawnienie — świadczenia w ratach"
            if przej:
                nagl += "  [przepisy przejściowe]"
            tk.Label(rb, text=nagl, font=self.app.f_sub,
                     bg=BG, fg=GOLD).pack(anchor="w", padx=16, pady=(12, 8))

            n_przed = sum(1 for r in raty if r['przed'])
            n_ok    = n - n_przed
            self._res_row(rb, "Łączna liczba rat:", str(n))
            self._res_row(rb, "Raty przedawnione:",
                          str(n_przed), color="#eb5757" if n_przed else "#6fcf97")
            self._res_row(rb, "Raty nieprzedawnione:",
                          str(n_ok),    color="#6fcf97" if n_ok else MUTED)
            tk.Frame(rb, bg="#333355", height=1).pack(fill="x", padx=16, pady=4)

            tbl = tk.Frame(rat_result, bg=PANEL,
                           highlightthickness=1, highlightbackground=BORDER)
            tbl.pack(fill="x", pady=(6, 0))

            hdr_r = tk.Frame(tbl, bg=BG)
            hdr_r.pack(fill="x")
            cols = [("Nr", 5), ("Wymagalność raty", 18),
                    ("Upływ przedawnienia", 20), ("Status", 22)]
            if przej:
                cols.insert(3, ("Podstawa", 14))
            for txt, w in cols:
                tk.Label(hdr_r, text=txt, font=self.app.f_small_bold, bg=BG, fg=GOLD,
                         width=w, anchor="w").pack(side="left", padx=8, pady=6)

            for r in raty:
                if r['przed']:
                    bg_r = "#2a1a1a"; fg_st = "#eb5757"; st = "⚠  PRZEDAWNIONA"
                elif r['pozostalo'] is not None and r['pozostalo'] <= 90:
                    bg_r = "#2a2a12"; fg_st = GOLD_LT
                    st   = f"⚡  wygasa za {r['pozostalo']} dni"
                else:
                    bg_r = "#1a2a1a"; fg_st = "#6fcf97"
                    st   = f"✅  {r['pozostalo']} dni" if r['pozostalo'] is not None else "✅"

                rf = tk.Frame(tbl, bg=bg_r)
                rf.pack(fill="x")
                tk.Frame(tbl, bg="#333355", height=1).pack(fill="x")
                tk.Label(rf, text=str(r['nr']),
                         font=self.app.f_body, bg=bg_r, fg="#cccccc",
                         width=5, anchor="w").pack(side="left", padx=8, pady=4)
                tk.Label(rf, text=r['wym'].strftime("%d.%m.%Y"),
                         font=self.app.f_body, bg=bg_r, fg="#cccccc",
                         width=18, anchor="w").pack(side="left", padx=8)
                tk.Label(rf, text=r['ost'].strftime("%d.%m.%Y"),
                         font=self.app.f_bold, bg=bg_r, fg=GOLD_LT,
                         width=20, anchor="w").pack(side="left", padx=8)
                if przej:
                    fg_p = {"stare (pred 2018)": "#eb5757",
                            "stare prawo": "#aaaaaa",
                            "nowe + k.r.": "#6fcf97",
                            "konsument ★": "#6fcf97",
                            "nowe prawo": "#555577"}.get(r['podst'], "#aaaaaa")
                    tk.Label(rf, text=r['podst'],
                             font=self.app.f_small_bold, bg=bg_r, fg=fg_p,
                             width=14, anchor="w").pack(side="left", padx=8)
                tk.Label(rf, text=st,
                         font=self.app.f_small_bold, bg=bg_r, fg=fg_st,
                         width=22, anchor="w").pack(side="left", padx=8)

            foot = tk.Frame(tbl, bg=BG)
            foot.pack(fill="x")
            foot_txt = (f"Termin: {_lata_str(lata)}  ·  {rat_cb.get()[:60]}"
                        + (f"  |  Dawny: {_lata_str(lata_st)}"
                           + ("  |  Konsument (art. 5 ust. 3)" if konsument else "")
                           if przej else "")
                        + "  |  ⚡ pozostało ≤ 90 dni")
            tk.Label(foot, text=foot_txt,
                     font=self.app.f_small, bg=BG, fg="#888888",
                     wraplength=880, justify="left").pack(anchor="w", padx=10, pady=6)

            tk.Label(rat_result, text="", bg=CREAM, height=1).pack()

        bf2 = tk.Frame(frame, bg=CREAM)
        bf2.pack(fill="x", padx=20, pady=(4, 0))
        self._btn(bf2, "⏳  Oblicz przedawnienie rat",
                  oblicz_raty_pf, gold=True).pack(side="left", pady=4)
        rat_result.pack(fill="x", padx=20, pady=(0, 20))
