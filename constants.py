"""
constants.py — Kolory, stałe UI, funkcje pomocnicze i stawki sądowe.
"""

import math

# ── Kolory i styl ─────────────────────────────────────────────────────────────
BG       = "#1a1a2e"
PANEL    = "#ffffff"
CREAM    = "#f5f0e8"
GOLD     = "#c9a84c"
GOLD_LT  = "#e8c97a"
TEXT     = "#1a1a2e"
MUTED    = "#6b6b6b"
RED      = "#8b2c2c"
GREEN    = "#2c6e49"
BORDER   = "#c8bfa8"
HEADER_H = 58

# ── Helpers ───────────────────────────────────────────────────────────────────
def fmt(n: float) -> str:
    """Formatuje liczbę jako polską kwotę PLN."""
    return f"{n:,.2f} PLN".replace(",", " ").replace(".", ",")

def safe_float(widget, default=0.0) -> float:
    try:
        return float(str(widget.get()).replace(",", ".").replace(" ", ""))
    except Exception:
        return default

def safe_int(widget, default=0) -> int:
    try:
        return int(str(widget.get()).strip())
    except Exception:
        return default

# ── Stawki opłat sądowych (UKSCP art. 13) ────────────────────────────────────
def oplata_sadowa(wps: float, rodzaj: str, instancja: str) -> float:
    if rodzaj == "pracownicza":
        return 0.0
    if wps <= 500:       o = 30
    elif wps <= 1500:    o = 100
    elif wps <= 4000:    o = 200
    elif wps <= 7500:    o = 400
    elif wps <= 10000:   o = 500
    elif wps <= 15000:   o = 750
    elif wps <= 20000:   o = 1000
    else:                o = min(wps * 0.05, 200000)
    if rodzaj == "upominawcze":
        o = o / 4
    return math.ceil(o)

# §2 rozp. MS z 22.10.2015 – minimalne wynagrodzenie pełnomocnika
def wynagrodzenie_pelnomocnika(wps: float) -> float:
    if wps <= 500:        return 90
    if wps <= 1500:       return 270
    if wps <= 5000:       return 900
    if wps <= 10000:      return 1800
    if wps <= 50000:      return 3600
    if wps <= 200000:     return 5400
    if wps <= 2000000:    return 10800
    return 15000
