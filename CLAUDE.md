# NetInfo – kontekst projektu dla Claude Code

## Co to jest
Desktopowa aplikacja do przeglądania interfejsów sieciowych w Windows 10/11.
Stos: Python 3 + CustomTkinter + psutil. Budowanie: `build.bat` → `dist\NetInfo.exe` (~19 MB, jeden plik).

## Architektura
- `main.py` – punkt wejścia
- `core/network.py` – zbiera dane przez PowerShell `Get-Net*` cmdlets (zwracają JSON, niezależne od języka Windows)
- `ui/app.py` – okno główne, sidebar nawigacyjny, rejestr modułów (`MODULE_REGISTRY`, `NAV_ITEMS`)
- `ui/modules/network_overview.py` – jedyny aktywny moduł; pozostałe 3 to placeholdery

## Jak dodać nowy moduł
1. Utwórz `ui/modules/nowy.py` z klasą dziedziczącą `ctk.CTkFrame`
2. Zarejestruj w `MODULE_REGISTRY` i `NAV_ITEMS` w `ui/app.py` (ustaw `available=True`)

## Pułapki CustomTkinter (już naprawione, nie powtarzaj)
- `hover_color="transparent"` w CTkButton → ValueError. Używaj koloru tła.
- `border_color=("transparent","transparent")` w CTkFrame → ValueError. Używaj `border_width=0`.

## Stan
Moduł przeglądu sieci: gotowy i przetestowany.
Planowane moduły: Skanowanie sieci, Monitor ruchu, Sprawdz porty.
