"""
main.py - Punkt wejscia aplikacji Kalkulator Prawniczy.
Autor: Dominik Mieczkowski-Wilga + przyjaciele
"""

import os, sys, subprocess

def _ukryj_pliki_pomocnicze():
    """Ukrywa pliki pomocnicze PyInstallera obok EXE (tylko Windows)."""
    if sys.platform != "win32":
        return
    try:
        folder = os.path.dirname(os.path.abspath(sys.executable))
        # PyInstaller 6.x — podfolder _internal
        internal = os.path.join(folder, "_internal")
        if os.path.isdir(internal):
            subprocess.call(
                ["attrib", "+h", internal],
                creationflags=0x08000000)  # CREATE_NO_WINDOW
            return
        # Starszy PyInstaller — pliki bezpośrednio obok EXE
        exe_name = os.path.basename(sys.executable).lower()
        for name in os.listdir(folder):
            if name.lower() == exe_name:
                continue
            subprocess.call(
                ["attrib", "+h", os.path.join(folder, name)],
                creationflags=0x08000000)
    except Exception:
        pass  # błąd uprawnień itp. — ignoruj, nie blokuj startu

_ukryj_pliki_pomocnicze()

import sys
import os


def _pokaz_blad(tytul, tresc):
    """Wyswietla okno bledu przez tkinter nawet jesli reszta aplikacji nie dziala."""
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(tytul, tresc)
        root.destroy()
    except Exception:
        pass


def _ensure_deps():
    """Instaluje brakujace zaleznosci przy pierwszym uruchomieniu."""
    try:
        from dateutil.relativedelta import relativedelta  # noqa: F401
    except ImportError:
        try:
            import subprocess
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "python-dateutil", "--quiet"],
                timeout=60
            )
        except Exception as e:
            _pokaz_blad(
                "Brak biblioteki",
                "Nie mozna zainstalowac python-dateutil.\n\n"
                "Uruchom recznie w terminalu:\n"
                "  pip install python-dateutil\n\n"
                f"Blad: {e}"
            )
            sys.exit(1)


def _ustal_katalog():
    """
    Ustawia sys.path tak, zeby modul app.py i inne byly widoczne.
    Potrzebne gdy EXE uruchamiany jest z innego katalogu roboczego.
    """
    if getattr(sys, "frozen", False):
        # Tryb PyInstaller EXE - modul sa w katalogu _MEIPASS (--onefile)
        # lub obok EXE (--onedir)
        katalog = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    else:
        # Tryb skryptowy - katalog tego pliku
        katalog = os.path.dirname(os.path.abspath(__file__))

    if katalog not in sys.path:
        sys.path.insert(0, katalog)

    # Dodatkowo dodaj katalog EXE (przydatne przy --onedir)
    exe_dir = os.path.dirname(os.path.abspath(sys.executable))
    if exe_dir not in sys.path:
        sys.path.insert(0, exe_dir)


def main():
    _ustal_katalog()
    _ensure_deps()

    try:
        from app import App
    except ImportError as e:
        _pokaz_blad(
            "Blad importu",
            f"Nie mozna zaladowac modulu aplikacji.\n\n{e}\n\n"
            "Upewnij sie, ze wszystkie pliki .py sa w tym samym katalogu co EXE."
        )
        sys.exit(1)
    except Exception as e:
        _pokaz_blad("Blad krytyczny", f"Nieoczekiwany blad podczas startu:\n\n{e}")
        sys.exit(1)

    try:
        app = App()
        app.mainloop()
    except Exception as e:
        _pokaz_blad("Blad aplikacji", f"Aplikacja zakonczyla sie bledem:\n\n{e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
