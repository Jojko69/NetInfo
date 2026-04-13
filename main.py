"""
main.py
=======
Punkt wejścia aplikacji NetInfo.

Uruchamianie:
  python main.py                 (tryb deweloperski)
  NetInfo.exe                    (po zbudowaniu przez PyInstaller)
"""

import os
import sys


def _fix_pyinstaller_path():
    """
    PyInstaller podczas startu rozpakowuje pliki do katalogu tymczasowego
    (_MEIPASS). Ta funkcja zapewnia, że import pakietów działa poprawnie
    zarówno podczas normalnego uruchomienia, jak i z pliku .exe.
    """
    if getattr(sys, "frozen", False):
        # Uruchomienie z pliku .exe – ustaw ścieżkę bazy na katalog .exe
        base_dir = os.path.dirname(sys.executable)
    else:
        # Uruchomienie ze źródła – katalog tego pliku
        base_dir = os.path.dirname(os.path.abspath(__file__))

    if base_dir not in sys.path:
        sys.path.insert(0, base_dir)


if __name__ == "__main__":
    _fix_pyinstaller_path()

    # Import tutaj (po korekcie ścieżek)
    from ui.app import NetInfoApp

    app = NetInfoApp()
    app.mainloop()
