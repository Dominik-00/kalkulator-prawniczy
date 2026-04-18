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
    n = n + 0.0  # normalizuje -0.0 → 0.0
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
_OPLATA_PROGI = (
    (500, 30), (1500, 100), (4000, 200), (7500, 400),
    (10000, 500), (15000, 750), (20000, 1000),
)

def oplata_sadowa(wps: float, rodzaj: str, instancja: str) -> float:
    rodzaj = (rodzaj or "").lower()
    if rodzaj == "pracownicza":
        return 0.0

    o = next((k for p, k in _OPLATA_PROGI if wps <= p), min(wps * 0.05, 100000))
    if rodzaj in {"nakazowe", "epu", "upominawcze"}:
        o /= 4
    return math.ceil(o)

# §2 rozp. MS z 22.10.2015 – minimalne wynagrodzenie pełnomocnika
_STAWKI_PELNOM = (
    (500, 90), (1500, 270), (5000, 900), (10000, 1800),
    (50000, 3600), (200000, 5400), (2000000, 10800), (5000000, 15000),
)

def wynagrodzenie_pelnomocnika(wps: float) -> float:
    return next((k for p, k in _STAWKI_PELNOM if wps <= p), 25000)
