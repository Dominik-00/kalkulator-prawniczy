# -*- coding: utf-8 -*-
"""
logika_oplata_roczna.py — czyste funkcje obliczeniowe dla aktualizacji opłaty
rocznej z tytułu użytkowania wieczystego (art. 77 UGN).
Wyodrębnione z tab_oplata_roczna.py dla możliwości testowania bez GUI (Tkinter).
"""

from datetime import date
from dateutil.relativedelta import relativedelta


def oblicz_aktualizacje_oplaty(
        oplata_dotychczasowa: float,
        wartosc_nowa: float,
        stawka_pct: float,
        data_akt: date | None = None,
        data_ostatniej: date | None = None,
        wartosc_stara: float | None = None,
) -> dict:
    """
    Oblicza zaktualizowaną opłatę roczną z tytułu użytkowania wieczystego.

    Podstawa prawna:
        Art. 77 ust. 1  UGN: aktualizacja nie częściej niż raz na 3 lata
        Art. 77 ust. 2a UGN: wzrost stopniowany — 1/3 różnicy w roku 1, 2/3 w roku 2,
                              pełna nowa opłata od roku 3
        Art. 77 ust. 2b UGN: spadek opłaty stosuje się od razu w pełnej wysokości
        Art. 77 ust. 3  UGN: nowa opłata = wartość nieruchomości × stawka procentowa

    Parametry:
        oplata_dotychczasowa -- aktualna opłata roczna (PLN, >= 0)
        wartosc_nowa         -- nowa wartość nieruchomości wg operatu (PLN, > 0)
        stawka_pct           -- stawka procentowa opłaty (np. 1.0 dla 1%, zakres (0, 100])
        data_akt             -- data aktualizacji (None → nie wylicza roku w harmonogramie)
        data_ostatniej       -- data poprzedniej aktualizacji (None → brak weryfikacji 3 lat)
        wartosc_stara        -- dotychczasowa wartość nieruchomości (None → brak weryfikacji)

    Zwraca słownik:
        oplata_nowa          -- float, nowa opłata roczna = wartosc_nowa × stawka
        roznica              -- float, różnica (dodatnia = wzrost, ujemna/zero = spadek)
        spadek               -- bool, True gdy oplata_nowa <= oplata_dotychczasowa
        prog1                -- float, opłata w roku 1 po aktualizacji (art. 77 ust. 2a)
        prog2                -- float, opłata w roku 2 po aktualizacji (art. 77 ust. 2a)
        weryfikacja_3lat     -- None | (lata: int, miesiace: int, ok: bool)
        oplata_z_wartosci_starej -- None | float
    """
    if oplata_dotychczasowa < 0:
        raise ValueError("oplata_dotychczasowa musi być >= 0")
    if wartosc_nowa <= 0:
        raise ValueError("wartosc_nowa musi być > 0")
    if not (0 < stawka_pct <= 100):
        raise ValueError("stawka_pct musi być w zakresie (0, 100]")

    stawka_ulamek = stawka_pct / 100.0
    oplata_nowa = wartosc_nowa * stawka_ulamek

    oplata_z_wartosci_starej = None
    if wartosc_stara is not None:
        oplata_z_wartosci_starej = wartosc_stara * stawka_ulamek

    roznica = oplata_nowa - oplata_dotychczasowa
    # UWAGA: equality (==) traktowane jako "spadek" — identycznie jak w tab_oplata_roczna.py
    # Efekt: przy równości prog1=prog2=oplata_nowa, nie jest błędem logicznym, ale komunikat
    # "nowa opłata niższa" jest wtedy mylący. Zachowane celowo dla zgodności z UI.
    spadek = oplata_nowa <= oplata_dotychczasowa

    if not spadek:
        prog1 = oplata_dotychczasowa + roznica * (1 / 3)
        prog2 = oplata_dotychczasowa + roznica * (2 / 3)
    else:
        prog1 = oplata_nowa
        prog2 = oplata_nowa

    weryfikacja_3lat = None
    if data_ostatniej is not None and data_akt is not None:
        delta = relativedelta(data_akt, data_ostatniej)
        lata = delta.years
        miesiace_extra = delta.months
        weryfikacja_3lat = (lata, miesiace_extra, lata >= 3)

    return {
        'oplata_nowa': oplata_nowa,
        'roznica': roznica,
        'spadek': spadek,
        'prog1': prog1,
        'prog2': prog2,
        'weryfikacja_3lat': weryfikacja_3lat,
        'oplata_z_wartosci_starej': oplata_z_wartosci_starej,
    }
