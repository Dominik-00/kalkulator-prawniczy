"""
inheritance.py — Moduł spadkowy: model danych, silnik dziedziczenia (KC art. 931–940),
                 generator PDF (reportlab), widok drzewa genealogicznego, dialog osoby.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, date
from fractions import Fraction
import json
import uuid

from constants import BG, PANEL, CREAM, GOLD, GOLD_LT, TEXT, MUTED, RED, BORDER

# ══════════════════════════════════════════════════════════════════════════════
#  MODUŁ SPADKOWY — MODEL DANYCH, SILNIK, PDF, DRZEWO, DIALOG
# ══════════════════════════════════════════════════════════════════════════════

import os
import sys

# ── Pomocnicza funkcja domyślnej nazwy pliku ──────────────────────────────────
def domyslna_nazwa_pliku(baza: "BazaDanych") -> str:
    """
    Zwraca domyślną ścieżkę do zapisu pliku w katalogu programu.

    Nazwa: DDMMYYYY_imię_zmarłego  (najstarsza osoba ze śmiercią wpisaną)
           DDMMYYYY_drzewo         (brak zmarłych lub brak daty urodzenia)

    Katalog: folder, w którym leży plik wykonywalny / skrypt.
    """
    dzis = datetime.now().strftime("%d%m%Y")

    # Szukaj najstarszej osoby z datą śmierci
    kandydaci = []
    for o in baza.osoby.values():
        if not o.data_smierci:
            continue
        if o.data_urodzenia:
            try:
                ur = _sp_parse_date(o.data_urodzenia)
                kandydaci.append((ur, o))
            except Exception:
                pass
        else:
            # ma datę śmierci, ale brak daty urodzenia — fallback do tej osoby
            kandydaci.append((None, o))

    imie_czesc = "drzewo"
    if kandydaci:
        # Najstarsza = najwcześniejsza data urodzenia; None traktuj jako bardzo późną
        kandydaci_z_datami = [(ur, o) for ur, o in kandydaci if ur is not None]
        if kandydaci_z_datami:
            _, najstarsza = min(kandydaci_z_datami, key=lambda x: x[0])
        else:
            # Wszyscy kandydaci bez daty urodzenia — bierz pierwszego
            _, najstarsza = kandydaci[0]
        # Sanityzuj imię — usuń znaki niedozwolone w nazwach plików
        imie_raw = najstarsza.imie.strip()
        imie_czesc = "".join(c for c in imie_raw if c.isalnum() or c in "_ -") or "drzewo"

    nazwa = f"{dzis}_{imie_czesc}.json"

    # Katalog programu (obsługuje zarówno .py jak i .exe z PyInstaller)
    if getattr(sys, "frozen", False):
        katalog = os.path.dirname(sys.executable)
    else:
        katalog = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(katalog, nazwa)


# ── Pomocnicze funkcje dat (moduł spadkowy) ───────────────────────────────────
def _sp_parse_date(s: str) -> date:
    s = s.strip()
    if len(s) == 8 and s.isdigit():
        s = f"{s[0:2]}-{s[2:4]}-{s[4:8]}"
    for fmt_str in ("%d-%m-%Y", "%Y-%m-%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(s, fmt_str).date()
        except ValueError:
            pass
    raise ValueError(f"Nieznany format daty: {s!r}")

def _sp_fmt_date(s: str) -> str:
    if not s:
        return ""
    try:
        return _sp_parse_date(s).strftime("%d-%m-%Y")
    except Exception:
        return s

# ── Model danych ─────────────────────────────────────────────────────────────
class Osoba:
    def __init__(self, imie: str, nazwisko: str, data_urodzenia: str = "",
                 data_smierci: str = "", plec: str = "M", id: str = None,
                 rodzic_ids: list = None, malzonek_id: str = None,
                 wydziedziczona: bool = False,       # art. 1008 KC — tylko pozbawia zachowku
                 odrzucila_spadek: bool = False,     # art. 1020 KC — zstępni wchodzą w miejsce
                 zrzekla_sie: bool = False,          # art. 1048 KC — wyłączona z dziedziczenia
                 zrzeczenie_obejmuje_zstepnych: bool = True,  # art. 1049 §1 KC — domyślnie TAK
                 notatki: str = "",
                 akt_urodzenia: bool = True,
                 akt_malzenstwa: bool = True,
                 akt_smierci: bool = True):
        self.id = id or str(uuid.uuid4())[:8]
        self.imie = imie
        self.nazwisko = nazwisko
        self.data_urodzenia = data_urodzenia
        self.data_smierci = data_smierci
        self.plec = plec
        self.rodzic_ids = rodzic_ids or []
        self.malzonek_id = malzonek_id
        self.wydziedziczona = wydziedziczona
        self.odrzucila_spadek = odrzucila_spadek
        self.notatki = notatki
        self.akt_urodzenia = akt_urodzenia
        self.akt_malzenstwa = akt_malzenstwa
        self.akt_smierci = akt_smierci
        self.zrzekla_sie = zrzekla_sie
        self.zrzeczenie_obejmuje_zstepnych = zrzeczenie_obejmuje_zstepnych

    @property
    def pelne_imie(self):
        return f"{self.imie} {self.nazwisko}"

    @property
    def zyje(self):
        return not bool(self.data_smierci)

    @property
    def wiek(self):
        if not self.data_urodzenia:
            return None
        try:
            ur = _sp_parse_date(self.data_urodzenia)
            koniec = _sp_parse_date(self.data_smierci) if self.data_smierci else date.today()
            return (koniec - ur).days // 365
        except Exception:
            return None

    def to_dict(self):
        return {
            "id": self.id, "imie": self.imie, "nazwisko": self.nazwisko,
            "data_urodzenia": self.data_urodzenia, "data_smierci": self.data_smierci,
            "plec": self.plec, "rodzic_ids": self.rodzic_ids,
            "malzonek_id": self.malzonek_id, "wydziedziczona": self.wydziedziczona,
            "odrzucila_spadek": self.odrzucila_spadek, "notatki": self.notatki,
            "akt_urodzenia": self.akt_urodzenia,
            "akt_malzenstwa": self.akt_malzenstwa,
            "akt_smierci": self.akt_smierci,
            "zrzekla_sie": self.zrzekla_sie,
            "zrzeczenie_obejmuje_zstepnych": self.zrzeczenie_obejmuje_zstepnych,
        }

    @staticmethod
    def from_dict(d):
        d = dict(d)
        d.setdefault("akt_urodzenia", True)
        d.setdefault("akt_malzenstwa", True)
        d.setdefault("akt_smierci", True)
        d.setdefault("zrzekla_sie", False)
        d.setdefault("zrzeczenie_obejmuje_zstepnych", True)
        # MIGRACJA DANYCH: stare pliki mogły używać wydziedziczona=True
        # jako zrzeczenie — zostaw jak jest, użytkownik powinien ręcznie
        # zmigrować dane (lub można tu dodać logikę migracji)
        return Osoba(**d)


class BazaDanych:
    def __init__(self):
        self.osoby: dict = {}
        self.plik = ""

    def dodaj(self, o: Osoba):
        self.osoby[o.id] = o

    def usun(self, id: str):
        if id in self.osoby:
            del self.osoby[id]
            for o in self.osoby.values():
                if id in o.rodzic_ids:
                    o.rodzic_ids.remove(id)
                if o.malzonek_id == id:
                    o.malzonek_id = None

    def usun_wiele(self, ids: list):
        ids_set = set(ids)
        for id in ids:
            if id in self.osoby:
                del self.osoby[id]
        for o in self.osoby.values():
            o.rodzic_ids = [r for r in o.rodzic_ids if r not in ids_set]
            if o.malzonek_id in ids_set:
                o.malzonek_id = None

    def zapisz(self, plik: str):
        self.plik = plik
        with open(plik, "w", encoding="utf-8") as f:
            json.dump([o.to_dict() for o in self.osoby.values()], f,
                      ensure_ascii=False, indent=2)

    def wczytaj(self, plik: str):
        self.plik = plik
        with open(plik, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.osoby = {d["id"]: Osoba.from_dict(d) for d in data}

    def dzieci(self, id: str) -> list:
        return [o for o in self.osoby.values() if id in o.rodzic_ids]

    def rodzice(self, id: str) -> list:
        o = self.osoby.get(id)
        if not o:
            return []
        return [self.osoby[r] for r in o.rodzic_ids if r in self.osoby]

    def malzonek(self, id: str):
        o = self.osoby.get(id)
        if o and o.malzonek_id:
            return self.osoby.get(o.malzonek_id)
        return None

    def rodzenstwo(self, id: str) -> list:
        o = self.osoby.get(id)
        if not o or not o.rodzic_ids:
            return []
        wynik = set()
        for pid in o.rodzic_ids:
            for dziecko in self.dzieci(pid):
                if dziecko.id != id:
                    wynik.add(dziecko.id)
        return [self.osoby[i] for i in wynik]

    def dziadkowie(self, id: str) -> list:
        wynik = []
        for rodzic in self.rodzice(id):
            wynik.extend(self.rodzice(rodzic.id))
        return wynik

    def wujkowie_ciotki(self, id: str) -> list:
        wynik = []
        for rodzic in self.rodzice(id):
            wynik.extend(self.rodzenstwo(rodzic.id))
        return wynik


# ── Silnik dziedziczenia (KC art. 931–940) ────────────────────────────────────
class SilnikDziedziczenia:
    def __init__(self, baza: BazaDanych, spadkodawca_id: str):
        self.baza = baza
        self.sp_id = spadkodawca_id
        self.sp = baza.osoby.get(spadkodawca_id)

    def _efektywny(self, osoba_id: str) -> bool:
            """
            Zwraca True jeśli osoba dziedziczy ustawowo.

            WYŁĄCZENIA z dziedziczenia ustawowego:
            - zrzeczenie się dziedziczenia (art. 1048 KC)
            - odrzucenie spadku (art. 1020 KC)

            NIE wyłącza: wydziedziczenie z art. 1008 KC — to jedynie
            pozbawia prawa do zachowku, nie wpływa na dziedziczenie ustawowe.
            """
            o = self.baza.osoby.get(osoba_id)
            if not o:
                return False
            if o.zrzekla_sie:        # art. 1048 KC — wyłączona z dziedziczenia
                return False
            if o.odrzucila_spadek:   # art. 1020 KC — traktowana jak nieżyjąca
                return False
            # o.wydziedziczona (art. 1008 KC) NIE wpływa na dziedziczenie ustawowe
            return True

    def oblicz(self) -> dict:
        if not self.sp:
            return {}
        return self._group_I()

    def _group_I(self) -> dict:
        malzonek = self.baza.malzonek(self.sp_id)
        malzonek_ok = malzonek and self._efektywny(malzonek.id) and malzonek.zyje
        dzieci = self.baza.dzieci(self.sp_id)
        grupy_dzieci = []
        for d in dzieci:
            if d.zyje and self._efektywny(d.id):
                grupy_dzieci.append(([d.id], True))
            elif not d.zyje or not self._efektywny(d.id):
                wnuki = self._zstepni_efektywni(d.id)
                if wnuki:
                    grupy_dzieci.append((wnuki, False))

        n_grup = len(grupy_dzieci)

        if n_grup == 0:
            return self._group_II()

        udzialy = {}
        if malzonek_ok:
            czesc_dzieci = Fraction(3, 4) if n_grup >= 2 else Fraction(1, 2)
            udzialy[malzonek.id] = Fraction(1) - czesc_dzieci
        else:
            czesc_dzieci = Fraction(1)

        czesc_na_grupe = czesc_dzieci / n_grup
        for (ids, _) in grupy_dzieci:
            czesc_na_osobe = czesc_na_grupe / len(ids)
            for oid in ids:
                udzialy[oid] = udzialy.get(oid, Fraction(0)) + czesc_na_osobe
        return udzialy

    def _zstepni_efektywni(self, id: str) -> list:
            """
            Szuka efektywnych zstępnych osoby która nie może/nie chce dziedziczyć.

            Rozróżnienie:
            - odrzucenie spadku (art. 1020): zstępni WCHODZĄ w miejsce odrzucającego
            - zrzeczenie się (art. 1048 + 1049 §1): zstępni domyślnie TEŻ wyłączeni,
              chyba że umowa stanowi inaczej (zrzeczenie_obejmuje_zstepnych=False)
            """
            o = self.baza.osoby.get(id)
            wynik = []
            for d in self.baza.dzieci(id):
                # Jeśli rodzic zrzekł się i zrzeczenie obejmuje zstępnych —
                # zstępni są wyłączeni (art. 1049 §1 KC), nie szukamy dalej
                if o and o.zrzekla_sie and o.zrzeczenie_obejmuje_zstepnych:
                    continue  # pomiń całą gałąź

                if d.zyje and self._efektywny(d.id):
                    wynik.append(d.id)
                else:
                    wynik.extend(self._zstepni_efektywni(d.id))
            return wynik

    def _group_II(self) -> dict:
        malzonek = self.baza.malzonek(self.sp_id)
        malzonek_ok = malzonek and self._efektywny(malzonek.id) and malzonek.zyje
        wszyscy_rodzice = self.baza.rodzice(self.sp_id)
        if not malzonek_ok and not wszyscy_rodzice:
            return self._group_III()

        udzialy = {}

        if not wszyscy_rodzice:
            if malzonek_ok:
                udzialy[malzonek.id] = Fraction(1)
                return udzialy
            return self._group_III()

        if malzonek_ok:
            udzialy[malzonek.id] = Fraction(1, 2)
            pula_rodziny = Fraction(1, 2)
        else:
            pula_rodziny = Fraction(1)

        n_miejsc = max(len(wszyscy_rodzice), 1)
        czesc_na_miejsce = pula_rodziny / n_miejsc

        for r in wszyscy_rodzice:
            if r.zyje and self._efektywny(r.id):
                udzialy[r.id] = udzialy.get(r.id, Fraction(0)) + czesc_na_miejsce
            else:
                rodz = [s for s in self.baza.rodzenstwo(self.sp_id) if self._efektywny(s.id)]
                rodz_grupe = []
                for s in rodz:
                    if s.zyje:
                        rodz_grupe.append([s.id])
                    else:
                        z = self._zstepni_efektywni(s.id)
                        if z:
                            rodz_grupe.append(z)
                if rodz_grupe:
                    cna = czesc_na_miejsce / len(rodz_grupe)
                    for gr in rodz_grupe:
                        cna2 = cna / len(gr)
                        for sid in gr:
                            udzialy[sid] = udzialy.get(sid, Fraction(0)) + cna2
                else:
                    zyj_rodzice = [x for x in wszyscy_rodzice if x.zyje and self._efektywny(x.id)]
                    if zyj_rodzice:
                        cna = czesc_na_miejsce / len(zyj_rodzice)
                        for x in zyj_rodzice:
                            udzialy[x.id] = udzialy.get(x.id, Fraction(0)) + cna
                    elif malzonek_ok:
                        udzialy[malzonek.id] = udzialy.get(malzonek.id, Fraction(0)) + czesc_na_miejsce

        if not udzialy and malzonek_ok:
            udzialy[malzonek.id] = Fraction(1)
        return udzialy if udzialy else self._group_III()

    def _group_III(self) -> dict:
        dziadkowie = self.baza.dziadkowie(self.sp_id)
        efekt = [d for d in dziadkowie if self._efektywny(d.id) and d.zyje]
        if not efekt:
            wuj = [w for w in self.baza.wujkowie_ciotki(self.sp_id)
                   if self._efektywny(w.id) and w.zyje]
            if wuj:
                c = Fraction(1, len(wuj))
                return {w.id: c for w in wuj}
            return self._group_IV()
        c = Fraction(1, len(efekt))
        return {d.id: c for d in efekt}

    def _group_IV(self) -> dict:
        malzonek = self.baza.malzonek(self.sp_id)
        if malzonek:
            pasierbowie = [d for d in self.baza.dzieci(malzonek.id)
                           if self.sp_id not in d.rodzic_ids
                           and self._efektywny(d.id) and d.zyje]
            if pasierbowie:
                c = Fraction(1, len(pasierbowie))
                return {p.id: c for p in pasierbowie}
        return {"__gmina__": Fraction(1)}

    def opis_udzialu(self, udzialy: dict) -> list:
        wynik = []
        for oid, u in udzialy.items():
            if oid == "__gmina__":
                wynik.append(("Gmina / Skarb Państwa", str(u), f"{float(u)*100:.2f}%"))
            else:
                o = self.baza.osoby.get(oid)
                if o:
                    wynik.append((o.pelne_imie, str(u), f"{float(u)*100:.2f}%"))
        return wynik


# ── Generator PDF (reportlab, instalowany opcjonalnie) ────────────────────────
def _generuj_pdf_spadki(baza: BazaDanych, spadkodawca_id: str, plik: str):
    """Generuje raport PDF. Wymaga reportlab."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.lib import colors
        from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                        Table, TableStyle, HRFlowable)
        from reportlab.lib.enums import TA_CENTER
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
    except ImportError:
        raise RuntimeError("Biblioteka reportlab nie jest zainstalowana.\n"
                           "Zainstaluj ją: pip install reportlab")

    PDF_REG, PDF_BOLD = "Helvetica", "Helvetica-Bold"
    kandydaci = [
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
        ("/System/Library/Fonts/Supplemental/Arial.ttf", "/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
    ]
    for reg_path, bold_path in kandydaci:
        if os.path.exists(reg_path):
            try:
                pdfmetrics.registerFont(TTFont("SpadkReg", reg_path))
                pdfmetrics.registerFont(TTFont("SpadkBold", bold_path if os.path.exists(bold_path) else reg_path))
                PDF_REG, PDF_BOLD = "SpadkReg", "SpadkBold"
                break
            except Exception:
                pass

    sp = baza.osoby.get(spadkodawca_id)
    if not sp:
        return
    silnik = SilnikDziedziczenia(baza, spadkodawca_id)
    udzialy = silnik.oblicz()
    opis = silnik.opis_udzialu(udzialy)

    doc = SimpleDocTemplate(plik, pagesize=A4,
                            rightMargin=2*cm, leftMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    elements = []

    tytul_s = ParagraphStyle("t", fontSize=18, alignment=TA_CENTER, fontName=PDF_BOLD, spaceAfter=6)
    podtytul_s = ParagraphStyle("pt", fontSize=11, alignment=TA_CENTER, fontName=PDF_REG,
                                spaceAfter=20, textColor=colors.grey)
    sekcja_s = ParagraphStyle("s", fontSize=12, fontName=PDF_BOLD, spaceAfter=8, spaceBefore=14,
                               textColor=colors.HexColor("#1a1a2e"))
    normal_s = ParagraphStyle("n", fontSize=10, fontName=PDF_REG, spaceAfter=4, leading=15)
    alert_s = ParagraphStyle("a", fontSize=10, fontName=PDF_REG,
                              textColor=colors.HexColor("#8b0000"), spaceAfter=3, leading=14, leftIndent=8)

    elements.append(Paragraph("RAPORT DZIEDZICZENIA USTAWOWEGO", tytul_s))
    elements.append(Paragraph("wg polskiego Kodeksu cywilnego (art. 931–940 KC)", podtytul_s))
    elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#4a90d9")))
    elements.append(Spacer(1, 12))

    elements.append(Paragraph("DANE SPADKODAWCY", sekcja_s))
    info = [
        ["Imię i nazwisko:", sp.pelne_imie],
        ["Data urodzenia:", _sp_fmt_date(sp.data_urodzenia) or "—"],
        ["Data śmierci:", _sp_fmt_date(sp.data_smierci) or "—"],
        ["Wiek:", f"{sp.wiek} lat" if sp.wiek else "—"],
    ]
    t = Table(info, colWidths=[5*cm, 11*cm])
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), PDF_BOLD), ("FONTNAME", (1, 0), (1, -1), PDF_REG),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.HexColor("#f0f4ff"), colors.white]),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
        ("LEFTPADDING", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 12))

    elements.append(Paragraph("UDZIAŁY W SPADKU", sekcja_s))
    if opis:
        udzialy_data = [["Spadkobierca", "Udział (ułamek)", "Udział (%)"]]
        for imie, ulamek, procent in opis:
            udzialy_data.append([imie, ulamek, procent])
        tu = Table(udzialy_data, colWidths=[8*cm, 5*cm, 3*cm])
        tu.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4a90d9")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), PDF_BOLD), ("FONTNAME", (0, 1), (-1, -1), PDF_REG),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#e8f4fd"), colors.white]),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("LEFTPADDING", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        elements.append(tu)

    elements.append(Spacer(1, 12))
    elements.append(Paragraph("STAN DOKUMENTÓW", sekcja_s))

    osoby_w_raporcie = set([spadkodawca_id])
    for oid in udzialy:
        if oid != "__gmina__" and oid in baza.osoby:
            osoby_w_raporcie.add(oid)
    for oid in list(osoby_w_raporcie):
        for o in baza.rodzice(oid):
            if not o.zyje:
                osoby_w_raporcie.add(o.id)

    osoby_do_docs = sorted([baza.osoby[o] for o in osoby_w_raporcie if o in baza.osoby],
                           key=lambda x: x.nazwisko)
    doc_rows = [["Osoba", "Akt urodzenia", "Akt małżeństwa", "Akt zgonu"]]
    braki = []
    for o in osoby_do_docs:
        malz_ist = bool(o.malzonek_id)
        zgon_ist = not o.zyje
        ur_sym = "TAK" if o.akt_urodzenia else "BRAK"
        ml_sym = "TAK" if o.akt_malzenstwa else ("BRAK" if malz_ist else "—")
        zm_sym = ("TAK" if o.akt_smierci else "BRAK") if zgon_ist else "—"
        doc_rows.append([o.pelne_imie, ur_sym, ml_sym, zm_sym])
        # Akt urodzenia i akt małżeństwa są zamienne — wystarczy jeden z nich
        ma_dokument_tozsamosci = o.akt_urodzenia or o.akt_malzenstwa
        if not ma_dokument_tozsamosci:
            braki.append((o.pelne_imie, "akt urodzenia lub akt małżeństwa",
                          "wymagany do ustalenia tożsamości — brak obu dokumentów"))
        # Akt zgonu wymagany gdy osoba nie żyje
        if zgon_ist and not o.akt_smierci:
            braki.append((o.pelne_imie, "akt zgonu",
                          "wymagany do stwierdzenia śmierci"))

    td = Table(doc_rows, colWidths=[7*cm, 3*cm, 3*cm, 3*cm])
    td.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2a5080")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), PDF_BOLD), ("FONTNAME", (0, 1), (-1, -1), PDF_REG),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"), ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f8f9fa"), colors.white]),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
        ("LEFTPADDING", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    elements.append(td)
    elements.append(Spacer(1, 8))

    if braki:
        elements.append(Paragraph("BRAKUJĄCE DOKUMENTY:", sekcja_s))
        for imie_b, typ_b, uzas_b in braki:
            elements.append(Paragraph(f"⚠  {imie_b} — brak: {typ_b}  ({uzas_b})", alert_s))

    note_s = ParagraphStyle("note", fontSize=8, fontName=PDF_REG, textColor=colors.grey,
                             spaceAfter=4, leading=12)
    elements.append(Spacer(1, 20))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.lightgrey))
    elements.append(Spacer(1, 6))
    elements.append(Paragraph(f"Data wygenerowania: {datetime.now().strftime('%d-%m-%Y %H:%M')}", note_s))
    elements.append(Paragraph("Raport wygenerowany przez Kalkulator Prawniczy", note_s))
    doc.build(elements)


# ── Widok drzewa genealogicznego ──────────────────────────────────────────────
class DrzewoGenealogiczne(tk.Frame):
    BOX_W = 160
    BOX_H = 66
    H_GAP = 40   # większy odstęp poziomy między kafelkami
    V_GAP = 110  # większy odstęp pionowy między pokoleniami

    def __init__(self, master, baza: BazaDanych, **kwargs):
        super().__init__(master, **kwargs)
        self.baza = baza
        self.canvas = tk.Canvas(self, bg="#e8f0fb", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<ButtonPress-1>", self._start_pan)
        self.canvas.bind("<B1-Motion>", self._pan)
        self.canvas.bind("<MouseWheel>", self._zoom)
        self.canvas.bind("<Button-4>", self._zoom)
        self.canvas.bind("<Button-5>", self._zoom)
        self.canvas.bind("<Double-Button-1>", self._dwuklik)
        self.canvas.bind("<ButtonPress-3>", self._kontekst)
        self._pan_start = None
        self._scale = 1.0
        self._offset = [50, 50]
        self.positions = {}
        self.on_select = None
        self.on_edit = None
        self.on_delete = None

    def _get_osoba_at(self, x, y):
        item = self.canvas.find_closest(x, y)
        if not item:
            return None
        for t in self.canvas.gettags(item[0]):
            if t.startswith("os_"):
                return t[3:]
        return None

    def _start_pan(self, e):
        self._pan_start = (e.x, e.y)
        oid = self._get_osoba_at(e.x, e.y)
        if oid and self.on_select:
            self.on_select(oid)

    def _pan(self, e):
        if self._pan_start:
            self._offset[0] += e.x - self._pan_start[0]
            self._offset[1] += e.y - self._pan_start[1]
            self._pan_start = (e.x, e.y)
            self.odrysuj()

    def _zoom(self, e):
        f = 1.1 if (getattr(e, "delta", 0) > 0 or e.num == 4) else 0.9
        self._scale = max(0.3, min(3.0, self._scale * f))
        self.odrysuj()

    def _dwuklik(self, e):
        oid = self._get_osoba_at(e.x, e.y)
        if oid and self.on_edit:
            self.on_edit(oid)

    def _kontekst(self, e):
        oid = self._get_osoba_at(e.x, e.y)
        menu = tk.Menu(self.canvas, tearoff=0)
        if oid and oid in self.baza.osoby:
            o = self.baza.osoby[oid]
            menu.add_command(label=f"👤 {o.pelne_imie}", state="disabled",
                             font=("Segoe UI", 9, "bold"))
            menu.add_separator()
            if self.on_edit:
                menu.add_command(label="✏ Edytuj", command=lambda: self.on_edit(oid))
            if self.on_delete:
                menu.add_command(label="🗑 Usuń", command=lambda: self.on_delete(oid),
                                 foreground="#c0392b")
        try:
            menu.tk_popup(e.x_root, e.y_root)
        finally:
            menu.grab_release()

    def centruj_na(self, osoba_id: str):
        self._oblicz_pozycje()
        if osoba_id not in self.positions:
            return
        px, py = self.positions[osoba_id]
        bw = self.BOX_W * self._scale
        bh = self.BOX_H * self._scale
        cw = self.canvas.winfo_width() or 600
        ch = self.canvas.winfo_height() or 400
        self._offset[0] += cw / 2 - (px + bw / 2)
        self._offset[1] += ch / 2 - (py + bh / 2)
        self.odrysuj()

    def odrysuj(self):
        self.canvas.delete("all")
        if not self.baza.osoby:
            return
        self._oblicz_pozycje()
        self._rysuj_polaczenia()
        self._rysuj_osoby()

    def _oblicz_pozycje(self):
        osoby = self.baza.osoby
        if not osoby:
            self.positions = {}
            return

        # ── Krok 1: oblicz głębokość (pokolenie) każdej osoby ─────────────────
        glebokosc = {}

        def _gleb(oid, visited):
            if oid in glebokosc:
                return glebokosc[oid]
            if oid in visited:
                return 0
            visited.add(oid)
            o = osoby.get(oid)
            rodzice_w = [p for p in (o.rodzic_ids if o else []) if p in osoby]
            glebokosc[oid] = (max(_gleb(p, visited) for p in rodzice_w) + 1) if rodzice_w else 0
            return glebokosc[oid]

        for oid in osoby:
            _gleb(oid, set())

        # Wyrównaj małżonków do tego samego pokolenia (max z obojga)
        zmiana = True
        while zmiana:
            zmiana = False
            for o in osoby.values():
                if o.malzonek_id and o.malzonek_id in osoby:
                    g1, g2 = glebokosc.get(o.id, 0), glebokosc.get(o.malzonek_id, 0)
                    t = max(g1, g2)
                    if g1 != t:
                        glebokosc[o.id] = t
                        zmiana = True
                    if g2 != t:
                        glebokosc[o.malzonek_id] = t
                        zmiana = True

        # ── Krok 2: posortuj osoby w każdym pokoleniu ─────────────────────────
        # Zasada: małżonkowie zawsze obok siebie, rodzeństwo grupowane razem.
        #
        # Algorytm:
        #   a) Wyodrębnij unikalne pary małżeńskie → jeden "slot" na parę.
        #   b) Singletony (bez małżonka w tym pokoleniu) → osobny slot.
        #   c) Kolejność slotów wynika z posortowania po kluczu rodzicielskim
        #      (wspólny rodzic → rodzeństwo trafia obok siebie).

        pokolenia = {}
        for oid, g in glebokosc.items():
            pokolenia.setdefault(g, []).append(oid)

        def _klucz_rodzicielski(oid):
            """Zwraca tuple id rodziców — służy do grupowania rodzeństwa."""
            o = osoby.get(oid)
            if not o or not o.rodzic_ids:
                return ()
            return tuple(sorted(o.rodzic_ids))

        def _posortuj_pokolenie(ids):
            """
            Zwraca listę slotów: każdy slot to [oid] lub [oid_A, oid_B] (para).
            Kolejność: najpierw pary/singletony z rodzicami (grupowane po rodzicach),
            potem osoby bez rodziców.
            """
            odwiedzone = set()
            sloty = []

            # Sortuj wg klucza rodzicielskiego, potem po id (stabilność)
            posortowane = sorted(ids,
                                 key=lambda oid: (_klucz_rodzicielski(oid), oid))

            for oid in posortowane:
                if oid in odwiedzone:
                    continue
                o = osoby.get(oid)
                malz_id = o.malzonek_id if o else None
                if malz_id and malz_id in osoby and malz_id in ids \
                        and malz_id not in odwiedzone \
                        and glebokosc.get(malz_id) == glebokosc.get(oid):
                    # Para: pierwsza osoba + małżonek obok
                    sloty.append([oid, malz_id])
                    odwiedzone.add(oid)
                    odwiedzone.add(malz_id)
                else:
                    sloty.append([oid])
                    odwiedzone.add(oid)

            # Posortuj sloty: grupuj wg klucza rodzicielskiego pierwszej osoby w slocie
            sloty.sort(key=lambda s: (_klucz_rodzicielski(s[0]), s[0]))
            return sloty

        # ── Krok 3: przypisz współrzędne ──────────────────────────────────────
        bw = self.BOX_W * self._scale
        bh = self.BOX_H * self._scale
        hg = self.H_GAP * self._scale
        # Mniejszy odstęp wewnątrz pary małżeńskiej, większy między parami/rodzinami
        para_gap = max(4, 8 * self._scale)   # odstęp między małżonkami
        rodzina_gap = hg                      # odstęp między różnymi rodzinami/osobami
        vg = self.V_GAP * self._scale
        cw = max(self.canvas.winfo_width(), 800)
        cx = self._offset[0] + cw / 2

        self.positions = {}

        for gen in sorted(pokolenia.keys()):
            sloty = _posortuj_pokolenie(pokolenia[gen])

            # Oblicz łączną szerokość wiersza
            total_w = 0.0
            for i, slot in enumerate(sloty):
                if len(slot) == 2:
                    total_w += 2 * bw + para_gap
                else:
                    total_w += bw
                if i < len(sloty) - 1:
                    total_w += rodzina_gap

            y = self._offset[1] + gen * (bh + vg)
            x = cx - total_w / 2

            for slot in sloty:
                if len(slot) == 2:
                    self.positions[slot[0]] = (x, y)
                    self.positions[slot[1]] = (x + bw + para_gap, y)
                    x += 2 * bw + para_gap + rodzina_gap
                else:
                    self.positions[slot[0]] = (x, y)
                    x += bw + rodzina_gap

    def _rysuj_polaczenia(self):
        bw = self.BOX_W * self._scale
        bh = self.BOX_H * self._scale
        off = max(10, 14 * self._scale)
        narysowane = set()

        # ── Linie małżeńskie (różowe) ─────────────────────────────────────────
        for o in self.baza.osoby.values():
            if not o.malzonek_id or o.id not in self.positions:
                continue
            if o.malzonek_id not in self.positions:
                continue
            para = tuple(sorted([o.id, o.malzonek_id]))
            if para in narysowane:
                continue
            narysowane.add(para)
            x1, y1 = self.positions[o.id]
            x2, y2 = self.positions[o.malzonek_id]
            cx1, cy1 = x1 + bw / 2, y1 + bh
            cx2, cy2 = x2 + bw / 2, y2 + bh
            hy = max(cy1, cy2) + off
            self.canvas.create_line(cx1, cy1, cx1, hy, cx2, hy, cx2, cy2,
                                    fill="#d63880", width=2.5)
            mx = (cx1 + cx2) / 2
            r = max(4, 5 * self._scale)
            self.canvas.create_oval(mx-r, hy-r, mx+r, hy+r,
                                    fill="#d63880", outline="#a01050")

        # ── Linie rodzic–dziecko ──────────────────────────────────────────────
        # Grupuj dzieci według zestawu widzialnych rodziców (frozenset id)
        # Obsługuje: 2 rodziców, 1 rodzic, a nawet 0 widzialnych (pomijamy)
        grupy_2 = {}   # frozenset(2 rodziców) → [dzieci]
        grupy_1 = {}   # id jednego rodzica   → [dzieci]

        for o in self.baza.osoby.values():
            if o.id not in self.positions:
                continue
            r_w = [p for p in o.rodzic_ids if p in self.positions]
            if len(r_w) == 2:
                grupy_2.setdefault(frozenset(r_w), []).append(o.id)
            elif len(r_w) == 1:
                grupy_1.setdefault(r_w[0], []).append(o.id)

        # Dzieci z DWOJGIEM rodziców — linia od punktu środkowego pary
        for r_ids, dzieci in grupy_2.items():
            r_list = list(r_ids)
            p1, p2 = self.positions[r_list[0]], self.positions[r_list[1]]
            cx1, cx2 = p1[0] + bw / 2, p2[0] + bw / 2
            cy1, cy2 = p1[1] + bh,     p2[1] + bh
            hy  = max(cy1, cy2) + off
            jx  = (cx1 + cx2) / 2

            # Pozioma belka łącząca dzieci
            xs_dzieci = []
            for cid in dzieci:
                if cid not in self.positions:
                    continue
                xc, yc = self.positions[cid]
                xs_dzieci.append(xc + bw / 2)

            if not xs_dzieci:
                continue

            cy_dzieci = self.positions[dzieci[0]][1]   # y górnej krawędzi dzieci
            belt_y = (hy + cy_dzieci) / 2              # y poziomej belki

            # Pionowa linia od punktu środkowego pary do belki
            self.canvas.create_line(jx, hy, jx, belt_y,
                                    fill="#3a7fd4", width=1.8)

            if len(xs_dzieci) > 1:
                # Pozioma belka nad dziećmi
                self.canvas.create_line(min(xs_dzieci), belt_y,
                                        max(xs_dzieci), belt_y,
                                        fill="#3a7fd4", width=1.8)

            # Pionowe linie od belki do każdego dziecka
            for cid in dzieci:
                if cid not in self.positions:
                    continue
                xc, yc = self.positions[cid]
                cxc = xc + bw / 2
                self.canvas.create_line(cxc, belt_y, cxc, yc,
                                        fill="#3a7fd4", width=1.8)

        # Dzieci z JEDNYM rodzicem — linia prosto od dołu pudełka rodzica
        for pid, dzieci in grupy_1.items():
            if pid not in self.positions:
                continue
            px, py = self.positions[pid]
            pcx = px + bw / 2
            pcy = py + bh

            xs_dzieci = []
            for cid in dzieci:
                if cid not in self.positions:
                    continue
                xs_dzieci.append(self.positions[cid][0] + bw / 2)

            if not xs_dzieci:
                continue

            cy_dzieci = self.positions[dzieci[0]][1]
            belt_y = (pcy + off + cy_dzieci) / 2

            # Pionowa linia od rodzica do belki — przerywana (odróżnia od pełnej pary)
            self.canvas.create_line(pcx, pcy, pcx, belt_y,
                                    fill="#7a9fd4", width=1.8, dash=(6, 3))

            if len(xs_dzieci) > 1:
                self.canvas.create_line(min(xs_dzieci), belt_y,
                                        max(xs_dzieci), belt_y,
                                        fill="#7a9fd4", width=1.8, dash=(6, 3))

            for cid in dzieci:
                if cid not in self.positions:
                    continue
                xc, yc = self.positions[cid]
                cxc = xc + bw / 2
                self.canvas.create_line(cxc, belt_y, cxc, yc,
                                        fill="#7a9fd4", width=1.8, dash=(6, 3))

    def _rysuj_osoby(self):
        bw = self.BOX_W * self._scale
        bh = self.BOX_H * self._scale

        for o in self.baza.osoby.values():
            if o.id not in self.positions:
                continue
            x, y = self.positions[o.id]
            tag = f"os_{o.id}"

            if o.wydziedziczona:
                border, bg, tc = "#c0392b", "#fde8e8", "#c0392b"
            elif o.odrzucila_spadek:
                border, bg, tc = "#c07010", "#fef3e0", "#8b5000"
            elif not o.zyje:
                border, bg, tc = "#222222", "#d0d0d0", "#111111"
            elif o.plec == "K":
                border, bg, tc = "#c0356a", "#fce8f2", "#a0205a"
            else:
                border, bg, tc = "#2a72c8", "#e5f0fb", "#1a3a8a"

            self.canvas.create_rectangle(x, y, x+bw, y+bh, fill=bg, outline=border,
                                         width=2, tags=(tag,))
            fs = max(7, int(9 * self._scale))
            self.canvas.create_text(x+bw/2, y+bh*0.32, text=o.imie, fill=tc,
                                    font=("Segoe UI", fs, "bold"), tags=(tag,))
            self.canvas.create_text(x+bw/2, y+bh*0.62, text=o.nazwisko, fill=tc,
                                    font=("Segoe UI", max(6, int(8*self._scale))), tags=(tag,))
            if not o.zyje:
                self.canvas.create_text(x+bw/2, y+bh*0.88, text="✝", fill="#333",
                                        font=("Segoe UI", max(5, int(7*self._scale))), tags=(tag,))


# ── Dialog osoby (natywny tkinter) ───────────────────────────────────────────
class DialogOsoby(tk.Toplevel):
    """Dialog dodawania/edycji osoby w katalogu spadkowym."""

    def __init__(self, master, baza: BazaDanych, app_fonts: dict,
                 osoba: Osoba = None):
        super().__init__(master)
        self.baza = baza
        self.osoba = osoba
        self.f = app_fonts
        self.result = None
        self.auto_created = []
        self.title("Dodaj osobę" if not osoba else "Edytuj osobę")
        self.geometry("1100x780")
        self.resizable(True, True)
        self.grab_set()
        self._build()
        if osoba:
            self._fill(osoba)

    def _choices(self):
        return [""] + [f"{o.pelne_imie} [{o.id}]"
                       for o in sorted(self.baza.osoby.values(), key=lambda x: x.nazwisko)]

    def _resolve(self, s: str) -> str:
        s = s.strip()
        if not s:
            return ""
        if "[" in s and s.endswith("]"):
            eid = s.split("[")[-1][:-1]
            if eid in self.baza.osoby:
                return eid
        for o in self.baza.osoby.values():
            if o.pelne_imie.lower() == s.lower():
                return o.id
        parts = s.split(None, 1)
        nowa = Osoba(imie=parts[0], nazwisko=(parts[1] if len(parts) > 1 else "?"))
        self.baza.dodaj(nowa)
        self.auto_created.append(nowa)
        return nowa.id

    def _lbl(self, parent, text, row, col=0):
        tk.Label(parent, text=text, font=self.f["small"],
                 bg=PANEL, fg=MUTED, anchor="w").grid(
            row=row, column=col, sticky="w", padx=(0, 8), pady=(6, 1))

    def _ent(self, parent, row, col=1, width=24):
        e = tk.Entry(parent, font=self.f["body"], relief="flat", bd=0,
                     bg=CREAM, fg=TEXT, width=width,
                     highlightthickness=1, highlightbackground=BORDER)
        e.grid(row=row, column=col, columnspan=2, sticky="ew",
               padx=(4, 8), pady=2, ipady=4)
        return e

    def _sep(self, parent, row, text):
        f = tk.Frame(parent, bg="#d0e4f4")
        f.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(12, 2))
        tk.Label(f, text=f"  {text}", font=self.f["small_bold"],
                 bg="#d0e4f4", fg="#1a5fa8", anchor="w").pack(fill="x", padx=4, pady=3)

    def _build(self):
        self.configure(bg=CREAM)
        tk.Label(self, text="Dane osoby", font=self.f["sub"],
                 bg=CREAM, fg=TEXT).pack(pady=(14, 4))

        scroll_outer = tk.Frame(self, bg=CREAM)
        scroll_outer.pack(fill="both", expand=True, padx=8)

        canvas = tk.Canvas(scroll_outer, bg=CREAM, highlightthickness=0)
        vsb = ttk.Scrollbar(scroll_outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        self._form = tk.Frame(canvas, bg=PANEL)
        win = canvas.create_window((0, 0), window=self._form, anchor="nw")

        def _conf(e):
            canvas.configure(scrollregion=canvas.bbox("all"))
        self._form.bind("<Configure>", _conf)

        def _resize(e):
            canvas.itemconfig(win, width=e.width)
        canvas.bind("<Configure>", _resize)

        def _scroll(e):
            canvas.yview_scroll(int(-1*(e.delta/120)), "units")
        canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", _scroll))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

        f = self._form
        f.columnconfigure(1, weight=1)

        self._sep(f, 0, "Dane podstawowe")
        self._lbl(f, "Imię *:", 1)
        self.e_imie = self._ent(f, 1)
        self._lbl(f, "Nazwisko *:", 2)
        self.e_nazwisko = self._ent(f, 2)
        self._lbl(f, "Data urodzenia:", 3)
        self.e_ur = self._ent(f, 3)
        tk.Label(f, text="DD-MM-RRRR lub DDMMRRRR", font=self.f["small"],
                 bg=PANEL, fg="#aaaaaa").grid(row=3, column=3, sticky="w")
        self._lbl(f, "Data śmierci:", 4)
        self.e_sm = self._ent(f, 4)
        tk.Label(f, text="puste = żyje", font=self.f["small"],
                 bg=PANEL, fg="#aaaaaa").grid(row=4, column=3, sticky="w")

        self._lbl(f, "Płeć *:", 5)
        pf = tk.Frame(f, bg=PANEL)
        pf.grid(row=5, column=1, columnspan=2, sticky="w", padx=(4, 0))
        self.v_plec = tk.StringVar(value="M")
        tk.Radiobutton(pf, text="Mężczyzna", variable=self.v_plec, value="M",
                       bg=PANEL, font=self.f["body"]).pack(side="left")
        tk.Radiobutton(pf, text="Kobieta", variable=self.v_plec, value="K",
                       bg=PANEL, font=self.f["body"]).pack(side="left", padx=(12, 0))

        self._sep(f, 6, "Rodzice  (z listy lub: Imię Nazwisko → auto-dodanie)")
        self._lbl(f, "Rodzic 1:", 7)
        self.cb_r1 = ttk.Combobox(f, values=self._choices(), font=self.f["body"], width=30)
        self.cb_r1.grid(row=7, column=1, columnspan=2, sticky="ew", padx=(4, 8), pady=2, ipady=2)
        self._lbl(f, "Rodzic 2:", 8)
        self.cb_r2 = ttk.Combobox(f, values=self._choices(), font=self.f["body"], width=30)
        self.cb_r2.grid(row=8, column=1, columnspan=2, sticky="ew", padx=(4, 8), pady=2, ipady=2)

        self._sep(f, 9, "Rodzeństwo")
        tk.Label(f,
            text="Wpisz imię i nazwisko lub wybierz z listy poniżej. "
                 "Sprzężone — wspólny rodzic ustawiany automatycznie.",
            font=self.f["small"], bg=PANEL, fg="#888", anchor="w", wraplength=440
        ).grid(row=10, column=0, columnspan=3, sticky="w", padx=4, pady=(0, 2))

        rod_frame = tk.Frame(f, bg=PANEL)
        rod_frame.grid(row=11, column=0, columnspan=3, sticky="ew", padx=4, pady=(0, 4))

        # Górny pasek: combobox z istniejącymi osobami + przycisk Dodaj
        rod_top = tk.Frame(rod_frame, bg=PANEL)
        rod_top.pack(fill="x", pady=(0, 2))

        self.e_rodz_input = ttk.Combobox(
            rod_top, font=self.f["body"],
            values=[""] + [o.pelne_imie for o in
                           sorted(self.baza.osoby.values(), key=lambda x: x.nazwisko)
                           if not (self.osoba and o.id == self.osoba.id)])
        self.e_rodz_input.pack(side="left", fill="x", expand=True, padx=(0, 4))

        def _dodaj_rodz():
            val = self.e_rodz_input.get().strip()
            if not val:
                return
            if val in self.lb_rodz.get(0, "end"):
                self.e_rodz_input.set("")
                return
            self.lb_rodz.insert("end", val)
            self.e_rodz_input.set("")

        tk.Button(rod_top, text="+ Dodaj", command=_dodaj_rodz,
                  bg=GOLD_LT, fg=TEXT, font=self.f["small"], relief="flat",
                  padx=8, pady=3, cursor="hand2").pack(side="left")

        # Lista dodanego rodzeństwa
        rod_bot = tk.Frame(rod_frame, bg=PANEL)
        rod_bot.pack(fill="x")

        self.lb_rodz = tk.Listbox(rod_bot, font=self.f["body"], bg=CREAM, fg=TEXT,
                                   relief="flat", highlightthickness=1,
                                   highlightbackground=BORDER, height=4,
                                   exportselection=False, selectmode="single")
        rod_vsb = ttk.Scrollbar(rod_bot, orient="vertical", command=self.lb_rodz.yview)
        self.lb_rodz.configure(yscrollcommand=rod_vsb.set)
        rod_vsb.pack(side="right", fill="y")
        self.lb_rodz.pack(side="left", fill="both", expand=True)

        def _usun_rodz():
            sel = self.lb_rodz.curselection()
            if sel:
                self.lb_rodz.delete(sel[0])

        tk.Button(rod_frame, text="✖ Usuń zaznaczone", command=_usun_rodz,
                  bg="#e0e0e0", fg=TEXT, font=self.f["small"], relief="flat",
                  padx=6, pady=2, cursor="hand2").pack(anchor="e", pady=(2, 0))

        self._sep(f, 12, "Dzieci")
        tk.Label(f,
            text="Wpisz imię i nazwisko lub wybierz z listy. "
                 "Sprzężone — dziecku zostanie ustawiony ten rodzic automatycznie.",
            font=self.f["small"], bg=PANEL, fg="#888", anchor="w", wraplength=440
        ).grid(row=13, column=0, columnspan=3, sticky="w", padx=4, pady=(0, 2))

        dz_frame = tk.Frame(f, bg=PANEL)
        dz_frame.grid(row=14, column=0, columnspan=3, sticky="ew", padx=4, pady=(0, 4))

        dz_top = tk.Frame(dz_frame, bg=PANEL)
        dz_top.pack(fill="x", pady=(0, 2))
        self.e_dzieci_input = ttk.Combobox(
            dz_top, font=self.f["body"],
            values=[""] + [o.pelne_imie for o in
                           sorted(self.baza.osoby.values(), key=lambda x: x.nazwisko)
                           if not (self.osoba and o.id == self.osoba.id)])
        self.e_dzieci_input.pack(side="left", fill="x", expand=True, padx=(0, 4))

        def _dodaj_dziecko():
            val = self.e_dzieci_input.get().strip()
            if not val or val in self.lb_dzieci.get(0, "end"):
                self.e_dzieci_input.set("")
                return
            self.lb_dzieci.insert("end", val)
            self.e_dzieci_input.set("")

        tk.Button(dz_top, text="+ Dodaj", command=_dodaj_dziecko,
                  bg=GOLD_LT, fg=TEXT, font=self.f["small"], relief="flat",
                  padx=8, pady=3, cursor="hand2").pack(side="left")

        dz_bot = tk.Frame(dz_frame, bg=PANEL)
        dz_bot.pack(fill="x")
        self.lb_dzieci = tk.Listbox(dz_bot, font=self.f["body"], bg=CREAM, fg=TEXT,
                                     relief="flat", highlightthickness=1,
                                     highlightbackground=BORDER, height=4,
                                     exportselection=False, selectmode="single")
        dz_vsb = ttk.Scrollbar(dz_bot, orient="vertical", command=self.lb_dzieci.yview)
        self.lb_dzieci.configure(yscrollcommand=dz_vsb.set)
        dz_vsb.pack(side="right", fill="y")
        self.lb_dzieci.pack(side="left", fill="both", expand=True)

        def _usun_dziecko():
            sel = self.lb_dzieci.curselection()
            if sel:
                self.lb_dzieci.delete(sel[0])

        tk.Button(dz_frame, text="✖ Usuń zaznaczone", command=_usun_dziecko,
                  bg="#e0e0e0", fg=TEXT, font=self.f["small"], relief="flat",
                  padx=6, pady=2, cursor="hand2").pack(anchor="e", pady=(2, 0))

        # ── Małżonek / Małżonka (row 15–16) ──────────────────────────────────
        self._sep(f, 15, "Małżonek / Małżonka")
        self._lbl(f, "Małżonek/a:", 16)
        self.cb_m = ttk.Combobox(f, values=self._choices(), font=self.f["body"], width=30)
        self.cb_m.grid(row=16, column=1, columnspan=2, sticky="ew", padx=(4, 8), pady=2, ipady=2)

        # ── Dokumenty urzędowe (row 17–21) ───────────────────────────────────
        self._sep(f, 17, "Dokumenty urzędowe")
        tk.Label(f,
            text="Zaznacz dokumenty POSIADANE. Akt urodzenia i akt małżeństwa są zamienne "
                 "— wystarczy jeden z nich. Brak obu → alert w raporcie.",
            font=self.f["small"], bg=PANEL, fg="#888", anchor="w",
            wraplength=420, justify="left"
        ).grid(row=18, column=0, columnspan=3, sticky="w", padx=4)
        self.v_akt_ur = tk.BooleanVar(value=True)
        self.v_akt_ml = tk.BooleanVar(value=False)
        self.v_akt_sm = tk.BooleanVar(value=False)
        tk.Checkbutton(f, text="Posiadam akt urodzenia", variable=self.v_akt_ur,
                       bg=PANEL, font=self.f["body"]).grid(
                           row=19, column=0, columnspan=3, sticky="w", padx=4, pady=2)
        tk.Checkbutton(f, text="Posiadam akt małżeństwa", variable=self.v_akt_ml,
                       bg=PANEL, font=self.f["body"]).grid(
                           row=20, column=0, columnspan=3, sticky="w", padx=4, pady=2)
        self.cb_akt_sm = tk.Checkbutton(
            f, text="Posiadam akt zgonu",
            variable=self.v_akt_sm, bg=PANEL,
            font=self.f["body"], state="disabled",
            disabledforeground="#aaaaaa")
        self.cb_akt_sm.grid(row=21, column=0, columnspan=3, sticky="w", padx=4, pady=2)
        self.e_sm.bind("<KeyRelease>", self._toggle_zgon)
        self.e_sm.bind("<FocusOut>", self._toggle_zgon)

        # ── Status prawny (row 22–28) ─────────────────────────────────────────
        self._sep(f, 22, "Status prawny")

        self.v_zrzekla = tk.BooleanVar()
        self.v_zrzeczenie_zstepnych = tk.BooleanVar(value=True)

        tk.Checkbutton(f,
            text="Zrzeczenie się dziedziczenia (art. 1048 KC) — wyłącza z dziedziczenia",
            variable=self.v_zrzekla,
            command=self._toggle_zrzeczenie,
            bg=PANEL, font=self.f["body"]
        ).grid(row=23, column=0, columnspan=3, sticky="w", padx=4, pady=2)

        self.cb_zrzeczenie_zstepnych = tk.Checkbutton(f,
            text="Zrzeczenie obejmuje też zstępnych (art. 1049 §1 KC — domyślnie TAK)",
            variable=self.v_zrzeczenie_zstepnych,
            bg=PANEL, font=self.f["small"],
            state="disabled"
        )
        self.cb_zrzeczenie_zstepnych.grid(
            row=24, column=0, columnspan=3, sticky="w", padx=24, pady=1
        )

        self.v_odrz = tk.BooleanVar()
        tk.Checkbutton(f,
            text="Odrzucenie spadku (art. 1020 KC) — zstępni wchodzą w miejsce",
            variable=self.v_odrz,
            bg=PANEL, font=self.f["body"]
        ).grid(row=25, column=0, columnspan=3, sticky="w", padx=4, pady=2)

        self.v_wydz = tk.BooleanVar()
        tk.Label(f,
            text="⚠ Wydziedziczenie (art. 1008 KC) — pozbawia wyłącznie ZACHOWKU,\n"
                 "    nie ma wpływu na dziedziczenie ustawowe. Odnotuj dla celów informacyjnych.",
            font=self.f["small"], bg="#fffbe6", fg="#7a5c00",
            justify="left", padx=6, pady=4
        ).grid(row=26, column=0, columnspan=3, sticky="ew", padx=4)

        tk.Checkbutton(f,
            text="Wydziedziczona/y (art. 1008 KC — tylko zachowek)",
            variable=self.v_wydz,
            bg=PANEL, font=self.f["body"]
        ).grid(row=27, column=0, columnspan=3, sticky="w", padx=4, pady=2)

        # ── Notatki (row 28–29) ───────────────────────────────────────────────
        self._sep(f, 28, "Notatki")
        self.e_notatki = tk.Text(f, height=3, font=self.f["body"],
                                  bg=CREAM, fg=TEXT, relief="flat",
                                  highlightthickness=1, highlightbackground=BORDER)
        self.e_notatki.grid(row=29, column=0, columnspan=3, sticky="ew", padx=4, pady=(4, 8))

        bf = tk.Frame(self, bg=CREAM)
        bf.pack(fill="x", padx=16, pady=10)
        tk.Button(bf, text="✔ Zapisz", command=self._zapisz,
                  bg=GOLD, fg=BG, font=self.f["bold"], relief="flat",
                  padx=18, pady=7, cursor="hand2").pack(side="left", expand=True, padx=4)
        tk.Button(bf, text="✖ Anuluj", command=self.destroy,
                  bg="#c0c0c0", fg=TEXT, font=self.f["body"], relief="flat",
                  padx=18, pady=7, cursor="hand2").pack(side="left", expand=True, padx=4)

    def _toggle_zgon(self, e=None):
        if self.e_sm.get().strip():
            self.cb_akt_sm.config(state="normal")
        else:
            self.v_akt_sm.set(False)
            self.cb_akt_sm.config(state="disabled")

    def _toggle_zrzeczenie(self, *_):
        if self.v_zrzekla.get():
            self.cb_zrzeczenie_zstepnych.config(state="normal")
        else:
            self.cb_zrzeczenie_zstepnych.config(state="disabled")

    def _fill(self, o: Osoba):
        self.e_imie.insert(0, o.imie)
        self.e_nazwisko.insert(0, o.nazwisko)
        self.e_ur.insert(0, _sp_fmt_date(o.data_urodzenia))
        self.e_sm.insert(0, _sp_fmt_date(o.data_smierci))
        self._toggle_zgon()
        self.v_plec.set(o.plec)
        self.v_wydz.set(o.wydziedziczona)
        self.v_odrz.set(o.odrzucila_spadek)
        self.e_notatki.insert("1.0", o.notatki)
        self.v_akt_ur.set(o.akt_urodzenia)
        self.v_akt_ml.set(o.akt_malzenstwa)
        self.v_akt_sm.set(o.akt_smierci)
        self.v_zrzekla.set(o.zrzekla_sie)
        self.v_zrzeczenie_zstepnych.set(o.zrzeczenie_obejmuje_zstepnych)
        self._toggle_zrzeczenie()

        def find_c(rid):
            for c in self._choices():
                if f"[{rid}]" in c:
                    return c
            return ""

        if len(o.rodzic_ids) >= 1:
            self.cb_r1.set(find_c(o.rodzic_ids[0]))
        if len(o.rodzic_ids) >= 2:
            self.cb_r2.set(find_c(o.rodzic_ids[1]))
        if o.malzonek_id:
            self.cb_m.set(find_c(o.malzonek_id))

        # Rodzeństwo — deduplikacja przez set (osoba z 2 wspólnych rodziców != 2x)
        if o.rodzic_ids:
            juz_dodane = set()
            for pid in o.rodzic_ids:
                for dziecko in self.baza.dzieci(pid):
                    if dziecko.id != o.id and dziecko.pelne_imie not in juz_dodane:
                        juz_dodane.add(dziecko.pelne_imie)
                        self.lb_rodz.insert("end", dziecko.pelne_imie)

        # Dzieci
        for dziecko in self.baza.dzieci(o.id):
            self.lb_dzieci.insert("end", dziecko.pelne_imie)

    def _norm_date(self, raw):
        raw = raw.strip()
        if not raw:
            return ""
        try:
            return _sp_parse_date(raw).strftime("%d-%m-%Y")
        except ValueError:
            messagebox.showerror("Błąd daty",
                f"Nieprawidłowy format: '{raw}'\nUżyj DD-MM-RRRR lub DDMMRRRR", parent=self)
            return None

    def _zapisz(self):
        imie = self.e_imie.get().strip()
        nazwisko = self.e_nazwisko.get().strip()
        if not imie or not nazwisko:
            messagebox.showerror("Błąd", "Imię i nazwisko są wymagane.", parent=self)
            return
        data_ur = self._norm_date(self.e_ur.get())
        if data_ur is None:
            return
        data_sm = self._norm_date(self.e_sm.get())
        if data_sm is None:
            return

        r1 = self._resolve(self.cb_r1.get())
        r2 = self._resolve(self.cb_r2.get())
        rodzic_ids = []
        if r1:
            rodzic_ids.append(r1)
        if r2 and r2 != r1:
            rodzic_ids.append(r2)
        malzonek_id = self._resolve(self.cb_m.get()) or None

        notatki = self.e_notatki.get("1.0", "end").strip()
        if self.osoba:
            o = self.osoba
            o.imie, o.nazwisko = imie, nazwisko
            o.data_urodzenia, o.data_smierci = data_ur, data_sm
            o.plec = self.v_plec.get()
            o.rodzic_ids = rodzic_ids
            o.malzonek_id = malzonek_id
            o.wydziedziczona = self.v_wydz.get()
            o.odrzucila_spadek = self.v_odrz.get()
            o.notatki = notatki
            o.akt_urodzenia = self.v_akt_ur.get()
            o.akt_malzenstwa = self.v_akt_ml.get()
            o.akt_smierci = self.v_akt_sm.get()
            o.zrzekla_sie = self.v_zrzekla.get()
            o.zrzeczenie_obejmuje_zstepnych = self.v_zrzeczenie_zstepnych.get()
            self.result = o
        else:
            self.result = Osoba(
                imie=imie, nazwisko=nazwisko,
                data_urodzenia=data_ur, data_smierci=data_sm,
                plec=self.v_plec.get(), rodzic_ids=rodzic_ids,
                malzonek_id=malzonek_id,
                wydziedziczona=self.v_wydz.get(),
                odrzucila_spadek=self.v_odrz.get(),
                notatki=notatki,
                akt_urodzenia=self.v_akt_ur.get(),
                akt_malzenstwa=self.v_akt_ml.get(),
                akt_smierci=self.v_akt_sm.get(),
                zrzekla_sie=self.v_zrzekla.get(),
                zrzeczenie_obejmuje_zstepnych=self.v_zrzeczenie_zstepnych.get(),
            )
            self.baza.dodaj(self.result)

        ja = self.result

        # ── Sprzężenie małżonka (obustronne) ─────────────────────────────────
        if malzonek_id and malzonek_id in self.baza.osoby:
            m = self.baza.osoby[malzonek_id]
            # Odepnij poprzedniego małżonka m (jeśli istnieje i jest inny)
            if m.malzonek_id and m.malzonek_id != ja.id:
                prev = self.baza.osoby.get(m.malzonek_id)
                if prev and prev.malzonek_id == m.id:
                    prev.malzonek_id = None
            m.malzonek_id = ja.id
        # Jeśli usunięto małżonka — odepnij po drugiej stronie
        if self.osoba and self.osoba.malzonek_id and self.osoba.malzonek_id != malzonek_id:
            stary_m = self.baza.osoby.get(self.osoba.malzonek_id)
            if stary_m and stary_m.malzonek_id == ja.id:
                stary_m.malzonek_id = None

        # ── Sprzężenie rodziców (obustronne: rodzic dostaje to dziecko) ──────
        for pid in ja.rodzic_ids:
            rodzic = self.baza.osoby.get(pid)
            # (relacja rodzic→dziecko wynika z dziecko.rodzic_ids, nie ma osobnego pola)

        # ── Sprzężenie rodzeństwa ─────────────────────────────────────────────
        # Zbierz nazwy z listboxa i zmapuj na obiekty Osoba (lub auto-utwórz)
        nazwy_w_liscie = list(self.lb_rodz.get(0, "end"))
        for nazwa in nazwy_w_liscie:
            nazwa = nazwa.strip()
            if not nazwa:
                continue
            # Znajdź istniejącą osobę po pelne_imie lub utwórz nową
            rodz_obj = next(
                (o for o in self.baza.osoby.values() if o.pelne_imie == nazwa),
                None)
            if rodz_obj is None:
                # Auto-utwórz z wpisanego imienia i nazwiska
                czesci = nazwa.split(None, 1)
                rodz_obj = Osoba(
                    imie=czesci[0],
                    nazwisko=(czesci[1] if len(czesci) > 1 else "?"))
                self.baza.dodaj(rodz_obj)

            # Nadaj wspólnych rodziców (sprzężenie)
            for pid in ja.rodzic_ids:
                if pid not in rodz_obj.rodzic_ids:
                    rodz_obj.rodzic_ids.append(pid)

        # ── Sprzężenie dzieci ─────────────────────────────────────────────
        for nazwa in self.lb_dzieci.get(0, "end"):
            nazwa = nazwa.strip()
            if not nazwa:
                continue
            dz_obj = next(
                (o for o in self.baza.osoby.values() if o.pelne_imie == nazwa), None)
            if dz_obj is None:
                czesci = nazwa.split(None, 1)
                dz_obj = Osoba(imie=czesci[0],
                               nazwisko=(czesci[1] if len(czesci) > 1 else "?"))
                self.baza.dodaj(dz_obj)
            if ja.id not in dz_obj.rodzic_ids:
                dz_obj.rodzic_ids.append(ja.id)

        self.destroy()

