# NetInfo – kontekst projektu dla Claude Code

## Co to jest
Desktopowa aplikacja sieciowa dla Windows 10/11.
Stos: Python 3 + CustomTkinter + psutil. Build: `build.bat` → `dist\NetInfo.exe` (~19 MB, jeden plik).

## Architektura
- `main.py` – punkt wejścia (zawiera `_fix_pyinstaller_path()` dla ścieżek w exe)
- `core/network.py` – dane interfejsów przez PowerShell `Get-Net*` cmdlets (JSON, niezależne od języka Windows)
- `core/scanner.py` – silnik skanowania: ICMP → ARP → TCP ports → DNS (4 fazy), model `ScanResult`
- `ui/app.py` – okno główne, sidebar, rejestr modułów (`MODULE_REGISTRY`, `NAV_ITEMS`)
- `ui/modules/network_overview.py` – przegląd interfejsów sieciowych
- `ui/modules/network_scan.py` – skanowanie sieci (CIDR/zakres, wyniki real-time, stop)
- `ui/modules/info_reference.py` – baza portów TCP/UDP (statyczna, bez logiki sieciowej)

## Jak dodać nowy moduł
1. Utwórz `ui/modules/nowy.py` z klasą dziedziczącą `ctk.CTkFrame`
2. Zarejestruj w `MODULE_REGISTRY` i `NAV_ITEMS` w `ui/app.py` (ustaw `available=True`)

## Pułapki CustomTkinter (nie powtarzaj)
- `hover_color="transparent"` w CTkButton → ValueError. Używaj koloru tła.
- `border_color=("transparent","transparent")` w CTkFrame → ValueError. Używaj `border_width=0`.

## Build
- `build.bat` wywołuje `python -m PyInstaller` (nie `pyinstaller` bezpośrednio — scripts/ może nie być w PATH)
- Nie dodawaj `--hidden-import "PIL"` — Pillow nie jest używana

## Stan
Trzy moduły gotowe: Przegląd sieci, Skanowanie sieci, Informacje.
Planowane: Monitor ruchu, Ping/Traceroute.
