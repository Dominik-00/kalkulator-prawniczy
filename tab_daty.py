# -*- coding: utf-8 -*-
"""
tab_daty.py — Zakładka 'Kalkulator dat (terminów procesowych)'.
Klasa TabDaty(tk.Frame) — przeniesiona z app.py (_tab_daty).
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta

from constants import (BG, PANEL, CREAM, GOLD, GOLD_LT, TEXT, MUTED,
                       BORDER)
from tab_base import TabBase
from logika_dat import (wielkanoc, swieta_rok, is_free_day, next_workday,
                        add_days_115, add_months_115, add_years_115,
                        oblicz_zasiedzenie_nieruchomosci, GRANICA_1990,
                        _SWIETA_CACHE)


class TabDaty(TabBase):
    """Zakładka kalkulatora terminów procesowych (prawomocność, wymagalność, zasiedzenie itp.)."""

    def __init__(self, master, app):
        super().__init__(master, app)
        self._build()

    # ── budowanie UI ─────────────────────────────────────────────────────────

    def _build(self):
        frame, _ = self._scrollable(self)

        tk.Label(frame, text="Kalkulator terminów procesowych",
                 font=self.app.f_sub, bg=CREAM, fg=TEXT).pack(anchor="w", padx=20, pady=(14, 2))
        tk.Label(frame,
                 text="KPC · KC · art. 115 KC — koniec terminu w dniu wolnym przesuwa się na najbliższy dzień roboczy",
                 font=self.app.f_small, bg=CREAM, fg=MUTED).pack(anchor="w", padx=20)

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

        # ── Święta i terminy — funkcje z logika_dat (zaimportowane na poziomie modułu)
        # wielkanoc, swieta_rok, is_free_day, next_workday,
        # add_days_115, add_months_115, add_years_115 dostępne przez import

        self.dt_result_frame = tk.Frame(frame, bg=CREAM)

        def clear_results():
            self._clear_frame(self.dt_result_frame)
            self.dt_result_frame.pack(fill="x", padx=20, pady=(4, 20))

        def show_result(title, rows_data):
            clear_results()
            rb = tk.Frame(self.dt_result_frame, bg=BG)
            rb.pack(fill="x")
            tk.Label(rb, text=f"  🗓  {title}",
                     font=self.app.f_sub, bg=BG, fg=GOLD).pack(anchor="w", padx=16, pady=(12, 6))

            for label, val, note, color in rows_data:
                row_f = tk.Frame(rb, bg=BG)
                row_f.pack(fill="x", padx=16, pady=2)
                tk.Label(row_f, text=label, font=self.app.f_body,
                         bg=BG, fg="#aaaaaa", anchor="w").pack(side="left")
                val_str = fmt_date(val) if isinstance(val, date) else str(val)
                fc = color if color else GOLD_LT
                tk.Label(row_f, text=val_str, font=self.app.f_result,
                         bg=BG, fg=fc).pack(side="right")
                tk.Frame(rb, bg="#2d2d4a", height=1).pack(fill="x", padx=16)
                if note:
                    tk.Label(rb, text=f"    ↳ {note}",
                             font=self.app.f_small, bg=BG, fg="#888888",
                             justify="left", wraplength=800).pack(
                        anchor="w", padx=16, pady=(0, 3))
            tk.Label(rb, text="", bg=BG, height=1).pack()

        def date_row(parent, row, label, hint="RRRR-MM-DD lub DD.MM.RRRR"):
            tk.Label(parent, text=label, font=self.app.f_small,
                     bg=PANEL, fg=MUTED).grid(
                row=row, column=0, sticky="w", pady=(6, 1), padx=(0, 8))
            e = tk.Entry(parent, font=self.app.f_body, relief="flat", bd=0,
                         bg=CREAM, fg=TEXT, width=17,
                         highlightthickness=1, highlightbackground=BORDER)
            e.grid(row=row, column=1, sticky="w", padx=(4, 8), pady=2, ipady=4)
            e.insert(0, date.today().strftime("%Y-%m-%d"))
            tk.Label(parent, text=hint, font=self.app.f_small,
                     bg=PANEL, fg="#aaaaaa").grid(row=row, column=2, sticky="w")
            return e

        def combo_row(parent, row, label, values, default=0):
            tk.Label(parent, text=label, font=self.app.f_small,
                     bg=PANEL, fg=MUTED).grid(
                row=row, column=0, sticky="w", pady=(6, 1))
            cb = ttk.Combobox(parent, values=values, state="readonly",
                              font=self.app.f_body, width=46)
            cb.current(default)
            cb.grid(row=row, column=1, columnspan=2, sticky="w",
                    padx=(4, 8), pady=2, ipady=2)
            return cb

        def calc_btn(parent, row, text, cmd):
            self._btn(parent, text, cmd, gold=True).grid(
                row=row, column=0, columnspan=3, sticky="w", pady=(10, 4))

        # ── KARTA 1 — PRAWOMOCNOŚĆ ────────────────────────────────────────
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
        ), font=self.app.f_small, bg="#f0f4ff", fg="#2a2a5a",
           justify="left", wraplength=840, padx=12, pady=8).pack(anchor="w")

        tk.Label(c1, text="Czy złożono wniosek o uzasadnienie?",
                 font=self.app.f_small, bg=PANEL, fg=MUTED).grid(
            row=1, column=0, sticky="w", pady=(4, 2))

        p1_tryb = tk.StringVar(value="bez_uzas")
        tryb_frame = tk.Frame(c1, bg=PANEL)
        tryb_frame.grid(row=1, column=1, columnspan=2, sticky="w", padx=(4, 0))
        tk.Radiobutton(tryb_frame, text="NIE — termin 7 dni od ogłoszenia/doręczenia",
                       variable=p1_tryb, value="bez_uzas",
                       bg=PANEL, font=self.app.f_body,
                       command=lambda: _toggle_p1()).pack(side="left")
        tk.Radiobutton(tryb_frame, text="TAK — termin od doręczenia z uzasadnieniem",
                       variable=p1_tryb, value="z_uzas",
                       bg=PANEL, font=self.app.f_body,
                       command=lambda: _toggle_p1()).pack(side="left", padx=(20, 0))

        p1_frame_a = tk.Frame(c1, bg=PANEL)
        p1_frame_a.grid(row=2, column=0, columnspan=3, sticky="ew")
        p1_frame_a.columnconfigure(2, weight=1)

        tk.Label(p1_frame_a, text="Data ogłoszenia / doręczenia orzeczenia:",
                 font=self.app.f_small, bg=PANEL, fg=MUTED).grid(
            row=0, column=0, sticky="w", pady=(6, 1), padx=(0, 8))
        e1a = tk.Entry(p1_frame_a, font=self.app.f_body, relief="flat", bd=0,
                       bg=CREAM, fg=TEXT, width=17,
                       highlightthickness=1, highlightbackground=BORDER)
        e1a.grid(row=0, column=1, sticky="w", padx=(4, 8), pady=2, ipady=4)
        e1a.insert(0, date.today().strftime("%Y-%m-%d"))
        tk.Label(p1_frame_a, text="RRRR-MM-DD lub DD.MM.RRRR",
                 font=self.app.f_small, bg=PANEL, fg="#aaaaaa").grid(row=0, column=2, sticky="w")

        p1_frame_b = tk.Frame(c1, bg=PANEL)
        p1_frame_b.grid(row=2, column=0, columnspan=3, sticky="ew")
        p1_frame_b.columnconfigure(2, weight=1)

        tk.Label(p1_frame_b, text="Data doręczenia orzeczenia z uzasadnieniem:",
                 font=self.app.f_small, bg=PANEL, fg=MUTED).grid(
            row=0, column=0, sticky="w", pady=(6, 1), padx=(0, 8))
        e1b = tk.Entry(p1_frame_b, font=self.app.f_body, relief="flat", bd=0,
                       bg=CREAM, fg=TEXT, width=17,
                       highlightthickness=1, highlightbackground=BORDER)
        e1b.grid(row=0, column=1, sticky="w", padx=(4, 8), pady=2, ipady=4)
        e1b.insert(0, date.today().strftime("%Y-%m-%d"))
        tk.Label(p1_frame_b, text="RRRR-MM-DD lub DD.MM.RRRR",
                 font=self.app.f_small, bg=PANEL, fg="#aaaaaa").grid(row=0, column=2, sticky="w")

        tk.Label(p1_frame_b, text="Rodzaj środka zaskarżenia:",
                 font=self.app.f_small, bg=PANEL, fg=MUTED).grid(
            row=1, column=0, sticky="w", pady=(6, 1))
        cb1b = ttk.Combobox(p1_frame_b, state="readonly", font=self.app.f_body, width=46,
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
                rows = [
                    ("Ogłoszenie / doręczenie orzeczenia:", d, None, None),
                    ("Ostatni dzień terminu na środek zaskarżenia (7 dni):", surowy,
                     "Art. 369 §2 KPC — gdy strona nie wniosła o uzasadnienie, termin do zaskarżenia wynosi 7 dni od ogłoszenia/doręczenia.", None),
                ]
                tytul = "Prawomocność — brak wniosku o uzasadnienie"

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
                rows = [
                    ("Doręczenie orzeczenia z uzasadnieniem:", d, None, None),
                    (f"Ostatni dzień terminu na środek zaskarżenia ({opis}):", surowy,
                     "Termin biegnie od daty doręczenia odpisu orzeczenia wraz z uzasadnieniem.", None),
                ]
                tytul = "Prawomocność — wniosek o uzasadnienie złożony"

            po_115 = next_workday(surowy)
            prawomocny = po_115 + relativedelta(days=1)
            if po_115 != surowy:
                rows.append(("Po art. 115 KC (dzień wolny → roboczy):", po_115,
                             "Koniec terminu przesunięty na pierwszy dzień roboczy.", GOLD_LT))
            rows.append(("Dzień uprawomocnienia się orzeczenia:", prawomocny,
                         "Orzeczenie prawomocne z upływem dnia następnego po ostatnim dniu terminu.",
                         "#6fcf97"))
            show_result(tytul, rows)

        calc_btn(c1, 3, "🗓  Oblicz prawomocność", oblicz_prawomocnosc)

        # ── KARTA 3 — WYMAGALNOŚĆ ─────────────────────────────────────────
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

        # ── KARTA 4 — KOMORNIK ────────────────────────────────────────────
        c4 = self._card(frame, "3.  Zawieszenie i umorzenie postępowania sądowego (art. 177 k.p.c.)", pady=10)
        c4.columnconfigure(2, weight=1)

        e4 = date_row(c4, 0, "Data doręczenia powodowi zobowiązania:",
                      hint="data skutecznego doręczenia wezwania komorniczego")

        tk.Label(c4,
                 text="(art. 177 KPC w zw. z art. 139(1) k.p.c.: zawieszenie po 2 mies.; art. 182 pkt 1 KPC: umorzenie po 3 mies. od zawieszenia)",
                 font=self.app.f_small, bg=PANEL, fg=MUTED).grid(
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

        # ── KARTA 5 — ZASIEDZENIE ─────────────────────────────────────────
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
                 font=self.app.f_small, bg="#f0f4ff", fg="#2a2a5a",
                 justify="left", wraplength=840, padx=12, pady=8).pack(anchor="w")

        e5 = date_row(c5, 1, "Data objęcia w posiadanie samoistne:")

        cb5_rodzaj = combo_row(c5, 2, "Przedmiot i rodzaj posiadania:", [
            "Nieruchomość — dobra wiara",
            "Nieruchomość — zła wiara",
            "Ruchomość — dobra wiara  (art. 174 KC: 3 lata)",
        ])

        tk.Label(c5,
                 text="(dla ruchomości nie stosuje się przepisów intertemporalnych 1990 r. — tylko 3 lata dobrej wiary)",
                 font=self.app.f_small, bg=PANEL, fg=MUTED).grid(
            row=3, column=0, columnspan=3, sticky="w", pady=(0, 4))

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
