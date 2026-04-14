# NetInfo

Desktopowa aplikacja sieciowa dla **Windows 10 i Windows 11**, napisana w Pythonie z interfejsem CustomTkinter.

Po uruchomieniu automatycznie wykrywa wszystkie interfejsy sieciowe w systemie i prezentuje ich pełne dane w przejrzystym, nowoczesnym interfejsie z ciemnym motywem.

---

## Funkcjonalności

### Przegląd sieci
- Automatyczne wykrywanie wszystkich interfejsów (Ethernet, Wi-Fi, VPN, Wirtualne, Loopback)
- Wyróżnienie aktywnego interfejsu z domyślną bramą (główne połączenie)
- Dla każdego interfejsu: IPv4/IPv6, maska podsieci, brama, DNS, MAC, typ, status, prędkość łącza, MTU, DHCP
- Przycisk **Odśwież** – ponowne skanowanie bez restartu

### Skanowanie sieci
- Czterofazowe wykrywanie hostów: ICMP Ping → ARP (MAC) → skanowanie portów TCP → Reverse DNS
- Obsługuje notację CIDR (`192.168.1.0/24`) i zakresy IP (`192.168.1.1-254`)
- Wyniki wyświetlane w czasie rzeczywistym podczas skanowania
- Opcjonalne skanowanie 18 popularnych portów TCP (SSH, HTTP, RDP, SMB...)
- Regulacja timeout pinga i timeout portów (suwaki)
- Przycisk **Stop** – przerwanie skanowania w dowolnym momencie

### Informacje
- Baza wiedzy o 18 portach TCP/UDP z opisami i przykładami aplikacji
- 6 kategorii: Web, Zdalne zarządzanie, Poczta, Sieć/Windows, Transfer plików, Bazy danych

### Ogólne
- Przełącznik **ciemny / jasny motyw**
- Nawigacja boczna z gotową architekturą dla kolejnych modułów

---

## Uruchomienie

### Ze źródła (tryb deweloperski)

Wymagany Python 3.10 lub nowszy.

```bash
pip install -r requirements.txt
python main.py
```

### Plik wykonywalny `.exe`

```bash
build.bat
```

Wynik: `dist\NetInfo.exe` – jeden plik (~19 MB), działa bez instalacji Pythona ani żadnych dodatkowych zależności.

---

## Struktura projektu

```
NetInfo/
├── main.py                        # Punkt wejścia aplikacji
├── requirements.txt               # Zależności Pythona
├── build.bat                      # Skrypt budowania .exe (PyInstaller)
│
├── core/
│   ├── network.py                 # Logika sieciowa: PowerShell + psutil
│   │                              # Klasa InterfaceInfo (model danych)
│   └── scanner.py                 # Silnik skanowania sieci
│                                  # Ping-sweep, ARP, porty TCP, reverse DNS
│
└── ui/
    ├── app.py                     # Główne okno, sidebar, rejestr modułów
    └── modules/
        ├── network_overview.py    # Moduł "Przegląd sieci"
        ├── network_scan.py        # Moduł "Skanowanie sieci"
        └── info_reference.py      # Moduł "Informacje" (baza portów TCP/UDP)
```

---

## Jak dodać nowy moduł

Architektura jest zaprojektowana tak, by dodanie nowego panelu (np. Ping, Skanowanie sieci, Monitor ruchu) wymagało minimalnych zmian.

**Krok 1** – utwórz plik `ui/modules/nowy_modul.py`:

```python
import customtkinter as ctk

class NowyModul(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        # Twój interfejs tutaj
```

**Krok 2** – zarejestruj w `ui/app.py`:

```python
# Import na górze pliku
from ui.modules.nowy_modul import NowyModul

# Dodaj do słownika MODULE_REGISTRY
MODULE_REGISTRY = {
    "network": NetworkOverviewModule,
    "nowy":    NowyModul,            # <-- dodaj
}

# Dodaj do listy NAV_ITEMS (available=True aktywuje przycisk)
NAV_ITEMS = [
    ("network", "Przeglad sieci", True),
    ("nowy",    "Nowy modul",     True),   # <-- dodaj
]
```

---

## Technologie

| Biblioteka | Zastosowanie |
|---|---|
| [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) | Nowoczesny interfejs graficzny (dark/light mode) |
| [psutil](https://github.com/giampaolo/psutil) | Uzupełniające dane o interfejsach (MTU, flagi) |
| PowerShell `Get-Net*` | Główne źródło danych sieciowych (locale-niezależne) |
| [PyInstaller](https://pyinstaller.org) | Budowanie pojedynczego pliku `.exe` |

Dane sieciowe pobierane są przez polecenia PowerShell (`Get-NetAdapter`, `Get-NetIPAddress`, `Get-NetRoute`, `Get-DnsClientServerAddress`, `Get-NetIPInterface`), które zwracają ustrukturyzowany JSON – niezależnie od języka systemu Windows.

---

## Wymagania systemowe

- Windows 10 lub Windows 11
- Python 3.10+ *(tylko przy uruchamianiu ze źródła)*
- PowerShell 5.1+ *(wbudowany w Windows 10/11)*

---

## Planowane moduły

- [x] Skanowanie sieci (host discovery, ICMP + ARP + TCP ports + DNS)
- [ ] Monitor ruchu sieciowego
- [ ] Sprawdzanie portów (port checker)
- [ ] Ping / Traceroute

---

## Licencja

MIT
