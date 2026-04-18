# -*- coding: utf-8 -*-
"""
abuzywny.py -- Kalkulator pozyczki ratalnej po eliminacji klauzul abuzywnych.

Podstawa prawna:
  art. 3851 KC  -- klauzule niedozwolone (niewiążące konsumenta)
  art. 36a u.k.k. -- limit pozaodsetkowych kosztów kredytu
  art. 405/410 KC -- nienależne świadczenie (zwrot nadpłaty)
  art. 359 KC   -- odsetki
  art. 481 KC   -- odsetki za opóźnienie
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date, datetime

from constants import (CREAM, PANEL, BG, GOLD, GOLD_LT, TEXT, MUTED,
                       BORDER, GREEN, RED, fmt, safe_float)


# ── Helpers obliczeniowe ───────────────────────────────────────────────────────

def _safe_date(raw):
    """Zwraca datę z popularnych formatów lub None przy błędnych danych."""
    if raw is None:
        return None
    if isinstance(raw, date):
        return raw
    s = str(raw).strip()
    if not s:
        return None
    for fmt_str in ("%Y-%m-%d", "%d-%m-%Y", "%d.%m.%Y"):
        try:
            return datetime.strptime(s, fmt_str).date()
        except ValueError:
            pass
    return None


def oblicz_odsetki(podstawa: float, stopa_pct: float, od, do, metoda: str = "proste") -> float:
    """Proste narzędzie pomocnicze do naliczania odsetek od salda."""
    od_d = _safe_date(od)
    do_d = _safe_date(do)
    if podstawa <= 0 or stopa_pct <= 0 or not od_d or not do_d or od_d >= do_d:
        return 0.0

    lata = (do_d - od_d).days / 365.25
    stopa = stopa_pct / 100.0
    if metoda == "skladane":
        return podstawa * ((1.0 + stopa) ** lata - 1.0)
    return podstawa * stopa * lata


def oblicz_zobowiazanie(
    skladniki: list,
    splaty: list,
    stopa: float = 0.0,
    od=None,
    do=None,
    metoda: str = "proste",
) -> dict:
    """Zachowana zgodność wsteczna dla starszych testów i prostych wyliczeń."""
    suma_total = sum(max(0.0, float(x.get("kwota", 0.0))) for x in skladniki)
    suma_abuz = sum(
        max(0.0, float(x.get("kwota", 0.0)))
        for x in skladniki
        if x.get("abuzywne")
    )
    po_redukcji = max(0.0, suma_total - suma_abuz)
    suma_splat = sum(max(0.0, float(x.get("kwota", 0.0))) for x in splaty)
    saldo = max(0.0, po_redukcji - suma_splat)
    nadplata = max(0.0, suma_splat - po_redukcji)
    odsetki = oblicz_odsetki(saldo, stopa, od, do, metoda) if saldo > 0 else 0.0
    do_zaplaty = saldo + odsetki if saldo > 0 else 0.0

    return {
        "suma_total": suma_total,
        "suma_abuz": suma_abuz,
        "po_redukcji": po_redukcji,
        "suma_splat": suma_splat,
        "saldo": saldo,
        "nadplata": nadplata,
        "odsetki": odsetki,
        "do_zaplaty": do_zaplaty,
        "stopa": stopa,
        "od": _safe_date(od),
        "do": _safe_date(do),
        "metoda": metoda,
    }

def _pmt(kapital: float, stopa_pct: float, n_rat: int) -> float:
    """Rata annuitetowa (PLN). stopa_pct -- roczna stopa w % (np. 20.5)."""
    if n_rat <= 0 or kapital <= 0:
        return 0.0
    if stopa_pct <= 0:
        return kapital / n_rat
    r = stopa_pct / 100.0 / 12.0
    return kapital * r / (1.0 - (1.0 + r) ** (-n_rat))


def oblicz_mpkk(kapital: float, n_dni: int) -> float:
    """
    Maksymalne pozaodsetkowe koszty kredytu (art. 36a u.k.k.).

    Dla okresu <  30 dni : MPKK = K x 5%                           (art. 36a ust. 1a)
    Dla okresu >= 30 dni : MPKK = K x 10%  +  K x (n/365) x 10%   (art. 36a ust. 1)
    Cap: MPKK ≤ 45% całkowitej kwoty kredytu                       (art. 36a ust. 2)

    Brzmienie aktualne po nowelizacji ustawą z 6.10.2022 r. (Dz.U. 2022 poz. 2339),
    obowiązującej od 18.12.2022 r.
    Granica: „nie krótszy niż 30 dni" (ust. 1) vs „krótszy niż 30 dni" (ust. 1a),
    czyli n = 30 stosuje ust. 1 (wzór procentowy), nie ust. 1a (5%).
    """
    if kapital <= 0 or n_dni <= 0:
        return 0.0
    if n_dni < 30:
        return kapital * 0.05
    mpkk = kapital * 0.10 + kapital * (n_dni / 365.0) * 0.10
    return min(mpkk, kapital * 0.45)


def oblicz_pozyczke(
    kwota_calkowita: float,
    kapital_netto: float,
    pozaodsetkowe: float,
    pozaodsetkowe_nieabuzywne: float,
    n_rat: int,
    stopa_pct: float,
    rat_zaplacono: int,
    rat_wypowiedzenia: int,
    mpkk: float = 0.0,
    n_dni: int = 0,
    kwota_zaplacona_input: float = 0.0,
) -> dict:
    """
    Oblicza zobowiązanie pożyczkowe po eliminacji klauzul abuzywnych.

    Parametry:
        kwota_calkowita           -- pełna kwota pożyczki wg powoda (PLN)
        kapital_netto             -- kwota oddana pożyczkobiorcy do rąk (PLN)
        pozaodsetkowe             -- łączne koszty pozaodsetkowe wg powoda (PLN)
        pozaodsetkowe_nieabuzywne -- część pozaodsetkowych uznana za legalną (PLN)
        n_rat                     -- liczba rat
        stopa_pct                 -- umówiona roczna stopa odsetek kapitalowych (%)
        rat_zaplacono             -- liczba rat faktycznie zapłaconych
                                    (ignorowane gdy kwota_zaplacona_input > 0)
        rat_wypowiedzenia         -- numer raty, po której nastąpiło wypowiedzenie
                                    (0 = brak wypowiedzenia lub przed 1. ratą)
        mpkk                      -- limit MPKK z art. 36a u.k.k. (0 = nie obliczono)
        n_dni                     -- okres umowy w dniach (0 = nie podano)
        kwota_zaplacona_input     -- bezpośrednia kwota spłacona przez pozwanego (PLN);
                                    gdy > 0 zastępuje rat_zaplacono * rata
    """
    pozaodsetkowe_abuzywne = max(0.0, pozaodsetkowe - pozaodsetkowe_nieabuzywne)

    # Rata kontrolna (powód dzieli całą kwotę przez liczbę rat)
    rata_powoda = kwota_calkowita / n_rat if n_rat > 0 else 0.0

    # Zobowiązanie po eliminacji klauzul abuzywnych
    # = annuity(kapitał netto + nieabuzywne koszty pozaodsetkowe)
    kapital_efektywny = kapital_netto + pozaodsetkowe_nieabuzywne
    rata = _pmt(kapital_efektywny, stopa_pct, n_rat)
    zobowiazanie = rata * n_rat

    # Kwota już zapłacona przez pozwanego
    # Tryb kwotowy: podana wprost (np. gdy spłacono niepełne raty)
    # Tryb ratowy:  liczba_rat × rata
    if kwota_zaplacona_input > 0:
        kwota_zaplacona = kwota_zaplacona_input
        tryb_splaty = "kwota"
    else:
        kwota_zaplacona = rat_zaplacono * rata
        tryb_splaty = "raty"

    outstanding = max(0.0, zobowiazanie - kwota_zaplacona)

    # Ocena wypowiedzenia przy założeniu umownego progu 2 pełnych rat zaległych.
    # To częsta klauzula kontraktowa, ale nie uniwersalna reguła ustawowa dla
    # wszystkich pożyczek konsumenckich.
    if rat_wypowiedzenia <= 0:
        wypowiedzenie_ok = False
        zaleglosci = 0
        kwota_zalegla = 0.0
    else:
        kwota_wymagalna_wyp = rat_wypowiedzenia * rata
        kwota_zalegla = max(0.0, kwota_wymagalna_wyp - kwota_zaplacona)
        # Liczba pełnych rat zaległych (floor) dla przyjętego progu umownego.
        zaleglosci = int(kwota_zalegla / rata) if rata > 0 else 0
        wypowiedzenie_ok = zaleglosci >= 2

    # Kwoty do zapłaty
    if rat_wypowiedzenia <= 0:
        # Brak wypowiedzenia -- całość zobowiązania wg harmonogramu
        do_zaplaty = outstanding
        niewymagalne = 0.0
    elif wypowiedzenie_ok:
        # Prawidłowe wypowiedzenie -- cały dług staje się natychmiast wymagalny
        do_zaplaty = outstanding
        niewymagalne = 0.0
    else:
        # Nieprawidłowe wypowiedzenie -- tylko kwota zaległa jest wymagalna
        do_zaplaty = kwota_zalegla
        niewymagalne = max(0.0, outstanding - do_zaplaty)

    return {
        "kwota_calkowita":           kwota_calkowita,
        "kapital_netto":             kapital_netto,
        "pozaodsetkowe":             pozaodsetkowe,
        "pozaodsetkowe_nieabuzywne": pozaodsetkowe_nieabuzywne,
        "pozaodsetkowe_abuzywne":    pozaodsetkowe_abuzywne,
        "n_rat":                     n_rat,
        "stopa_pct":                 stopa_pct,
        "rata_powoda":               rata_powoda,
        "rata":                      rata,
        "zobowiazanie":              zobowiazanie,
        "rat_zaplacono":             rat_zaplacono,
        "kwota_zaplacona":           kwota_zaplacona,
        "kwota_zaplacona_bezp":      kwota_zaplacona_input,
        "tryb_splaty":               tryb_splaty,
        "outstanding":               outstanding,
        "rat_wypowiedzenia":         rat_wypowiedzenia,
        "wypowiedzenie_ok":          wypowiedzenie_ok,
        "zaleglosci":                zaleglosci,
        "kwota_zalegla":             kwota_zalegla,
        "do_zaplaty":                do_zaplaty,
        "niewymagalne":              niewymagalne,
        "mpkk":                      mpkk,
        "n_dni":                     n_dni,
    }


# ── Widżet zakładki ────────────────────────────────────────────────────────────

class TabAbuzywny(tk.Frame):
    """
    Zakładka: Pożyczka ratalna -- eliminacja klauzul abuzywnych.

    Oblicza rzeczywiste zobowiązanie pożyczkobiorcy po eliminacji
    niedozwolonych postanowień umownych (art. 3851 KC), uwzględniając
    koszty pozaodsetkowe, liczbę rat, umówioną stopę procentową
    oraz pomocniczą ocenę wypowiedzenia przy założeniu progu 2 pełnych rat.
    """

    def __init__(self, master, fonts: dict, **kwargs):
        super().__init__(master, bg=CREAM, **kwargs)
        self.f = fonts
        self._build()

    # ── Budowa layoutu ────────────────────────────────────────────────────────

    def _build(self):
        canvas = tk.Canvas(self, bg=CREAM, highlightthickness=0)
        vsb = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        self._main = tk.Frame(canvas, bg=CREAM)
        win = canvas.create_window((0, 0), window=self._main, anchor="nw")

        self._main.bind("<Configure>",
                        lambda e: canvas.configure(
                            scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
                    lambda e: canvas.itemconfig(win, width=e.width))

        def _scroll(e):
            canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
        canvas.bind("<Enter>",
                    lambda e: canvas.bind_all("<MouseWheel>", _scroll))
        canvas.bind("<Leave>",
                    lambda e: canvas.unbind_all("<MouseWheel>"))

        m = self._main

        tk.Label(m, text="Pożyczka ratalna -- eliminacja klauzul abuzywnych",
                 font=self.f["sub"], bg=CREAM, fg=TEXT
                 ).pack(anchor="w", padx=20, pady=(14, 2))
        tk.Label(m,
                 text="Art. 3851 KC · art. 36a u.k.k.  "
                      "· oblicz rzeczywiste zobowiązanie po usunięciu niedozwolonych postanowień",
                 font=self.f["small"], bg=CREAM, fg=MUTED
                 ).pack(anchor="w", padx=20, pady=(0, 6))

        self._build_dane(m)
        self._build_koszty(m)
        self._build_splaty(m)
        self._build_przyciski(m)
        self._build_wyniki_placeholder(m)

    def _karta(self, parent, title: str, kolor: str = "#1a5fa8") -> tk.Frame:
        """Tworzy kartę-sekcję z kolorowym paskiem bocznym. Zwraca inner Frame."""
        outer = tk.Frame(parent, bg=CREAM)
        outer.pack(fill="x", padx=20, pady=(10, 0))

        card = tk.Frame(outer, bg=PANEL,
                        highlightthickness=1, highlightbackground=BORDER)
        card.pack(fill="x")

        hdr = tk.Frame(card, bg=PANEL)
        hdr.pack(fill="x")
        tk.Frame(hdr, bg=kolor, width=5).pack(side="left", fill="y")
        tk.Label(hdr, text=f"  {title}",
                 font=self.f["bold"], bg=PANEL, fg=TEXT, anchor="w"
                 ).pack(fill="x", padx=4, pady=8)
        tk.Frame(card, bg=BORDER, height=1).pack(fill="x")

        inner = tk.Frame(card, bg=PANEL)
        inner.pack(fill="x", padx=14, pady=(10, 14))
        return inner

    def _pole(self, parent, row: int, label: str,
              hint: str = "", val: str = "") -> tk.Entry:
        """Tworzy parę etykieta + Entry w gridzie (kolumny 0-2)."""
        tk.Label(parent, text=label, font=self.f["small"],
                 bg=PANEL, fg=MUTED
                 ).grid(row=row, column=0, sticky="w",
                        padx=(0, 8), pady=(6, 1))
        e = tk.Entry(parent, font=self.f["body"], relief="flat", bd=0,
                     bg=CREAM, fg=TEXT, width=18,
                     highlightthickness=1, highlightbackground=BORDER)
        e.grid(row=row, column=1, sticky="ew", padx=(4, 8), pady=2, ipady=4)
        if val:
            e.insert(0, val)
        if hint:
            tk.Label(parent, text=hint, font=self.f["small"],
                     bg=PANEL, fg="#aaaaaa"
                     ).grid(row=row, column=2, sticky="w", padx=(0, 8))
        return e

    # ── Sekcja 1: Dane pożyczki ───────────────────────────────────────────────

    def _build_dane(self, parent):
        g = self._karta(parent, "1 ·  Dane pożyczki (wg powoda)",
                        kolor="#1565c0")
        g.columnconfigure(1, weight=1)

        self.e_kwota_calkowita = self._pole(
            g, 0,
            "Całkowita kwota pożyczki wg powoda (PLN):",
            "np. 17 792,97")
        self.e_kapital_netto = self._pole(
            g, 1,
            "Kapitał netto -- kwota oddana do rąk pożyczkobiorcy (PLN):",
            "np. 8 000,00")
        self.e_n_rat = self._pole(
            g, 2,
            "Liczba rat:",
            "np. 24")
        self.e_stopa = self._pole(
            g, 3,
            "Umówiona roczna stopa odsetek kapitałowych (%):",
            "np. 20,50 - jeżeli brak odsetek wstaw 0")

    # ── Sekcja 2: Koszty pozaodsetkowe ───────────────────────────────────────

    def _build_koszty(self, parent):
        g = self._karta(parent, "2 ·  Koszty pozaodsetkowe i limit MPKK",
                        kolor="#6a1b9a")
        g.columnconfigure(1, weight=1)

        # ---- Wiersz 0: okres umowy (n_dni) ----------------------------------
        self.e_n_dni = self._pole(
            g, 0,
            "Okres umowy (liczba dni od zawarcia do ostatniej raty):",
            "np. 730 (2 lata)  ·  decyduje o wzorze MPKK")

        # ---- Wiersz 1: wynik MPKK + przycisk --------------------------------
        mpkk_row = tk.Frame(g, bg=PANEL)
        mpkk_row.grid(row=1, column=0, columnspan=3,
                      sticky="ew", pady=(6, 0))

        self._lbl_mpkk = tk.Label(
            mpkk_row,
            text="  MPKK (art. 36a u.k.k.): -- (wpisz kapital netto i okres umowy)",
            font=self.f["small"], bg="#f0eaff", fg="#5a3e8a",
            anchor="w", padx=6, pady=5)
        self._lbl_mpkk.pack(side="left", fill="x", expand=True)

        tk.Button(
            mpkk_row,
            text="Zastosuj MPKK",
            font=self.f["small"], bg="#6a1b9a", fg="white",
            relief="flat", padx=10, pady=4, cursor="hand2",
            command=self._zastosuj_mpkk
        ).pack(side="right", padx=6)

        # ---- Wiersz 2: koszty wg powoda ------------------------------------
        self.e_pozaodsetkowe = self._pole(
            g, 2,
            "Pozaodsetkowe koszty łącznie wg powoda (PLN):",
            "prowizja + ubezpieczenie + inne opłaty")

        # ---- Wiersz 3: koszty nieabuzywne ----------------------------------
        self.e_pozaodsetkowe_nieabuz = self._pole(
            g, 3,
            "Pozaodsetkowe nieabuzywne (PLN):",
            "0 = wszystkie abuzywne  ·  lub kliknij 'Zastosuj MPKK'",
            val="0")

        # ---- Wiersz 4: koszty abuzywne (auto) ------------------------------
        self._lbl_abuz = tk.Label(
            g,
            text="  Pozaodsetkowe abuzywne (wyliczone):  --",
            font=self.f["small"], bg=PANEL, fg="#e74c3c")
        self._lbl_abuz.grid(row=4, column=0, columnspan=3,
                             sticky="w", pady=(4, 0))

        # ---- Wiersz 5: nota prawna ----------------------------------------
        tk.Label(
            g,
            text="ℹ  Art. 36a u.k.k. (brzmienie po nowelizacji z 2022 r.):\n"
                 "  Okres > 30 dni:  MPKK = K x 10% + K x (n/365) x 10%  "
                 "(maks. 45% K)\n"
                 "  Okres <= 30 dni: MPKK = K x 5%",
            font=self.f["small"], bg="#f8f4ff", fg="#5a3e8a",
            wraplength=580, justify="left", anchor="w",
            padx=8, pady=7
        ).grid(row=5, column=0, columnspan=3, sticky="ew",
               padx=0, pady=(10, 0))

        # ---- Bindowania (odswiezanie na biezaco) ---------------------------
        for e in (self.e_pozaodsetkowe, self.e_pozaodsetkowe_nieabuz,
                  self.e_n_dni):
            e.bind("<KeyRelease>", lambda _e: self._aktualizuj_abuz())

        # Kapital netto z sekcji 1 takze wplywa na MPKK
        self.e_kapital_netto.bind(
            "<KeyRelease>", lambda _e: self._aktualizuj_abuz())

        self._aktualizuj_abuz()

    def _aktualizuj_abuz(self):
        # -- abuzywne = roznica miedzy kosztami powoda a nieabuzywna czescia --
        poz  = safe_float(self.e_pozaodsetkowe)
        niab = safe_float(self.e_pozaodsetkowe_nieabuz)
        abuz = max(0.0, poz - niab)
        self._lbl_abuz.config(
            text=f"  Pozaodsetkowe abuzywne (wyliczone):  {fmt(abuz)}")

        # -- MPKK na zywo (art. 36a u.k.k.) ----------------------------------
        kapital = safe_float(self.e_kapital_netto)
        n_dni_s = self.e_n_dni.get().strip().replace(",", ".")
        try:
            n_dni = int(float(n_dni_s)) if n_dni_s else 0
        except (ValueError, TypeError):
            n_dni = 0

        if kapital > 0 and n_dni > 0:
            mpkk = oblicz_mpkk(kapital, n_dni)
            if n_dni <= 30:
                formula = f"K x 5%  (okres <= 30 dni)"
            else:
                wartosc_bez_cap = kapital * 0.10 + kapital * (n_dni / 365.0) * 0.10
                cap_aktywny = wartosc_bez_cap > kapital * 0.45
                formula = (
                    f"K x 10% + K x {n_dni}/365 x 10%"
                    + ("  [CAP 45%]" if cap_aktywny else "")
                )
            nadwyzka = max(0.0, poz - mpkk) if poz > 0 else 0.0
            info = f"  nadwyzka nad MPKK: {fmt(nadwyzka)}" if nadwyzka > 0 else ""
            self._lbl_mpkk.config(
                text=f"  MPKK (art. 36a u.k.k.):  {fmt(mpkk)}   [{formula}]{info}",
                bg="#e8f5e9", fg="#1b5e20")
        else:
            self._lbl_mpkk.config(
                text="  MPKK (art. 36a u.k.k.): -- (wpisz kapital netto i okres umowy)",
                bg="#f0eaff", fg="#5a3e8a")

    def _zastosuj_mpkk(self):
        """Kopiuje obliczony limit MPKK do pola 'pozaodsetkowe nieabuzywne'."""
        kapital = safe_float(self.e_kapital_netto)
        n_dni_s = self.e_n_dni.get().strip().replace(",", ".")
        try:
            n_dni = int(float(n_dni_s)) if n_dni_s else 0
        except (ValueError, TypeError):
            n_dni = 0

        if kapital <= 0 or n_dni <= 0:
            messagebox.showwarning(
                "Brak danych",
                "Aby zastosowac MPKK, wpisz najpierw:\n"
                "  - Kapitał netto (sekcja 1)\n"
                "  - Okres umowy w dniach (sekcja 2)",
                parent=self)
            return

        mpkk = oblicz_mpkk(kapital, n_dni)
        self.e_pozaodsetkowe_nieabuz.delete(0, "end")
        self.e_pozaodsetkowe_nieabuz.insert(0, f"{mpkk:.2f}".replace(".", ","))
        self._aktualizuj_abuz()

    # ── Sekcja 3: Spłaty ─────────────────────────────────────────────────────

    def _build_splaty(self, parent):
        g = self._karta(parent, "3 ·  Spłaty",
                        kolor="#2e7d32")
        g.columnconfigure(1, weight=1)

        # ---- Kwota spłacona ------------------------------------------------
        self.e_kwota_zaplacona = self._pole(
            g, 0,
            "Kwota spłacona przez pozwanego (PLN):",
            "wpisz łączną kwotę wpłaconą przez pozwanego (0 jeśli nic nie zapłacił)")

        # ---- Wypowiedzenie -------------------------------------------------
        self.e_rat_wyp = self._pole(
            g, 1,
            "Po której racie nastąpiło wypowiedzenie:",
            "np. 3 - jeżeli nie wypowiedziano wpisz 0",
            val="0")

    # ── Przyciski ─────────────────────────────────────────────────────────────

    def _build_przyciski(self, parent):
        bf = tk.Frame(parent, bg=CREAM)
        bf.pack(fill="x", padx=20, pady=14)

        tk.Button(bf, text="⚖  OBLICZ ZOBOWIĄZANIE",
                  font=self.f["bold"], bg=GOLD, fg=BG,
                  relief="flat", padx=22, pady=10, cursor="hand2",
                  command=self._oblicz
                  ).pack(side="left")

        tk.Button(bf, text="🗑  Wyczyść formularz",
                  font=self.f["small"], bg="#3a3a5a", fg=CREAM,
                  relief="flat", padx=14, pady=10, cursor="hand2",
                  command=self._wyczysc
                  ).pack(side="left", padx=(10, 0))

    # ── Placeholder wyników ───────────────────────────────────────────────────

    def _build_wyniki_placeholder(self, parent):
        self._wyniki_frame = tk.Frame(parent, bg=CREAM)
        self._wyniki_frame.pack(fill="x", padx=20, pady=(0, 20))

    # ── Logika obliczeniowa ───────────────────────────────────────────────────

    def _oblicz(self):
        def _int_nn(e, name):
            """Parsuje pole jako int >= 0; przy błędzie pokazuje komunikat i zwraca None."""
            s = e.get().strip().replace(",", ".")
            try:
                v = int(float(s))
                if v < 0:
                    raise ValueError
                return v
            except (ValueError, TypeError):
                messagebox.showerror(
                    "Błąd danych",
                    f'Pole "{name}" musi byc liczba calkowita >= 0.',
                    parent=self)
                return None

        kwota_calkowita = safe_float(self.e_kwota_calkowita)
        kapital_netto   = safe_float(self.e_kapital_netto)
        pozaodsetkowe   = safe_float(self.e_pozaodsetkowe)
        pozaodsetkowe_nieabuz = safe_float(self.e_pozaodsetkowe_nieabuz)

        stopa_s = self.e_stopa.get().strip().replace(",", ".")
        try:
            stopa = float(stopa_s) if stopa_s else 0.0
        except ValueError:
            stopa = 0.0

        # Okres umowy -- potrzebny do obliczenia limitu MPKK (art. 36a u.k.k.)
        n_dni_s = self.e_n_dni.get().strip().replace(",", ".")
        try:
            n_dni = int(float(n_dni_s)) if n_dni_s else 0
        except (ValueError, TypeError):
            n_dni = 0

        n_rat = _int_nn(self.e_n_rat, "Liczba rat")
        if n_rat is None:
            return
        if n_rat == 0:
            messagebox.showerror("Błąd danych",
                                 "Liczba rat musi wynosić co najmniej 1.",
                                 parent=self)
            return

        kwota_zaplacona_input = safe_float(self.e_kwota_zaplacona)
        rat_zaplacono = 0

        rat_wyp = _int_nn(self.e_rat_wyp,
                          "Numer raty, po której nastąpiło wypowiedzenie")
        if rat_wyp is None:
            return

        if kapital_netto <= 0:
            messagebox.showerror("Błąd danych",
                                 "Kapitał netto musi być większy od zera.",
                                 parent=self)
            return

        mpkk = oblicz_mpkk(kapital_netto, n_dni)

        w = oblicz_pozyczke(
            kwota_calkowita, kapital_netto, pozaodsetkowe,
            pozaodsetkowe_nieabuz, n_rat, stopa,
            rat_zaplacono, rat_wyp,
            mpkk=mpkk, n_dni=n_dni,
            kwota_zaplacona_input=kwota_zaplacona_input)
        self._pokaz_wyniki(w)

    # ── Wyświetlanie wyników ──────────────────────────────────────────────────

    def _pokaz_wyniki(self, w: dict):
        for child in self._wyniki_frame.winfo_children():
            child.destroy()

        box = tk.Frame(self._wyniki_frame, bg=BG)
        box.pack(fill="x")

        def pasek(tekst: str):
            s = tk.Frame(box, bg="#1a1a35")
            s.pack(fill="x", pady=(8, 0))
            tk.Label(s, text=f"  {tekst}",
                     font=self.f["small_bold"],
                     bg="#1a1a35", fg=GOLD
                     ).pack(anchor="w", padx=14, pady=5)

        def wiersz(etykieta: str, wartosc: str,
                   kolor=GOLD_LT, pogrubiony: bool = False):
            r = tk.Frame(box, bg=BG)
            r.pack(fill="x", padx=14, pady=3)
            tk.Label(r, text=etykieta, font=self.f["body"],
                     bg=BG, fg="#aaaaaa").pack(side="left")
            fnt = self.f.get("big", self.f["result"]) if pogrubiony \
                  else self.f["result"]
            tk.Label(r, text=wartosc, font=fnt,
                     bg=BG, fg=kolor).pack(side="right")
            tk.Frame(box, bg="#26263e", height=1).pack(fill="x", padx=14)

        # Nagłówek
        tk.Label(box, text="  WYNIKI -- ZOBOWIĄZANIE PO ELIMINACJI KLAUZUL  ",
                 font=self.f["bold"], bg=BG, fg=GOLD
                 ).pack(anchor="w", padx=14, pady=(12, 4))
        tk.Frame(box, bg=GOLD, height=2).pack(fill="x", padx=14, pady=(0, 4))

        # ── Dane wg powoda ────────────────────────────────────────────────────
        pasek("CAŁKOWITA KWOTA POŻYCZKI WG POWODA")
        wiersz("Całkowita kwota pożyczki wg powoda:",
               fmt(w["kwota_calkowita"]))
        wiersz("  z tego kapitał netto oddany do rąk pozwanego:",
               fmt(w["kapital_netto"]))
        wiersz("  pozaodsetkowe koszty wg powoda:",
               fmt(w["pozaodsetkowe"]))
        wiersz("     w tym nieabuzywne:",
               fmt(w["pozaodsetkowe_nieabuzywne"]))
        wiersz("     w tym abuzywne -- eliminowane (art. 3851 KC):",
               f"- {fmt(w['pozaodsetkowe_abuzywne'])}", kolor="#e74c3c")

        # ── Limit MPKK (art. 36a u.k.k.) ─────────────────────────────────────
        pasek("LIMIT MPKK -- ART. 36a U.K.K.")
        if w["n_dni"] > 0:
            if w["n_dni"] <= 30:
                formula_txt = f"K x 5%  (okres {w['n_dni']} dni -- <= 30 dni)"
            else:
                wartosc_bez_cap = (w["kapital_netto"] * 0.10
                                   + w["kapital_netto"] * (w["n_dni"] / 365.0) * 0.10)
                cap_aktywny = wartosc_bez_cap > w["kapital_netto"] * 0.45
                formula_txt = (
                    f"K x 10% + K x {w['n_dni']}/365 x 10%"
                    + ("  [zastosowano cap 45%]" if cap_aktywny else "")
                    + f"  (okres {w['n_dni']} dni)"
                )
            wiersz("Limit ustawowy MPKK (art. 36a u.k.k.):",
                   fmt(w["mpkk"]), kolor="#9c27b0", pogrubiony=True)
            wiersz("  Zastosowana formula:",
                   formula_txt, kolor="#7b52ab")
            nadwyzka = max(0.0, w["pozaodsetkowe"] - w["mpkk"])
            if nadwyzka > 0:
                wiersz("  Nadwyżka kosztów wg powoda ponad limit MPKK:",
                       f"+ {fmt(nadwyzka)}", kolor="#e74c3c")
                wiersz("  Ocena kosztów pozaodsetkowych wg powoda:",
                       "PRZEKRACZAJĄ limit art. 36a u.k.k.", kolor="#e74c3c")
            else:
                wiersz("  Ocena kosztów pozaodsetkowych wg powoda:",
                       "mieszczą się w limicie art. 36a u.k.k.", kolor=GREEN)
        else:
            wiersz("Okres umowy:", "nie podano -- MPKK nie obliczono",
                   kolor=MUTED)

        # ── Rata kontrolna ────────────────────────────────────────────────────
        pasek("KONTROLNIE -- RATA WG POWODA")
        wiersz(f"Liczba rat: {w['n_rat']}  ·  "
               f"Rata kontrolna (kwota całkowita ÷ liczba rat):",
               fmt(w["rata_powoda"]))

        # ── Zobowiązanie po abuzywności ───────────────────────────────────────
        pasek("ZOBOWIĄZANIE PO ELIMINACJI KLAUZUL ABUZYWNYCH  (art. 3851 KC)")
        kapital_ef = w["kapital_netto"] + w["pozaodsetkowe_nieabuzywne"]
        wiersz("Podstawa annuity (kapitał + nieabuzywne):",
               fmt(kapital_ef))
        stopa_str = (f"{w['stopa_pct']:.4g}%" if w["stopa_pct"] > 0
                     else "0% (brak odsetek)")
        wiersz(f"Umówiona roczna stopa odsetek kapitałowych (nie RRSO):  {stopa_str}",
               "")
        wiersz(f"Tyle powinna wynosić rata po abuzywności  "
               f"({w['n_rat']} rat, annuity):",
               fmt(w["rata"]), kolor=GREEN)
        wiersz("Tyle powinien zapłacić łącznie pozwany:",
               fmt(w["zobowiazanie"]), kolor=GREEN, pogrubiony=True)

        # ── Spłaty ────────────────────────────────────────────────────────────
        pasek("TYLE ZDĄŻYŁ ZAPŁACIĆ POZWANY")
        wiersz("Kwota spłacona przez pozwanego:",
               fmt(w["kwota_zaplacona"]), kolor="#5dade2")

        # ── Wypowiedzenie ─────────────────────────────────────────────────────
        pasek("CZY WYPOWIEDZENIE BYLO PRAWIDŁOWE?  (założenie: próg 2 pełnych rat)")
        if w["rat_wypowiedzenia"] <= 0:
            wiersz("Numer raty, po ktorej nastapilo wypowiedzenie:", "--")
            wiersz("Ocena:",
                   "Brak wypowiedzenia",
                   kolor=MUTED, pogrubiony=True)
        elif w["wypowiedzenie_ok"]:
            wiersz(f"Wypowiedzenie po racie {w['rat_wypowiedzenia']}  "
                   f"-- zaleglosci na dzien wypowiedzenia: "
                   f"{w['zaleglosci']} pelnych rat  (wymagane >= 2):",
                   "Wypowiedzenie PRAWIDŁOWE",
                   kolor=GREEN, pogrubiony=True)
        else:
            wiersz(f"Wypowiedzenie po racie {w['rat_wypowiedzenia']}  "
                   f"-- zaleglosci na dzien wypowiedzenia: "
                   f"{w['zaleglosci']} pelnych rat  (wymagane >= 2):",
                   "Wypowiedzenie NIEPRAWIDŁOWE",
                   kolor="#e74c3c", pogrubiony=True)
        if w["rat_wypowiedzenia"] > 0:
            wiersz("Kwota zaległa na dzień wypowiedzenia:",
                   fmt(w["kwota_zalegla"]), kolor="#e67e22")

        # ── Do zapłaty ────────────────────────────────────────────────────────
        pasek("DO ZAPŁATY POZOSTAŁO")
        wiersz("Niespłacone zobowiązanie po abuzywności (łącznie):",
               fmt(w["outstanding"]))
        wiersz("Do zapłaty pozostało:",
               fmt(w["do_zaplaty"]), kolor=GOLD, pogrubiony=True)

        # ── Ewentualnie raty niewymagalne (tylko przy nieprawidłowym wyp.) ────
        pasek("EWENTUALNIE RATY NIEWYMAGALNE")
        if w["niewymagalne"] > 0:
            wiersz("Raty niewymagalne (nie podlegają przyspieszonemu dochodzeniu):",
                   fmt(w["niewymagalne"]), kolor=MUTED)
        else:
            wiersz("Raty niewymagalne:", fmt(0.0), kolor=MUTED)
        wiersz("DO ZAPŁATY POZOSTAŁO (finalnie):",
               fmt(w["do_zaplaty"]), kolor=GOLD, pogrubiony=True)

        # ── Podstawa prawna ───────────────────────────────────────────────────
        nota = tk.Frame(box, bg="#111128")
        nota.pack(fill="x", pady=(12, 0))
        tk.Label(nota,
                 text="Podstawa prawna:  "
                      "art. 3851 KC -- niedozwolone postanowienia umowne  ·  "
                      "art. 36a u.k.k. -- limit pozaodsetkowych kosztów kredytu  ·  "
                      "art. 405 i 410 KC -- nienależne świadczenie",
                 font=self.f["small"], bg="#111128", fg="#555577",
                 anchor="w", justify="left", wraplength=700,
                 padx=14, pady=8
                 ).pack(fill="x")

    # ── Wyczyść ───────────────────────────────────────────────────────────────

    def _wyczysc(self):
        """Czyści formularz i przywraca wartości domyślne."""
        for e in (self.e_kwota_calkowita, self.e_kapital_netto,
                  self.e_pozaodsetkowe, self.e_n_rat, self.e_stopa,
                  self.e_n_dni):
            e.delete(0, "end")

        self.e_pozaodsetkowe_nieabuz.delete(0, "end")
        self.e_pozaodsetkowe_nieabuz.insert(0, "0")

        self.e_kwota_zaplacona.delete(0, "end")

        self.e_rat_wyp.delete(0, "end")
        self.e_rat_wyp.insert(0, "0")

        self._aktualizuj_abuz()

        for child in self._wyniki_frame.winfo_children():
            child.destroy()
