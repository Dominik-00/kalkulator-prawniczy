# -*- coding: utf-8 -*-
"""
logika_dat.py — Czyste funkcje obliczeniowe dla terminów procesowych.

Wyodrębnione z tab_daty._build() w celu umożliwienia testowania jednostkowego
bez uruchamiania GUI Tkinter.

Podstawa prawna: art. 115 KC, art. 172–176 KC, art. 363/369 KPC.
"""

from datetime import date, timedelta
from dateutil.relativedelta import relativedelta


# ── Algorytm Gaussa — Wielkanoc ───────────────────────────────────────────────

def wielkanoc(rok: int) -> date:
    """
    Zwraca datę Niedzieli Wielkanocnej dla danego roku (algorytm Gaussa).

    Źródło: algorytm Gaussa z poprawkami dla wyjątków 26 IV i 25 IV.
    """
    a = rok % 19
    b = rok % 4
    c = rok % 7
    d = (19 * a + 24) % 30
    e = (2 * b + 4 * c + 6 * d + 5) % 7
    dzien = 22 + d + e
    miesiac = 3
    if dzien > 31:
        dzien -= 31
        miesiac = 4
    if miesiac == 4 and dzien == 26:
        dzien = 19
    if miesiac == 4 and dzien == 25 and d == 28 and e == 6 and a > 10:
        dzien = 18
    return date(rok, miesiac, dzien)


def swieta_rok(rok: int) -> frozenset:
    """
    Zwraca zbiór dat świąt ustawowo wolnych od pracy w danym roku (ustawa z 18.01.1951 r.).

    Uwzględnia:
    - Epifanię (6 I) od 2011 r. (ustawa z 24.09.2010 r., Dz.U. 2010 nr 217 poz. 1427)
    - Poniedziałek Wielkanocny, Zielone Świątki (Wiel.+49), Boże Ciało (Wiel.+60)
    """
    wiel = wielkanoc(rok)
    dni = {
        date(rok, 1, 1),   # Nowy Rok
        date(rok, 5, 1),   # Święto Pracy
        date(rok, 5, 3),   # Konstytucja 3 Maja
        date(rok, 8, 15),  # Wniebowzięcie NMP
        date(rok, 11, 1),  # Wszystkich Świętych
        date(rok, 11, 11), # Niepodległość
        date(rok, 12, 25), # Boże Narodzenie (1. dzień)
        date(rok, 12, 26), # Boże Narodzenie (2. dzień)
        wiel,                                  # Niedziela Wielkanocna
        wiel + timedelta(days=1),              # Poniedziałek Wielkanocny
        wiel + timedelta(days=49),             # Zielone Świątki
        wiel + timedelta(days=60),             # Boże Ciało
    }
    if rok >= 2011:
        dni.add(date(rok, 1, 6))               # Epifania (Trzech Króli)
    return frozenset(dni)


# ── Cache świąt (lata 2000–2099 obliczane leniwie) ───────────────────────────

_SWIETA_CACHE: dict = {r: swieta_rok(r) for r in range(2000, 2030)}


def is_free_day(d: date) -> bool:
    """Zwraca True gdy dzień jest sobotą, niedzielą lub świętem ustawowym."""
    if d.weekday() >= 5:
        return True
    swieta = _SWIETA_CACHE.get(d.year) or swieta_rok(d.year)
    return d in swieta


def next_workday(d: date) -> date:
    """Art. 115 KC: jeśli koniec terminu przypada na dzień wolny, przesuwa go na
    najbliższy następny dzień roboczy."""
    while is_free_day(d):
        d += relativedelta(days=1)
    return d


def add_days_115(start: date, days: int) -> date:
    """Dodaje *days* dni i stosuje art. 115 KC."""
    return next_workday(start + relativedelta(days=days))


def add_months_115(start: date, months: int) -> date:
    """Dodaje *months* miesięcy i stosuje art. 115 KC."""
    return next_workday(start + relativedelta(months=months))


def add_years_115(start: date, years: int) -> date:
    """Dodaje *years* lat i stosuje art. 115 KC."""
    return next_workday(start + relativedelta(years=years))


# ── Zasiedzenie ───────────────────────────────────────────────────────────────

GRANICA_1990 = date(1990, 10, 1)
"""Data wejścia w życie nowelizacji KC wydłużającej terminy zasiedzenia
(ustawa z 28.07.1990 r., Dz.U. 1990 nr 55 poz. 321)."""


def oblicz_zasiedzenie_nieruchomosci(
    start: date,
    dobra_wiara: bool,
) -> dict:
    """
    Oblicza termin zasiedzenia nieruchomości z uwzględnieniem przepisów
    intertemporalnych nowelizacji z 1.10.1990 r.

    Zwraca słownik:
        stary_lat       — liczba lat wg starych przepisów (10 lub 20)
        nowy_lat        — liczba lat wg nowych przepisów (20 lub 30)
        termin_stary    — data zasiedzenia wg starych przepisów (po art. 115 KC)
        termin_nowy     — data zasiedzenia wg nowych przepisów (po art. 115 KC)
        zastosowany     — 'stare' | 'nowe'
        termin          — data zastosowanego terminu
        wymagane_nowe   — True gdy stary termin upłynął po GRANICA_1990
                          (nowe przepisy mają zastosowanie)
    """
    stary_lat = 10 if dobra_wiara else 20
    nowy_lat  = 20 if dobra_wiara else 30

    termin_stary_raw = start + relativedelta(years=stary_lat)
    termin_stary     = next_workday(termin_stary_raw)

    termin_nowy_raw = start + relativedelta(years=nowy_lat)
    termin_nowy     = next_workday(termin_nowy_raw)

    if start >= GRANICA_1990:
        zastosowany  = 'nowe'
        termin       = termin_nowy
        wymagane_nowe = True
    elif termin_stary <= GRANICA_1990:
        zastosowany  = 'stare'
        termin       = termin_stary
        wymagane_nowe = False
    else:
        zastosowany  = 'nowe'
        termin       = termin_nowy
        wymagane_nowe = True

    return {
        'stary_lat':    stary_lat,
        'nowy_lat':     nowy_lat,
        'termin_stary': termin_stary,
        'termin_nowy':  termin_nowy,
        'zastosowany':  zastosowany,
        'termin':       termin,
        'wymagane_nowe': wymagane_nowe,
    }
