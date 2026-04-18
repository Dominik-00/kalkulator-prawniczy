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
                 akt_smierci: bool = True,
                 podstawa_odrzucenia: str = "",
                 podstawa_odrzucenia_tekst: str = ""):
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
        # Podstawa odrzucenia: "akta_n" | "oswiadczenie_sadowe" | "akt_notarialny" | "inne_akta" | ""
        self.podstawa_odrzucenia = podstawa_odrzucenia
        # Tekst uzupełniający dla "akta_n" i "inne_akta"
        self.podstawa_odrzucenia_tekst = podstawa_odrzucenia_tekst

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
            "podstawa_odrzucenia": self.podstawa_odrzucenia,
            "podstawa_odrzucenia_tekst": self.podstawa_odrzucenia_tekst,
        }

    @staticmethod
    def from_dict(d):
        d = dict(d)
        d.setdefault("akt_urodzenia", True)
        d.setdefault("akt_malzenstwa", True)
        d.setdefault("akt_smierci", True)
        d.setdefault("zrzekla_sie", False)
        d.setdefault("zrzeczenie_obejmuje_zstepnych", True)
        d.setdefault("podstawa_odrzucenia", "")
        d.setdefault("podstawa_odrzucenia_tekst", "")
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
        """Zapis niezaszyfrowany — zachowany dla kompatybilności wstecznej.
        W nowym kodzie używaj zapisz_zaszyfrowana()."""
        self.plik = plik
        with open(plik, "w", encoding="utf-8") as f:
            json.dump([o.to_dict() for o in self.osoby.values()], f,
                      ensure_ascii=False, indent=2)

    def wczytaj(self, plik: str):
        """Odczyt niezaszyfrowany — zachowany dla kompatybilności wstecznej.
        W nowym kodzie używaj wczytaj_zaszyfrowana()."""
        self.plik = plik
        with open(plik, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.osoby = {d["id"]: Osoba.from_dict(d) for d in data}

    # ── F-02: metody szyfrujące (RODO art. 25, 32(1)(a)) ─────────────────────

    def zapisz_zaszyfrowana(self, plik: str, haslo: str) -> None:
        """
        Serializuje bazę do JSON, szyfruje AES-256-GCM i zapisuje do pliku .kpj.

        Parametry:
            plik  — ścieżka docelowa (zalecane rozszerzenie .kpj)
            haslo — hasło podane przez użytkownika; używane do wyprowadzenia klucza
                    metodą PBKDF2-SHA256 (480 000 iteracji, 128-bitowa sól losowa)

        Rzuca:
            ImportError — gdy biblioteka cryptography nie jest zainstalowana
            OSError     — przy błędzie zapisu pliku
        """
        from crypto_helper import zapisz_zaszyfrowany
        self.plik = plik
        dane = [o.to_dict() for o in self.osoby.values()]
        zapisz_zaszyfrowany(plik, dane, haslo)

    def wczytaj_zaszyfrowana(self, plik: str, haslo: str) -> None:
        """
        Odczytuje plik .kpj, odszyfrowuje i ładuje osoby do bazy.

        Rzuca:
            ImportError — gdy biblioteka cryptography nie jest zainstalowana
            ValueError  — przy złym haśle lub uszkodzonym pliku
            OSError     — przy błędzie odczytu pliku
        """
        from crypto_helper import wczytaj_zaszyfrowany
        self.plik = plik
        dane = wczytaj_zaszyfrowany(plik, haslo)
        self.osoby = {d["id"]: Osoba.from_dict(d) for d in dane}

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

    def _przodkowie(self, oid: str) -> set:
        """Zwraca zbiór ID wszystkich przodków (rodzice, dziadkowie itd.) metodą BFS."""
        wynik = set()
        kolejka = list(self.rodzice(oid))
        while kolejka:
            p = kolejka.pop()
            if p.id in wynik:
                continue
            wynik.add(p.id)
            kolejka.extend(self.rodzice(p.id))
        return wynik

    def sprawdz_niedozwolony_zwiazek(self, osoba_id, kandydat_id,
                                      extra_rodzice_osoby=None) -> str:
        """
        Sprawdza dopuszczalność prawną małżeństwa (KRiO art. 14 §1).

        Parametry:
            osoba_id             — ID osoby edytowanej (None gdy dodawana nowa)
            kandydat_id          — ID proponowanego małżonka
            extra_rodzice_osoby  — lista ID rodziców nowej osoby (gdy osoba_id=None)

        Zwraca:
            Pusty string gdy związek jest dozwolony.
            Komunikat błędu gdy niedozwolony.
        """
        if not kandydat_id:
            return ""
        if osoba_id and osoba_id == kandydat_id:
            return "Osoba nie może być własnym małżonkiem (KRiO art. 10 §1)."

        # Zbuduj zbiór przodków osoby i jej rodziców
        if osoba_id and osoba_id in self.osoby:
            rodzice_osoby_ids = {p.id for p in self.rodzice(osoba_id)}
            przodkowie_osoby = self._przodkowie(osoba_id)
        else:
            rodzice_osoby_ids = set(extra_rodzice_osoby or [])
            przodkowie_osoby = set(rodzice_osoby_ids)
            for pid in rodzice_osoby_ids:
                przodkowie_osoby |= self._przodkowie(pid)

        przodkowie_kandydata = self._przodkowie(kandydat_id)

        # Krewny w linii prostej wstępnej (kandydat jest przodkiem osoby)
        if kandydat_id in przodkowie_osoby:
            return ("Niedozwolone małżeństwo z krewnym w linii prostej (przodek). "
                    "KRiO art. 14 §1.")

        # Krewny w linii prostej zstępnej (osoba jest przodkiem kandydata)
        if osoba_id and osoba_id in przodkowie_kandydata:
            return ("Niedozwolone małżeństwo z krewnym w linii prostej (zstępny). "
                    "KRiO art. 14 §1.")

        # Rodzeństwo — w tym przyrodnie (wspólny co najmniej jeden rodzic)
        rodzice_kandydata_ids = {p.id for p in self.rodzice(kandydat_id)}
        if rodzice_osoby_ids & rodzice_kandydata_ids:
            return ("Niedozwolone małżeństwo między rodzeństwem lub przyrodnim "
                    "rodzeństwem. KRiO art. 14 §1.")

        return ""


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

    def _udzialy_zstepnych(self, id: str) -> dict:
        """
        Zwraca udziały reprezentantów danej osoby według zasad reprezentacji.

        Każde dziecko tworzy osobną gałąź; jeżeli nie może dziedziczyć, w jego
        miejsce wchodzą jego zstępni, dzieląc udział tej gałęzi dalej
        rekurencyjnie.
        """
        o = self.baza.osoby.get(id)
        if o and o.zrzekla_sie and o.zrzeczenie_obejmuje_zstepnych:
            return {}

        galezie = []
        for d in self.baza.dzieci(id):
            if d.id == self.sp_id:
                continue
            if d.zyje and self._efektywny(d.id):
                galezie.append({d.id: Fraction(1)})
            else:
                udzialy = self._udzialy_zstepnych(d.id)
                if udzialy:
                    galezie.append(udzialy)

        if not galezie:
            return {}

        wynik = {}
        czesc_na_galaz = Fraction(1, len(galezie))
        for galaz in galezie:
            for oid, udzial in galaz.items():
                wynik[oid] = wynik.get(oid, Fraction(0)) + udzial * czesc_na_galaz
        return wynik

    def _pasierb_uprawniony(self, osoba) -> bool:
        """
        Art. 934(1) KC: pasierb dziedziczy tylko wtedy, gdy nie dożył otwarcia
        spadku żaden z jego rodziców poza spadkodawcą.
        """
        if not osoba or not osoba.zyje or not self._efektywny(osoba.id):
            return False
        if self.sp_id in osoba.rodzic_ids:
            return False

        inni_rodzice = [rid for rid in osoba.rodzic_ids if rid != self.sp_id]
        for rid in inni_rodzice:
            rodzic = self.baza.osoby.get(rid)
            if rodzic and rodzic.zyje:
                return False
        return True

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
        if not dziadkowie:
            wuj = [w for w in self.baza.wujkowie_ciotki(self.sp_id)
                   if self._efektywny(w.id) and w.zyje]
            if wuj:
                c = Fraction(1, len(wuj))
                return {w.id: c for w in wuj}
            return self._group_IV()

        galezie = []
        for dziadek in dziadkowie:
            if dziadek.zyje and self._efektywny(dziadek.id):
                galezie.append({dziadek.id: Fraction(1)})
                continue

            udzialy_zstepnych = self._udzialy_zstepnych(dziadek.id)
            if udzialy_zstepnych:
                galezie.append(udzialy_zstepnych)

        if not galezie:
            return self._group_IV()

        wynik = {}
        czesc_na_galaz = Fraction(1, len(galezie))
        for galaz in galezie:
            for oid, udzial in galaz.items():
                wynik[oid] = wynik.get(oid, Fraction(0)) + udzial * czesc_na_galaz
        return wynik

    def _group_IV(self) -> dict:
        malzonek = self.baza.malzonek(self.sp_id)
        if malzonek:
            pasierbowie = [d for d in self.baza.dzieci(malzonek.id)
                           if self._pasierb_uprawniony(d)]
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
    # Dodaj osoby, które odrzuciły spadek — też wymagają dokumentów
    for o in baza.osoby.values():
        if o.odrzucila_spadek:
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

    # ── Podstawy odrzucenia spadku ─────────────────────────────────────────────
    _PODSTAWY_ETYKIETY = {
        "akta_n":             "Akta N",
        "oswiadczenie_sadowe": "Oświadczenie w toku postępowania sądowego",
        "akt_notarialny":      "Akt notarialny w aktach",
        "inne_akta":           "Inne akta",
    }
    odrzucajacy = [o for o in baza.osoby.values() if o.odrzucila_spadek]
    if odrzucajacy:
        elements.append(Spacer(1, 12))
        elements.append(Paragraph("PODSTAWY ODRZUCENIA SPADKU", sekcja_s))
        odrz_data = [["Osoba", "Podstawa odrzucenia", "Sygnatura / opis"]]
        for o in sorted(odrzucajacy, key=lambda x: x.nazwisko):
            etykieta = _PODSTAWY_ETYKIETY.get(o.podstawa_odrzucenia, "")
            if not etykieta:
                etykieta = "⚠ nie wskazano podstawy"
            tekst = o.podstawa_odrzucenia_tekst or ""
            if o.podstawa_odrzucenia in ("akta_n", "inne_akta") and not tekst:
                tekst = "⚠ brak opisu (pole tekstowe niewypełnione)"
            odrz_data.append([o.pelne_imie, etykieta, tekst])
        to = Table(odrz_data, colWidths=[5*cm, 6*cm, 5*cm])
        to.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#5a3e8a")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), PDF_BOLD), ("FONTNAME", (0, 1), (-1, -1), PDF_REG),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f3eeff"), colors.white]),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
            ("LEFTPADDING", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        elements.append(to)

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
        self.canvas.bind("<ButtonRelease-1>", self._stop_drag)
        self.canvas.bind("<MouseWheel>", self._zoom)
        self.canvas.bind("<Button-4>", self._zoom)
        self.canvas.bind("<Button-5>", self._zoom)
        self.canvas.bind("<Double-Button-1>", self._dwuklik)
        self.canvas.bind("<ButtonPress-3>", self._kontekst)
        self._pan_start = None
        self._drag_osoba_id = None
        self._custom_offsets = {}   # {oid: (dx, dy)} w jednostkach bez skali
        self._scale = 1.0
        self._offset = [50, 50]
        self.positions = {}
        self.on_select = None
        self.on_edit = None
        self.on_delete = None

    def _get_osoba_at(self, x, y):
        items = self.canvas.find_overlapping(x - 1, y - 1, x + 1, y + 1)
        for item in reversed(items):
            for t in self.canvas.gettags(item):
                if t.startswith("os_"):
                    return t[3:]
        return None

    def _start_pan(self, e):
        self._pan_start = (e.x, e.y)
        oid = self._get_osoba_at(e.x, e.y)
        if oid:
            self._drag_osoba_id = oid
            if self.on_select:
                self.on_select(oid)
        else:
            self._drag_osoba_id = None

    def _pan(self, e):
        if not self._pan_start:
            return
        dx = e.x - self._pan_start[0]
        dy = e.y - self._pan_start[1]
        self._pan_start = (e.x, e.y)
        if self._drag_osoba_id:
            prev = self._custom_offsets.get(self._drag_osoba_id, (0.0, 0.0))
            self._custom_offsets[self._drag_osoba_id] = (
                prev[0] + dx / self._scale,
                prev[1] + dy / self._scale,
            )
        else:
            self._offset[0] += dx
            self._offset[1] += dy
        self.odrysuj()

    def _stop_drag(self, e):
        self._drag_osoba_id = None
        self._pan_start = None

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

    def reset_pozycji(self):
        """Czyści ręczne przesunięcia i resetuje widok do układu automatycznego."""
        self._custom_offsets.clear()
        self._scale = 1.0
        self._offset = [50, 50]
        self.odrysuj()

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

            # Posortuj sloty wg średniego X rodziców (już obliczonego w poprzednim
            # pokoleniu). Gwarantuje, że dzieci trafiają pod właściwych rodziców,
            # niezależnie od przypadkowych wartości UUID.
            # Slot może zaczynać się od małżonka bez rodziców w bazie (s[0]),
            # dlatego przeszukujemy rodziców WSZYSTKICH członków slotu.
            def _klucz_slotu(s):
                xs = []
                for mid in s:
                    o = osoby.get(mid)
                    for r in (o.rodzic_ids if o else []):
                        if r in self.positions:
                            xs.append(self.positions[r][0])
                if xs:
                    # Dzieci z rodzicami na pozycjach — sortuj wg ich środka X
                    return (0, sum(xs) / len(xs), s[0])
                # Fallback: brak znanych pozycji rodziców (pokolenie 0)
                return (1, 0.0, s[0])

            sloty.sort(key=_klucz_slotu)
            return sloty

        # ── Krok 3: przypisz współrzędne (bottom-up szerokość → top-down pozycje) ─
        bw = self.BOX_W * self._scale
        bh = self.BOX_H * self._scale
        hg = self.H_GAP * self._scale
        para_gap = max(4, 8 * self._scale)
        rodzina_gap = hg
        vg = self.V_GAP * self._scale
        cw = max(self.canvas.winfo_width(), 800)
        cx = self._offset[0] + cw / 2

        self.positions = {}

        # ── 3a: Buduj sloty dla każdego pokolenia ─────────────────────────────
        all_gen_sloty = {}   # gen -> [(oid, ...), ...]
        oid_to_gi    = {}    # oid -> (gen, slot_idx)

        for gen in sorted(pokolenia.keys()):
            ids = set(pokolenia[gen])
            odw = set()
            sorted_ids = sorted(ids, key=lambda o: (_klucz_rodzicielski(o), o))
            sloty = []
            for oid in sorted_ids:
                if oid in odw:
                    continue
                o = osoby.get(oid)
                m = o.malzonek_id if o else None
                if (m and m in ids and m not in odw
                        and glebokosc.get(m) == gen):
                    sloty.append((oid, m))
                    odw.add(oid); odw.add(m)
                else:
                    sloty.append((oid,))
                    odw.add(oid)
            all_gen_sloty[gen] = sloty
            for idx, slot in enumerate(sloty):
                for oid in slot:
                    oid_to_gi[oid] = (gen, idx)

        # ── 3b: Posortuj każde pokolenie wg kolejności rodzicielskich slotów ──
        for gen in sorted(all_gen_sloty.keys()):
            if gen == 0:
                continue
            sloty = all_gen_sloty[gen]

            def _pkey(idx, _s=sloty, _g=gen):
                pidxs = []
                for oid in _s[idx]:
                    o = osoby.get(oid)
                    for pid in (o.rodzic_ids if o else []):
                        if pid in oid_to_gi and oid_to_gi[pid][0] < _g:
                            pidxs.append(oid_to_gi[pid])
                return (tuple(sorted(set(pidxs))), idx)

            order = sorted(range(len(sloty)), key=_pkey)
            all_gen_sloty[gen] = [sloty[i] for i in order]
            for new_idx, slot in enumerate(all_gen_sloty[gen]):
                for oid in slot:
                    oid_to_gi[oid] = (gen, new_idx)

        # ── 3c: Oblicz footprint każdego slotu (bottom-up) ────────────────────
        # footprint(slot) = max(własna szerokość, suma footprintów bezpośrednich dzieci)
        fp = {}   # (gen, idx) -> required width

        min_gen = min(all_gen_sloty.keys())
        max_gen = max(all_gen_sloty.keys())

        for gen in range(max_gen, min_gen - 1, -1):
            for idx, slot in enumerate(all_gen_sloty[gen]):
                sw = (2 * bw + para_gap) if len(slot) == 2 else bw
                slot_ids = set(slot)
                if gen + 1 in all_gen_sloty:
                    # Zbierz UNIKALNE indeksy slotów dzieci w gen+1
                    child_idxs = sorted({
                        oid_to_gi[o.id][1]
                        for o in osoby.values()
                        if o.id in oid_to_gi
                        and oid_to_gi[o.id][0] == gen + 1
                        and any(p in slot_ids for p in o.rodzic_ids)
                    })
                    if child_idxs:
                        child_w = (sum(fp[(gen + 1, ci)] for ci in child_idxs)
                                   + (len(child_idxs) - 1) * rodzina_gap)
                        fp[(gen, idx)] = max(sw, child_w)
                    else:
                        fp[(gen, idx)] = sw
                else:
                    fp[(gen, idx)] = sw

        # ── 3d: Przypisz pozycje top-down ──────────────────────────────────────
        slot_cx = {}   # (gen, idx) -> center X canvasu

        for gen in sorted(all_gen_sloty.keys()):
            sloty = all_gen_sloty[gen]
            y = self._offset[1] + gen * (bh + vg)

            if gen == min_gen:
                # Pokolenie korzeniowe — wyśrodkuj wokół cx
                total_w = (sum(fp[(gen, i)] for i in range(len(sloty)))
                           + max(len(sloty) - 1, 0) * rodzina_gap)
                x = cx - total_w / 2
                for idx in range(len(sloty)):
                    slot_cx[(gen, idx)] = x + fp[(gen, idx)] / 2
                    x += fp[(gen, idx)] + rodzina_gap
            else:
                # Grupuj sloty wg klucza rodzicielskiego (slotów rodziców w gen-1)
                def _pslot_key(idx, _s=sloty, _g=gen):
                    pidxs = set()
                    for oid in _s[idx]:
                        o = osoby.get(oid)
                        for pid in (o.rodzic_ids if o else []):
                            if pid in oid_to_gi and oid_to_gi[pid][0] == _g - 1:
                                pidxs.add(oid_to_gi[pid][1])
                    return tuple(sorted(pidxs))

                groups = {}
                for idx in range(len(sloty)):
                    key = _pslot_key(idx)
                    groups.setdefault(key, []).append(idx)

                def _gcenter(key):
                    if not key:
                        return cx
                    return sum(slot_cx[(gen - 1, pi)] for pi in key) / len(key)

                # Posortuj grupy wg centrum rodzica (lewe → prawe)
                group_order = sorted(groups.keys(),
                                     key=lambda k: (_gcenter(k), k))

                # Wyznacz lewy brzeg grup, rozwiązując kolizje w prawo
                group_left = {}
                prev_right = None
                for key in group_order:
                    idxs = groups[key]
                    gw = (sum(fp[(gen, i)] for i in idxs)
                          + max(len(idxs) - 1, 0) * rodzina_gap)
                    ideal_left = _gcenter(key) - gw / 2
                    if prev_right is not None:
                        ideal_left = max(ideal_left, prev_right + rodzina_gap)
                    group_left[key] = ideal_left
                    prev_right = ideal_left + gw

                # Przypisz centra slotów
                for key in group_order:
                    x = group_left[key]
                    for idx in groups[key]:
                        slot_cx[(gen, idx)] = x + fp[(gen, idx)] / 2
                        x += fp[(gen, idx)] + rodzina_gap

            # Wyznacz pozycje pudełek z centrum slotu
            for idx, slot in enumerate(sloty):
                c  = slot_cx.get((gen, idx), cx)
                sw = (2 * bw + para_gap) if len(slot) == 2 else bw
                x  = c - sw / 2
                if len(slot) == 2:
                    self.positions[slot[0]] = (x, y)
                    self.positions[slot[1]] = (x + bw + para_gap, y)
                else:
                    self.positions[slot[0]] = (x, y)

        # Zastosuj ręczne przesunięcia (drag & drop) — przeliczone przez aktualną skalę
        for oid, (odx, ody) in self._custom_offsets.items():
            if oid in self.positions:
                px, py = self.positions[oid]
                self.positions[oid] = (px + odx * self._scale, py + ody * self._scale)

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

        # ── Linie rodzeństwa (zielone, przerywane) ────────────────────────────
        # Grupuj osoby wg frozenset rodziców — każda grupa to rodzeństwo
        grupy_rod = {}
        for o in self.baza.osoby.values():
            if o.id not in self.positions or not o.rodzic_ids:
                continue
            klucz = frozenset(o.rodzic_ids)
            grupy_rod.setdefault(klucz, []).append(o.id)

        for rodzenstwo in grupy_rod.values():
            widoczni = [oid for oid in rodzenstwo if oid in self.positions]
            if len(widoczni) < 2:
                continue
            widoczni.sort(key=lambda oid: self.positions[oid][0])
            mid_y = self.positions[widoczni[0]][1] + bh / 2
            x_lewy  = self.positions[widoczni[0]][0] + bw
            x_prawy = self.positions[widoczni[-1]][0]
            self.canvas.create_line(x_lewy, mid_y, x_prawy, mid_y,
                                    fill="#2e8b57", width=max(1, 1.2 * self._scale),
                                    dash=(5, 4))

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

        self._sep(f, 6, "Rodzice  (wybierz z listy lub wpisz Imię Nazwisko, potem Dodaj)")
        r_frame = tk.Frame(f, bg=PANEL)
        r_frame.grid(row=7, column=0, columnspan=3, sticky="ew", padx=4, pady=(0, 4))

        r_top = tk.Frame(r_frame, bg=PANEL)
        r_top.pack(fill="x", pady=(0, 2))
        self.cb_r_input = ttk.Combobox(r_top, values=self._choices(), font=self.f["body"], width=34)
        self.cb_r_input.pack(side="left", fill="x", expand=True, padx=(0, 4))

        def _dodaj_rodzica():
            val = self.cb_r_input.get().strip()
            if not val:
                return
            current = list(self.lb_rodzice.get(0, "end"))
            if len(current) >= 2:
                messagebox.showwarning("Limit", "Można dodać maksymalnie 2 rodziców.", parent=self)
                return
            if val in current:
                self.cb_r_input.set("")
                return
            self.lb_rodzice.insert("end", val)
            self.cb_r_input.set("")

        tk.Button(r_top, text="+ Dodaj", command=_dodaj_rodzica,
                  bg=GOLD_LT, fg=TEXT, font=self.f["small"], relief="flat",
                  padx=8, pady=3, cursor="hand2").pack(side="left")

        r_bot = tk.Frame(r_frame, bg=PANEL)
        r_bot.pack(fill="x")
        self.lb_rodzice = tk.Listbox(r_bot, font=self.f["body"], bg=CREAM, fg=TEXT,
                                     relief="flat", highlightthickness=1,
                                     highlightbackground=BORDER, height=2,
                                     exportselection=False, selectmode="single")
        r_vsb = ttk.Scrollbar(r_bot, orient="vertical", command=self.lb_rodzice.yview)
        self.lb_rodzice.configure(yscrollcommand=r_vsb.set)
        r_vsb.pack(side="right", fill="y")
        self.lb_rodzice.pack(side="left", fill="both", expand=True)

        def _usun_rodzica():
            sel = self.lb_rodzice.curselection()
            if sel:
                self.lb_rodzice.delete(sel[0])

        tk.Button(r_frame, text="✖ Usuń zaznaczonego", command=_usun_rodzica,
                  bg="#e0e0e0", fg=TEXT, font=self.f["small"], relief="flat",
                  padx=6, pady=2, cursor="hand2").pack(anchor="e", pady=(2, 0))

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
            values=[""] + [f"{o.pelne_imie} [{o.id}]" for o in
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
            values=[""] + [f"{o.pelne_imie} [{o.id}]" for o in
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
        self._sep(f, 15, "Małżonek / Małżonka  (wybierz z listy lub wpisz, potem Ustaw)")
        m_frame = tk.Frame(f, bg=PANEL)
        m_frame.grid(row=16, column=0, columnspan=3, sticky="ew", padx=4, pady=(0, 4))

        m_top = tk.Frame(m_frame, bg=PANEL)
        m_top.pack(fill="x", pady=(0, 2))
        self.cb_m_input = ttk.Combobox(m_top, values=self._choices(), font=self.f["body"], width=34)
        self.cb_m_input.pack(side="left", fill="x", expand=True, padx=(0, 4))

        def _ustaw_malzonka():
            val = self.cb_m_input.get().strip()
            if not val:
                return
            self.lb_malzonek.delete(0, "end")
            self.lb_malzonek.insert("end", val)
            self.cb_m_input.set("")

        def _usun_malzonka():
            self.lb_malzonek.delete(0, "end")

        tk.Button(m_top, text="Ustaw", command=_ustaw_malzonka,
                  bg=GOLD_LT, fg=TEXT, font=self.f["small"], relief="flat",
                  padx=8, pady=3, cursor="hand2").pack(side="left")
        tk.Button(m_top, text="Wyczyść", command=_usun_malzonka,
                  bg="#e0e0e0", fg=TEXT, font=self.f["small"], relief="flat",
                  padx=6, pady=3, cursor="hand2").pack(side="left", padx=(4, 0))

        m_bot = tk.Frame(m_frame, bg=PANEL)
        m_bot.pack(fill="x")
        self.lb_malzonek = tk.Listbox(m_bot, font=self.f["body"], bg=CREAM, fg=TEXT,
                                      relief="flat", highlightthickness=1,
                                      highlightbackground=BORDER, height=1,
                                      exportselection=False, selectmode="single")
        m_vsb = ttk.Scrollbar(m_bot, orient="vertical", command=self.lb_malzonek.yview)
        self.lb_malzonek.configure(yscrollcommand=m_vsb.set)
        m_vsb.pack(side="right", fill="y")
        self.lb_malzonek.pack(side="left", fill="both", expand=True)

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
        self.cb_odrz = tk.Checkbutton(f,
            text="Odrzucenie spadku (art. 1020 KC) — zstępni wchodzą w miejsce",
            variable=self.v_odrz,
            command=self._toggle_odrzucenie,
            bg=PANEL, font=self.f["body"]
        )
        self.cb_odrz.grid(row=25, column=0, columnspan=3, sticky="w", padx=4, pady=2)

        # ── Podstawa odrzucenia (widoczna tylko gdy odrzucono) ────────────────
        self._odrz_frame = tk.Frame(f, bg="#f0eeff", bd=1, relief="groove")
        self._odrz_frame.grid(row=26, column=0, columnspan=3, sticky="ew", padx=12, pady=(0, 4))
        self._odrz_frame.grid_remove()  # ukryty domyślnie

        tk.Label(self._odrz_frame, text="Odrzucono spadek na podstawie:",
                 font=self.f["bold"], bg="#f0eeff", fg=TEXT
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=8, pady=(6, 2))

        self.v_podstawa = tk.StringVar(value="")
        _PODSTAWY = [
            ("akta_n",             "Akta N"),
            ("oswiadczenie_sadowe", "Oświadczenie w toku postępowania sądowego"),
            ("akt_notarialny",      "Akt notarialny w aktach"),
            ("inne_akta",           "Inne akta"),
        ]
        self._odrz_txt_akta_n   = None
        self._odrz_txt_inne     = None

        for i, (val, label) in enumerate(_PODSTAWY):
            rb = tk.Radiobutton(self._odrz_frame, text=label, variable=self.v_podstawa,
                                value=val, bg="#f0eeff", font=self.f["body"],
                                command=self._toggle_podstawa_txt)
            rb.grid(row=i+1, column=0, sticky="w", padx=20, pady=1)

        # Textbox dla "Akta N"
        lbl_an = tk.Label(self._odrz_frame, text="Sygnatura / opis (Akta N):",
                          font=self.f["small"], bg="#f0eeff", fg=MUTED)
        lbl_an.grid(row=1, column=1, sticky="w", padx=(4, 4))
        self._odrz_txt_akta_n = tk.Entry(self._odrz_frame, font=self.f["body"],
                                          bg=CREAM, fg=TEXT, relief="flat",
                                          highlightthickness=1, highlightbackground=BORDER,
                                          width=28, state="disabled",
                                          disabledbackground="#e0e0e0")
        self._odrz_txt_akta_n.grid(row=2, column=1, sticky="ew", padx=(4, 8), pady=(0, 2))

        # Textbox dla "Inne akta"
        lbl_in = tk.Label(self._odrz_frame, text="Sygnatura / opis (Inne akta):",
                          font=self.f["small"], bg="#f0eeff", fg=MUTED)
        lbl_in.grid(row=4, column=1, sticky="w", padx=(4, 4))
        self._odrz_txt_inne = tk.Entry(self._odrz_frame, font=self.f["body"],
                                        bg=CREAM, fg=TEXT, relief="flat",
                                        highlightthickness=1, highlightbackground=BORDER,
                                        width=28, state="disabled",
                                        disabledbackground="#e0e0e0")
        self._odrz_txt_inne.grid(row=5, column=1, sticky="ew", padx=(4, 8), pady=(0, 6))

        self._odrz_frame.columnconfigure(1, weight=1)

        self.v_wydz = tk.BooleanVar()
        tk.Label(f,
            text="⚠ Wydziedziczenie (art. 1008 KC) — pozbawia wyłącznie ZACHOWKU,\n"
                 "    nie ma wpływu na dziedziczenie ustawowe. Odnotuj dla celów informacyjnych.",
            font=self.f["small"], bg="#fffbe6", fg="#7a5c00",
            justify="left", padx=6, pady=4
        ).grid(row=27, column=0, columnspan=3, sticky="ew", padx=4)

        tk.Checkbutton(f,
            text="Wydziedziczona/y (art. 1008 KC — tylko zachowek)",
            variable=self.v_wydz,
            bg=PANEL, font=self.f["body"]
        ).grid(row=28, column=0, columnspan=3, sticky="w", padx=4, pady=2)

        # ── Notatki (row 29–30) ───────────────────────────────────────────────
        self._sep(f, 29, "Notatki")
        self.e_notatki = tk.Text(f, height=3, font=self.f["body"],
                                  bg=CREAM, fg=TEXT, relief="flat",
                                  highlightthickness=1, highlightbackground=BORDER)
        self.e_notatki.grid(row=30, column=0, columnspan=3, sticky="ew", padx=4, pady=(4, 8))

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

    def _toggle_odrzucenie(self, *_):
        """Pokazuje/ukrywa sekcję podstawy odrzucenia i odblokuje checkboxy dokumentów."""
        if self.v_odrz.get():
            self._odrz_frame.grid()
        else:
            self._odrz_frame.grid_remove()
            self.v_podstawa.set("")
            # Wyczyść textboxy
            if self._odrz_txt_akta_n:
                self._odrz_txt_akta_n.config(state="normal")
                self._odrz_txt_akta_n.delete(0, "end")
                self._odrz_txt_akta_n.config(state="disabled")
            if self._odrz_txt_inne:
                self._odrz_txt_inne.config(state="normal")
                self._odrz_txt_inne.delete(0, "end")
                self._odrz_txt_inne.config(state="disabled")

    def _toggle_podstawa_txt(self, *_):
        """Włącza/wyłącza textboxy w zależności od wybranej podstawy."""
        val = self.v_podstawa.get()
        if self._odrz_txt_akta_n:
            if val == "akta_n":
                self._odrz_txt_akta_n.config(state="normal", disabledbackground="#e0e0e0")
            else:
                self._odrz_txt_akta_n.config(state="disabled")
        if self._odrz_txt_inne:
            if val == "inne_akta":
                self._odrz_txt_inne.config(state="normal", disabledbackground="#e0e0e0")
            else:
                self._odrz_txt_inne.config(state="disabled")

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
        self.v_odrz.set(o.odrzucila_spadek)
        if o.odrzucila_spadek:
            self._toggle_odrzucenie()
            self.v_podstawa.set(o.podstawa_odrzucenia)
            self._toggle_podstawa_txt()
            tekst = o.podstawa_odrzucenia_tekst or ""
            if o.podstawa_odrzucenia == "akta_n" and self._odrz_txt_akta_n:
                self._odrz_txt_akta_n.config(state="normal")
                self._odrz_txt_akta_n.insert(0, tekst)
            elif o.podstawa_odrzucenia == "inne_akta" and self._odrz_txt_inne:
                self._odrz_txt_inne.config(state="normal")
                self._odrz_txt_inne.insert(0, tekst)

        def find_c(rid):
            for c in self._choices():
                if f"[{rid}]" in c:
                    return c
            return ""

        for rid in o.rodzic_ids[:2]:
            c = find_c(rid)
            if c:
                self.lb_rodzice.insert("end", c)

        if o.malzonek_id:
            c = find_c(o.malzonek_id)
            if c:
                self.lb_malzonek.insert("end", c)

        # Rodzeństwo — deduplikacja przez set (osoba z 2 wspólnych rodziców != 2x)
        if o.rodzic_ids:
            juz_dodane = set()
            for pid in o.rodzic_ids:
                for dziecko in self.baza.dzieci(pid):
                    identifier = f"{dziecko.pelne_imie} [{dziecko.id}]"
                    if dziecko.id != o.id and identifier not in juz_dodane:
                        juz_dodane.add(identifier)
                        self.lb_rodz.insert("end", identifier)

        # Dzieci
        for dziecko in self.baza.dzieci(o.id):
            self.lb_dzieci.insert("end", f"{dziecko.pelne_imie} [{dziecko.id}]")

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

        rodzic_ids = []
        for rval in self.lb_rodzice.get(0, "end"):
            rid = self._resolve(rval.strip())
            if rid and rid not in rodzic_ids:
                rodzic_ids.append(rid)
        malzonek_id = None
        if self.lb_malzonek.size() > 0:
            malzonek_id = self._resolve(self.lb_malzonek.get(0).strip()) or None

        # ── Walidacja prawna: zakaz niedozwolonych związków (KRiO art. 14 §1) ─
        if malzonek_id:
            osoba_id_do_spr = self.osoba.id if self.osoba else None
            blad_zwiazku = self.baza.sprawdz_niedozwolony_zwiazek(
                osoba_id_do_spr, malzonek_id,
                extra_rodzice_osoby=rodzic_ids if not self.osoba else None
            )
            if blad_zwiazku:
                messagebox.showerror("Niedozwolony związek", blad_zwiazku, parent=self)
                return

        notatki = self.e_notatki.get("1.0", "end").strip()

        # Odczytaj podstawę odrzucenia i tekst uzupełniający
        podstawa = self.v_podstawa.get() if self.v_odrz.get() else ""
        if podstawa == "akta_n" and self._odrz_txt_akta_n:
            podstawa_tekst = self._odrz_txt_akta_n.get().strip()
        elif podstawa == "inne_akta" and self._odrz_txt_inne:
            podstawa_tekst = self._odrz_txt_inne.get().strip()
        else:
            podstawa_tekst = ""

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
            o.podstawa_odrzucenia = podstawa
            o.podstawa_odrzucenia_tekst = podstawa_tekst
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
                podstawa_odrzucenia=podstawa,
                podstawa_odrzucenia_tekst=podstawa_tekst,
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
        # Zbierz wpisy z listboxa i zmapuj na obiekty Osoba przez _resolve
        nazwy_w_liscie = list(self.lb_rodz.get(0, "end"))
        for nazwa in nazwy_w_liscie:
            nazwa = nazwa.strip()
            if not nazwa:
                continue
            rodz_id = self._resolve(nazwa)
            rodz_obj = self.baza.osoby.get(rodz_id) if rodz_id else None
            if not rodz_obj:
                continue

            # Sprzężenie obustronne: unia rodziców obu osób
            for pid in list(ja.rodzic_ids):
                if pid not in rodz_obj.rodzic_ids:
                    rodz_obj.rodzic_ids.append(pid)
            for pid in list(rodz_obj.rodzic_ids):
                if pid not in ja.rodzic_ids:
                    ja.rodzic_ids.append(pid)

        # ── Sprzężenie dzieci ─────────────────────────────────────────────
        for nazwa in self.lb_dzieci.get(0, "end"):
            nazwa = nazwa.strip()
            if not nazwa:
                continue
            dz_id = self._resolve(nazwa)
            dz_obj = self.baza.osoby.get(dz_id) if dz_id else None
            if not dz_obj:
                continue
            if ja.id not in dz_obj.rodzic_ids:
                dz_obj.rodzic_ids.append(ja.id)

        self.destroy()
