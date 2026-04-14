"""
core/scanner.py
===============
Silnik skanowania sieci dla aplikacji NetInfo.

Cztereetapowe wykrywanie urządzeń:
  Faza 1 – ICMP Ping (równoległy)     → czy host żyje + czas odpowiedzi
  Faza 2 – ARP cache                  → adres MAC (tylko sieć lokalna L2)
  Faza 3 – Skanowanie portów TCP      → popularne porty (opcjonalne)
  Faza 4 – Reverse DNS                → nazwa hosta

Dlaczego taka kolejność:
  - Ping-sweep zapełnia tablicę ARP systemu Windows automatycznie
  - Jedno wywołanie "arp -a" po sweep'ie daje MAC dla wszystkich hostów
  - Porty skanujemy przed DNS – DNS jest najwolniejszy, robimy go na końcu
  - DNS wykonujemy równolegle by zminimalizować czas

Ograniczenia:
  - Hosty z wyłączonym ICMP (np. niektóre firewalle) mogą nie być wykryte
  - MAC jest dostępny tylko dla hostów w tej samej sieci L2
"""

import ipaddress
import queue
import re
import socket
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Stałe
# ---------------------------------------------------------------------------

# Flaga ukrywająca okno konsoli przy wywołaniach subprocess na Windows
_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0

# Maksymalny dozwolony zakres skanowania
MAX_HOSTS  = 65534   # /16
WARN_HOSTS = 4094    # /20 – ostrzeżenie o długim czasie

# ---------------------------------------------------------------------------
# Popularne porty TCP do skanowania (Faza 3 – opcjonalna)
# ---------------------------------------------------------------------------
# Słownik: numer_portu → skrócona_nazwa_usługi
COMMON_PORTS: Dict[int, str] = {
    21:   "FTP",
    22:   "SSH",
    23:   "Telnet",
    25:   "SMTP",
    53:   "DNS",
    80:   "HTTP",
    110:  "POP3",
    135:  "RPC",
    139:  "NetBIOS",
    143:  "IMAP",
    443:  "HTTPS",
    445:  "SMB",
    1433: "MSSQL",
    3306: "MySQL",
    3389: "RDP",
    5900: "VNC",
    8080: "HTTP-Alt",
    8443: "HTTPS-Alt",
}


# ---------------------------------------------------------------------------
# Model danych
# ---------------------------------------------------------------------------

@dataclass
class ScanResult:
    """Kompletne dane o jednym wykrytym hoście."""
    ip: str
    hostname: str = "Nieznany"
    mac: str = "Brak"
    response_ms: float = -1
    is_alive: bool = False
    open_ports: List[int] = field(default_factory=list)  # numery otwartych portów TCP


# ---------------------------------------------------------------------------
# Parsowanie zakresu
# ---------------------------------------------------------------------------

def parse_targets(text: str) -> Tuple[List[str], str]:
    """
    Zamienia wejście użytkownika na listę adresów IP.

    Obsługiwane formaty:
      192.168.1.0/24           – notacja CIDR
      192.168.1.1-192.168.1.254 – pełny zakres
      192.168.1.1-254          – skrócony zakres (ostatni oktet)
      192.168.1.1              – pojedynczy host

    Zwraca: (lista_IP, komunikat_błędu)
    Przy sukcesie komunikat_błędu jest pustym stringiem.
    """
    text = text.strip()
    if not text:
        return [], "Podaj adres sieci lub zakres IP."

    try:
        if "/" in text:
            # Notacja CIDR
            network = ipaddress.ip_network(text, strict=False)
            hosts = [str(ip) for ip in network.hosts()]
            if not hosts:
                return [], "Sieć nie zawiera adresów hostów (maska /31 lub /32)."
            return hosts, ""

        elif "-" in text:
            # Zakres: pełny lub skrócony
            left, right = text.split("-", 1)
            start_str = left.strip()
            end_str = right.strip()

            # Skrócony zapis: 192.168.1.1-254  →  192.168.1.1-192.168.1.254
            if "." not in end_str:
                prefix = ".".join(start_str.split(".")[:-1])
                end_str = f"{prefix}.{end_str}"

            start = int(ipaddress.ip_address(start_str))
            end = int(ipaddress.ip_address(end_str))

            if start > end:
                return [], "Adres początkowy jest większy od końcowego."

            return [str(ipaddress.ip_address(i)) for i in range(start, end + 1)], ""

        else:
            # Pojedynczy adres IP – tylko walidacja
            ipaddress.ip_address(text)
            return [text], ""

    except ValueError as exc:
        return [], f"Nieprawidłowy adres: {exc}"


def validate_target_size(count: int) -> Optional[str]:
    """
    Sprawdza czy liczba hostów mieści się w rozsądnych granicach.
    Zwraca None (OK), ostrzeżenie lub komunikat błędu.
    """
    if count > MAX_HOSTS:
        return f"error:Zakres {count:,} hostów przekracza maksimum ({MAX_HOSTS:,}). Użyj maski /16 lub większej."
    if count > WARN_HOSTS:
        return f"warn:Zakres {count:,} hostów może wymagać kilku minut skanowania. Kontynuować?"
    return None


# ---------------------------------------------------------------------------
# Faza 1 – ICMP Ping
# ---------------------------------------------------------------------------

def ping_host(ip: str, timeout_ms: int = 500) -> Tuple[bool, float]:
    """
    Wysyła jeden pakiet ICMP ping do podanego adresu IP.
    Zwraca (True, czas_ms) jeśli host odpowiedział, (False, -1) jeśli nie.

    Obsługuje polski i angielski Windows (różne komunikaty w stdout).
    """
    try:
        proc = subprocess.run(
            ["ping", "-n", "1", "-w", str(timeout_ms), ip],
            capture_output=True,
            text=True,
            encoding="cp852",
            errors="replace",
            timeout=(timeout_ms / 1000) + 2.0,
            creationflags=_NO_WINDOW,
        )
        if proc.returncode != 0:
            return False, -1

        # Szukaj czasu: "czas=5ms", "time=5ms", "czas<1ms", "time<1ms"
        match = re.search(r'(?:czas|time)[=<](\d+)', proc.stdout, re.IGNORECASE)
        ms = float(match.group(1)) if match else 0.5
        return True, ms

    except Exception:
        return False, -1


# ---------------------------------------------------------------------------
# Faza 2 – ARP cache (adresy MAC)
# ---------------------------------------------------------------------------

def get_arp_table() -> dict:
    """
    Czyta tablicę ARP systemu Windows poleceniem 'arp -a'.
    Zwraca słownik {ip_str: mac_str}.

    Tablica jest automatycznie zapełniana przez system po ping-sweep.
    Działa tylko dla hostów w tej samej sieci lokalnej (Layer 2).
    """
    try:
        proc = subprocess.run(
            ["arp", "-a"],
            capture_output=True,
            text=True,
            encoding="cp852",
            errors="replace",
            timeout=5,
            creationflags=_NO_WINDOW,
        )
        table = {}
        for line in proc.stdout.splitlines():
            # Format PL/EN: "  192.168.1.1    00-11-22-33-44-55    dynamiczny"
            m = re.match(
                r'\s*([\d.]+)\s+'
                r'([0-9a-fA-F]{2}[-:][0-9a-fA-F]{2}[-:][0-9a-fA-F]{2}'
                r'[-:][0-9a-fA-F]{2}[-:][0-9a-fA-F]{2}[-:][0-9a-fA-F]{2})',
                line
            )
            if m:
                ip = m.group(1)
                mac = m.group(2).replace("-", ":").upper()
                # Pomiń adresy rozgłoszeniowe (FF:FF:FF:FF:FF:FF)
                if mac != "FF:FF:FF:FF:FF:FF":
                    table[ip] = mac
        return table

    except Exception:
        return {}


# ---------------------------------------------------------------------------
# Faza 3 – Skanowanie portów TCP (opcjonalne)
# ---------------------------------------------------------------------------

def scan_ports(ip: str, ports: List[int], timeout_ms: int = 400) -> List[int]:
    """
    Sprawdza które porty TCP są otwarte na danym hoście.
    Używa socket.connect_ex() – pełne połączenie TCP (niezawodne).
    Skanuje wszystkie porty jednego hosta równolegle.

    Zwraca posortowaną listę numerów otwartych portów.
    """
    timeout_sec = timeout_ms / 1000

    def _check(port: int) -> Optional[int]:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout_sec)
            result = sock.connect_ex((ip, port))
            sock.close()
            return port if result == 0 else None
        except Exception:
            return None

    with ThreadPoolExecutor(max_workers=min(len(ports), 10)) as pool:
        results = list(pool.map(_check, ports))

    return sorted(p for p in results if p is not None)


# ---------------------------------------------------------------------------
# Faza 4 – Reverse DNS (nazwy hostów)
# ---------------------------------------------------------------------------

def resolve_hostname(ip: str, timeout_sec: float = 1.5) -> str:
    """
    Próbuje rozwiązać nazwę hosta przez reverse DNS.
    Używa wątku z timeoutem, bo socket.gethostbyaddr() może blokować.
    Zwraca 'Nieznany' gdy rozwiązanie się nie powiedzie.
    """
    holder = ["Nieznany"]
    done = threading.Event()

    def _do():
        try:
            holder[0] = socket.gethostbyaddr(ip)[0]
        except Exception:
            pass
        done.set()

    t = threading.Thread(target=_do, daemon=True)
    t.start()
    done.wait(timeout=timeout_sec)
    return holder[0]


# ---------------------------------------------------------------------------
# Główna funkcja skanowania (uruchamiana w wątku tła)
# ---------------------------------------------------------------------------

def scan_network(
    targets: List[str],
    result_queue: queue.Queue,
    stop_event: threading.Event,
    timeout_ms: int = 500,
    max_workers: int = 100,
    do_port_scan: bool = False,
    port_timeout_ms: int = 400,
) -> None:
    """
    Skanuje listę adresów IP i publikuje wyniki przez kolejkę.

    Wiadomości wrzucane do result_queue:
      ("progress", scanned: int, total: int)   – postęp ping-sweep
      ("found_live", ScanResult)               – wykryty żywy host (bez MAC/hostname)
      ("status", tekst: str)                   – zmiana etapu (np. "Pobieranie MAC...")
      ("done", wyniki: List[ScanResult])        – zakończenie, finalne dane

    Parametry:
      targets        – lista adresów IP do sprawdzenia
      result_queue   – kolejka thread-safe do komunikacji z UI
      stop_event     – ustawienie zatrzymuje skanowanie
      timeout_ms     – timeout pinga w milisekundach (100–2000)
      max_workers    – liczba równoległych wątków ping
      do_port_scan   – czy wykonać skanowanie portów TCP (Faza 3)
      port_timeout_ms – timeout połączenia TCP na port w milisekundach
    """
    total = len(targets)
    scanned = 0
    live_hosts: List[ScanResult] = []

    # ---- Faza 1: Ping-sweep ------------------------------------------------
    def _ping_one(ip: str) -> Optional[ScanResult]:
        if stop_event.is_set():
            return None
        alive, ms = ping_host(ip, timeout_ms)
        return ScanResult(ip=ip, is_alive=True, response_ms=ms) if alive else None

    with ThreadPoolExecutor(max_workers=min(max_workers, total)) as pool:
        futures = {pool.submit(_ping_one, ip): ip for ip in targets}
        for fut in as_completed(futures):
            if stop_event.is_set():
                break
            scanned += 1
            try:
                result = fut.result()
            except Exception:
                result = None
            if result:
                live_hosts.append(result)
                result_queue.put(("found_live", result))
            result_queue.put(("progress", scanned, total))

    if stop_event.is_set():
        live_hosts.sort(key=lambda r: [int(x) for x in r.ip.split(".")])
        result_queue.put(("done", live_hosts))
        return

    # ---- Faza 2: Adresy MAC z tablicy ARP ----------------------------------
    if live_hosts:
        result_queue.put(("status", "Pobieranie adresów MAC z tablicy ARP..."))
        arp = get_arp_table()
        for r in live_hosts:
            r.mac = arp.get(r.ip, "Brak")

    # ---- Faza 3: Skanowanie portów TCP (opcjonalne) ------------------------
    if live_hosts and do_port_scan and not stop_event.is_set():
        port_list = list(COMMON_PORTS.keys())
        n_hosts = len(live_hosts)
        n_ports = len(port_list)
        result_queue.put((
            "status",
            f"Skanowanie portów: {n_ports} portów × {n_hosts} hostów "
            f"(może potrwać do {n_hosts * port_timeout_ms // 1000 + 5} s)..."
        ))

        def _ports_one(r: ScanResult) -> ScanResult:
            if not stop_event.is_set():
                r.open_ports = scan_ports(r.ip, port_list, port_timeout_ms)
            return r

        # Skanujemy po 20 hostów naraz – każdy host używa n_ports wątków wewnętrznie
        with ThreadPoolExecutor(max_workers=min(20, n_hosts)) as pool:
            futs = [pool.submit(_ports_one, r) for r in live_hosts]
            done_count = 0
            for fut in as_completed(futs):
                if stop_event.is_set():
                    break
                try:
                    fut.result()
                except Exception:
                    pass
                done_count += 1
                result_queue.put(("status", f"Skanowanie portów: {done_count}/{n_hosts} hostów..."))

    # ---- Faza 4: Rozwiązywanie nazw hostów (DNS) ---------------------------
    if live_hosts and not stop_event.is_set():
        result_queue.put(("status", "Rozwiązywanie nazw hostów (DNS)..."))

        def _resolve_one(r: ScanResult) -> ScanResult:
            if not stop_event.is_set():
                r.hostname = resolve_hostname(r.ip)
            return r

        with ThreadPoolExecutor(max_workers=min(50, len(live_hosts))) as pool:
            futs = [pool.submit(_resolve_one, r) for r in live_hosts]
            for fut in as_completed(futs):
                if stop_event.is_set():
                    break
                try:
                    fut.result()
                except Exception:
                    pass

    # Sortuj po adresie IP
    live_hosts.sort(key=lambda r: [int(x) for x in r.ip.split(".")])
    result_queue.put(("done", live_hosts))
