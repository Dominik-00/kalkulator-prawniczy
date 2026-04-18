# -*- coding: utf-8 -*-
"""
logika_przedawnienie.py — Czyste funkcje obliczeniowe dla przedawnienia roszczeń.

Wyodrębnione z tab_przedawnienie.TabPrzedawnienie._build() w celu umożliwienia
testowania jednostkowego bez uruchamiania GUI Tkinter.

Podstawa prawna:
    art. 118–125 KC
    ustawa z 13.04.2018 r. (Dz.U. 2018 poz. 1104) — nowelizacja KC
    art. 5 ust. 1–3 ustawy z 2018 r. — przepisy przejściowe
"""

from datetime import date
from dateutil.relativedelta import relativedelta


# ── Stałe ustawowe ────────────────────────────────────────────────────────────

DATA_NOWELIZACJI = date(2018, 7, 9)
"""Data wejścia w życie ustawy nowelizującej art. 118 KC (Dz.U. 2018 poz. 1104)."""

DATA_MIN_KONSUMENT = date(2020, 7, 9)
"""Minimalna data ochrony konsumenckiej — 2 lata od nowelizacji (art. 5 ust. 3 ustawy z 2018 r.)."""


# ── Pomocnicze ────────────────────────────────────────────────────────────────

def lata_str(n: int) -> str:
    """
    Zwraca polską formę słowną liczby lat (odmiana przez przypadki).

    Przykłady: 1 → '1 rok', 2 → '2 lata', 5 → '5 lat'.
    """
    if n == 1:
        return "1 rok"
    if n in (2, 3, 4):
        return f"{n} lata"
    return f"{n} lat"


# ── Upływ terminu (art. 118 KC) ───────────────────────────────────────────────

def uplyw(wymagalnosc: date, lata: int) -> tuple:
    """
    Oblicza upływ terminu przedawnienia zgodnie z art. 118 KC.

    Dla terminów ≥ 2 lata stosuje zasadę końca roku kalendarzowego
    (art. 118 zd. 2 KC: „koniec terminu przedawnienia przypada na ostatni
    dzień roku kalendarzowego").

    Zwraca:
        (surowa, ostateczna)
        surowa    — data arytmetyczna: wymagalnosc + lata
        ostateczna — data po korekcie art. 118 KC (31 XII roku surowej)
                     lub == surowa gdy lata < 2
    """
    if lata < 1:
        raise ValueError(f"Termin przedawnienia musi wynosić co najmniej 1 rok, podano: {lata}")
    surowa = wymagalnosc + relativedelta(years=lata)
    ostateczna = date(surowa.year, 12, 31) if lata >= 2 else surowa
    return surowa, ostateczna


# ── Przepisy przejściowe (art. 5 ustawy z 13.04.2018 r.) ─────────────────────

def oblicz_przejsciowe(
    wymagalnosc: date,
    lata_nowe: int,
    lata_stare: int,
    konsument: bool = False,
) -> tuple:
    """
    Oblicza termin przedawnienia z uwzględnieniem przepisów przejściowych
    ustawy z 13.04.2018 r. (Dz.U. 2018 poz. 1104).

    Algorytm (art. 5 ustawy z 2018 r.):
    1. Jeśli stary termin upłynął PRZED 9.07.2018 → roszczenie już przedawnione
       wg starych przepisów (art. 5 ust. 1 in fine).
    2. Jeśli nowy termin < stary termin (nowelizacja skróciła termin):
       - Nowy bieg: od 9.07.2018 + nowy termin (art. 5 ust. 2)
       - Stosuje się ten z terminów (stary vs nowy-od-2018), który upływa wcześniej.
    3. W pozostałych przypadkach (nowy ≥ stary): stosuje się nowy termin
       liczony od daty wymagalności (art. 5 ust. 1).
    4. Konsument: data ostateczna nie może być wcześniejsza niż 9.07.2020
       (art. 5 ust. 3).

    Parametry:
        wymagalnosc — data wymagalności roszczenia
        lata_nowe   — termin wg nowych przepisów (po nowelizacji 2018)
        lata_stare  — termin wg przepisów sprzed nowelizacji
        konsument   — True gdy uprawniony jest konsumentem (art. 5 ust. 3)

    Zwraca:
        (wynik: date, info: dict)

        info zawiera:
            tryb              — 'stare_pred_now' | 'przejsciowy'
            stare_uplyw       — data upływu wg starych przepisów
            nowe_uplyw        — data upływu wg nowych przepisów (None przy trybie stare_pred_now)
            nowe_od_now       — True gdy nowy termin liczony od 9.07.2018 (art. 5 ust. 2)
            wybrany           — 'stare' | 'nowe'
            konsument_korekta — True gdy zastosowano minimalną ochronę konsumencką
    """
    stare_uplyw = wymagalnosc + relativedelta(years=lata_stare)

    # Przypadek 1 — stary termin upłynął przed wejściem w życie nowelizacji
    if stare_uplyw < DATA_NOWELIZACJI:
        return stare_uplyw, {
            'tryb': 'stare_pred_now',
            'stare_uplyw': stare_uplyw,
            'nowe_uplyw': None,
            'nowe_od_now': False,
            'wybrany': 'stare',
            'konsument_korekta': False,
        }

    # Przypadek 2 — nowelizacja skróciła termin (lata_nowe < lata_stare)
    if lata_nowe < lata_stare:
        nowe_s = DATA_NOWELIZACJI + relativedelta(years=lata_nowe)
        nowe_o = date(nowe_s.year, 12, 31) if lata_nowe >= 2 else nowe_s
        nowe_od_now = True
        # Stosuje się ten termin, który upływa wcześniej
        if stare_uplyw <= nowe_o:
            wynik   = stare_uplyw
            wybrany = 'stare'
        else:
            wynik   = nowe_o
            wybrany = 'nowe'
    # Przypadek 3 — nowelizacja wydłużyła termin lub termin bez zmian
    else:
        nowe_s = wymagalnosc + relativedelta(years=lata_nowe)
        nowe_o = date(nowe_s.year, 12, 31) if lata_nowe >= 2 else nowe_s
        nowe_od_now = False
        wynik   = nowe_o
        wybrany = 'nowe'

    # Przypadek 4 — ochrona konsumencka (art. 5 ust. 3)
    konsument_korekta = False
    if konsument and wynik < DATA_MIN_KONSUMENT:
        wynik = DATA_MIN_KONSUMENT
        konsument_korekta = True

    return wynik, {
        'tryb': 'przejsciowy',
        'stare_uplyw': stare_uplyw,
        'nowe_uplyw': nowe_o,
        'nowe_od_now': nowe_od_now,
        'wybrany': wybrany,
        'konsument_korekta': konsument_korekta,
        'DATA_MIN_K': DATA_MIN_KONSUMENT,
    }
