# -*- coding: utf-8 -*-
"""
logika_raty.py — czyste funkcje obliczeniowe dla rozłożenia świadczenia na raty.
Wyodrębnione z tab_raty.py dla możliwości testowania bez GUI (Tkinter).
"""

import math
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta


def oblicz_harmonogram_rat(kwota: float, ilosc: int,
                           data_start: date | None = None,
                           czest: str = "miesiac") -> list:
    """
    Oblicza harmonogram równych rat dla kwoty świadczenia.

    Algorytm podziału:
      rata_base = floor(kwota / ilosc * 100) / 100   (zaokrąglenie w dół do groszy)
      pierwsza  = kwota - rata_base * (ilosc - 1)    (pierwsza rata absorbuje resztę)

    Parametry:
        kwota       -- całkowita kwota świadczenia (> 0)
        ilosc       -- liczba rat (>= 1)
        data_start  -- data pierwszej raty; None → termin = "—"
        czest       -- "miesiac" | "kwartal" | "rok" | "tydzien"

    Zwraca listę słowników:
        {'nr': int, 'kwota': float, 'wyrownujaca': bool, 'termin': str | date}
    """
    if kwota <= 0:
        raise ValueError("kwota musi być > 0")
    if ilosc < 1:
        raise ValueError("ilosc musi być >= 1")

    rata_base = math.floor(kwota / ilosc * 100) / 100
    suma_bez_pierwszej = round(rata_base * (ilosc - 1), 2)
    pierwsza = round(kwota - suma_bez_pierwszej, 2)

    def next_date(n: int):
        if data_start is None:
            return "—"
        if czest == "miesiac":
            return data_start + relativedelta(months=n)
        elif czest == "kwartal":
            return data_start + relativedelta(months=n * 3)
        elif czest == "rok":
            return data_start + relativedelta(years=n)
        else:  # tydzien
            return data_start + timedelta(weeks=n)

    raty = []
    for i in range(1, ilosc + 1):
        kwota_r = pierwsza if i == 1 else rata_base
        raty.append({
            'nr': i,
            'kwota': kwota_r,
            'wyrownujaca': i == 1 and abs(pierwsza - rata_base) > 0.005,
            'termin': next_date(i - 1),   # nr=1 → n=0 → data_start + 0
        })

    return raty


def oblicz_ilosc_rat_z_kwoty(kwota: float, kwota_j: float) -> int:
    """
    Oblicza minimalną liczbę rat potrzebną do spłaty kwoty ratami o zadanej wysokości.
    Odpowiada trybowi „Znana kwota raty" z tab_raty.py (math.ceil).

    Warunek (jak w UI): kwota_j > 0 i kwota_j < kwota.
    """
    if kwota_j <= 0 or kwota_j >= kwota:
        raise ValueError("kwota_j musi być > 0 i < kwota")
    return math.ceil(kwota / kwota_j)
