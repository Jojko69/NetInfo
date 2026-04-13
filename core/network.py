"""
core/network.py
===============
Moduł zbierania danych o interfejsach sieciowych w systemie Windows.

Strategia pozyskiwania danych:
  - PowerShell Get-Net* cmdlets  → główne źródło (locale-niezależne, ustrukturyzowane JSON)
  - psutil                       → dane uzupełniające (MTU, flagi)

Wszystkie wywołania PowerShell mają timeout 10 s i ukryte okno konsoli.
"""

import json
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import psutil


# ---------------------------------------------------------------------------
# Struktura danych interfejsu
# ---------------------------------------------------------------------------

@dataclass
class InterfaceInfo:
    """Kompletne informacje o jednym interfejsie sieciowym."""

    name: str             # Nazwa systemowa, np. "Ethernet", "Wi-Fi"
    description: str      # Opis sprzętowy, np. "Intel(R) Ethernet Connection"
    mac: str              # Adres MAC, np. "00:1A:2B:3C:4D:5E"
    iface_type: str       # Typ: Ethernet | Wi-Fi | VPN | Wirtualny | Loopback | Inne
    status: str           # Wyświetlany status: "Aktywny" / "Nieaktywny"
    is_active: bool       # Czy link jest aktywny (UP)
    is_default: bool      # Czy posiada domyślną bramę (główny interfejs)

    ipv4: Optional[str] = None          # np. "192.168.1.100"
    ipv4_mask: str = ""                 # np. "255.255.255.0"
    ipv4_prefix: int = 0               # np. 24
    ipv6: Optional[str] = None          # np. "2001:db8::1"
    ipv6_prefix: int = 0

    gateway: Optional[str] = None      # np. "192.168.1.1"
    dns_servers: List[str] = field(default_factory=list)

    speed_mbps: int = 0                # Prędkość łącza w Mb/s
    mtu: int = 0                       # Maximum Transmission Unit (maks. rozmiar pakietu)
    dhcp_enabled: bool = False         # Czy adres IP jest przydzielany automatycznie (DHCP)


# ---------------------------------------------------------------------------
# Narzędzia pomocnicze
# ---------------------------------------------------------------------------

def _powershell(cmd: str) -> Optional[str]:
    """
    Uruchamia polecenie PowerShell i zwraca stdout jako tekst UTF-8.
    Zwraca None przy błędzie lub timeout.
    """
    flags = 0
    if sys.platform == "win32":
        # CREATE_NO_WINDOW (0x08000000) – ukrywa okno konsoli przy starcie z .exe
        flags = 0x08000000

    try:
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy", "Bypass",
                "-Command", cmd,
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
            creationflags=flags,
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except Exception:
        return None


def _prefix_to_mask(prefix: int) -> str:
    """Zamienia długość prefiksu (np. 24) na maskę podsieci (np. 255.255.255.0)."""
    if not 0 <= prefix <= 32:
        return ""
    bits = (0xFFFFFFFF << (32 - prefix)) & 0xFFFFFFFF
    return ".".join(str((bits >> shift) & 0xFF) for shift in (24, 16, 8, 0))


def _classify_interface(description: str, name: str, media_type: str = "") -> str:
    """Określa typ interfejsu na podstawie opisu, nazwy i typu mediów."""
    d = description.lower()
    n = name.lower()
    m = media_type.lower()

    if "loopback" in d or "loopback" in n:
        return "Loopback"
    if any(x in d or x in n for x in ("wi-fi", "wireless", "wifi", "802.11")) or "native 802.11" in m:
        return "Wi-Fi"
    if any(x in d or x in n for x in ("vpn", "tunnel", "tap-windows", "wireguard", "openvpn")):
        return "VPN"
    if "bluetooth" in d or "bluetooth" in n:
        return "Bluetooth"
    if any(x in d for x in ("vmware", "virtualbox", "hyper-v", "virtual", "miniport")):
        return "Wirtualny"
    if "ethernet" in d or "ethernet" in n or "local area" in d:
        return "Ethernet"
    return "Inne"


def _parse_speed(raw: str) -> int:
    """
    Konwertuje tekstową prędkość (np. '1 Gbps', '100 Mbps') na liczbę Mb/s.
    Get-NetAdapter zwraca LinkSpeed jako napis.
    """
    if not raw:
        return 0
    raw = str(raw).strip()
    try:
        if "Gbps" in raw:
            return int(float(raw.replace("Gbps", "").strip()) * 1000)
        if "Mbps" in raw:
            return int(float(raw.replace("Mbps", "").strip()))
        if "Kbps" in raw:
            return max(1, int(float(raw.replace("Kbps", "").strip()) // 1000))
        # Surowa wartość w bps (np. z WMI)
        val = int("".join(c for c in raw if c.isdigit()))
        return val // 1_000_000
    except (ValueError, TypeError):
        return 0


def _fmt_mac(mac: str) -> str:
    """Normalizuje adres MAC: zamienia myślniki na dwukropki i używa wielkich liter."""
    if not mac:
        return "Brak"
    return mac.replace("-", ":").upper()


def _load_json(raw: Optional[str]) -> list:
    """
    Parsuje JSON zwrócony przez PowerShell.
    PowerShell zwraca obiekt (dict) gdy jest 1 wynik, lub tablicę (list) gdy więcej.
    Zawsze zwraca listę.
    """
    if not raw:
        return []
    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else [data]
    except (json.JSONDecodeError, TypeError):
        return []


# ---------------------------------------------------------------------------
# Główna funkcja zbierania danych
# ---------------------------------------------------------------------------

def get_network_interfaces() -> List[InterfaceInfo]:
    """
    Zbiera i zwraca listę wszystkich interfejsów sieciowych z pełnymi danymi.

    Kolejność na liście: najpierw interfejs z domyślną bramą (główny), potem
    pozostałe aktywne, na końcu nieaktywne.
    """
    interfaces: Dict[str, InterfaceInfo] = {}

    # ------------------------------------------------------------------
    # Krok 1: Podstawowe dane adapterów (Get-NetAdapter)
    # ------------------------------------------------------------------
    raw = _powershell(
        "Get-NetAdapter | "
        "Select-Object Name,InterfaceDescription,MacAddress,Status,LinkSpeed,MediaType | "
        "ConvertTo-Json -Compress"
    )
    for adapter in _load_json(raw):
        name = adapter.get("Name", "")
        if not name:
            continue
        is_up = str(adapter.get("Status", "")).lower() == "up"
        iface = InterfaceInfo(
            name=name,
            description=adapter.get("InterfaceDescription", name),
            mac=_fmt_mac(adapter.get("MacAddress", "")),
            iface_type=_classify_interface(
                adapter.get("InterfaceDescription", ""),
                name,
                adapter.get("MediaType", ""),
            ),
            status="Aktywny" if is_up else "Nieaktywny",
            is_active=is_up,
            is_default=False,
            speed_mbps=_parse_speed(adapter.get("LinkSpeed", "")),
        )
        interfaces[name] = iface

    # ------------------------------------------------------------------
    # Krok 2: Adresy IP (Get-NetIPAddress)
    # ------------------------------------------------------------------
    raw = _powershell(
        "Get-NetIPAddress | "
        "Select-Object InterfaceAlias,AddressFamily,IPAddress,PrefixLength,PrefixOrigin | "
        "ConvertTo-Json -Compress"
    )
    for addr in _load_json(raw):
        iface_name = addr.get("InterfaceAlias", "")
        if iface_name not in interfaces:
            continue

        family = addr.get("AddressFamily", 0)   # 2=IPv4, 23=IPv6
        ip = addr.get("IPAddress", "")
        prefix = addr.get("PrefixLength", 0)
        origin = addr.get("PrefixOrigin", "")
        iface = interfaces[iface_name]

        if family == 2:  # IPv4
            # Pomiń adresy link-local 169.254.x.x jeśli mamy już normalny adres
            if ip.startswith("169.254") and iface.ipv4 is not None:
                continue
            iface.ipv4 = ip
            iface.ipv4_prefix = prefix
            iface.ipv4_mask = _prefix_to_mask(prefix)
            iface.dhcp_enabled = (origin == "Dhcp")

        elif family == 23:  # IPv6
            # Preferuj adresy globalne (nie link-local fe80::)
            if ip.lower().startswith("fe80") and iface.ipv6 is not None:
                continue
            iface.ipv6 = ip
            iface.ipv6_prefix = prefix

    # ------------------------------------------------------------------
    # Krok 3: Domyślna brama (Get-NetRoute)
    # ------------------------------------------------------------------
    raw = _powershell(
        "Get-NetRoute -DestinationPrefix '0.0.0.0/0' -ErrorAction SilentlyContinue | "
        "Select-Object InterfaceAlias,NextHop,RouteMetric | "
        "ConvertTo-Json -Compress"
    )
    for route in _load_json(raw):
        iface_name = route.get("InterfaceAlias", "")
        next_hop = route.get("NextHop", "")
        if next_hop and next_hop not in ("0.0.0.0", "") and iface_name in interfaces:
            interfaces[iface_name].gateway = next_hop
            interfaces[iface_name].is_default = True

    # ------------------------------------------------------------------
    # Krok 4: Serwery DNS (Get-DnsClientServerAddress)
    # ------------------------------------------------------------------
    raw = _powershell(
        "Get-DnsClientServerAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue | "
        "Select-Object InterfaceAlias,ServerAddresses | "
        "ConvertTo-Json -Compress"
    )
    for entry in _load_json(raw):
        iface_name = entry.get("InterfaceAlias", "")
        if iface_name not in interfaces:
            continue
        servers = entry.get("ServerAddresses", [])
        if isinstance(servers, str):
            servers = [servers]
        interfaces[iface_name].dns_servers = [s for s in servers if s]

    # ------------------------------------------------------------------
    # Krok 5: MTU i DHCP (Get-NetIPInterface) + psutil jako backup
    # ------------------------------------------------------------------
    raw = _powershell(
        "Get-NetIPInterface -AddressFamily IPv4 -ErrorAction SilentlyContinue | "
        "Select-Object InterfaceAlias,NlMtu,Dhcp | "
        "ConvertTo-Json -Compress"
    )
    for entry in _load_json(raw):
        iface_name = entry.get("InterfaceAlias", "")
        if iface_name not in interfaces:
            continue
        mtu = entry.get("NlMtu", 0)
        if mtu and int(mtu) > 0:
            interfaces[iface_name].mtu = int(mtu)
        dhcp = str(entry.get("Dhcp", "")).lower()
        if dhcp == "enabled":
            interfaces[iface_name].dhcp_enabled = True

    # Uzupełnij brakujące MTU z psutil
    try:
        for iface_name, stats in psutil.net_if_stats().items():
            if iface_name in interfaces and interfaces[iface_name].mtu == 0:
                interfaces[iface_name].mtu = stats.mtu
    except Exception:
        pass

    # ------------------------------------------------------------------
    # Sortowanie: domyślny interfejs na górze → aktywne → nieaktywne
    # ------------------------------------------------------------------
    result = sorted(
        interfaces.values(),
        key=lambda x: (not x.is_default, not x.is_active, x.name.lower()),
    )
    return result
