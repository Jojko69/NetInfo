"""
ui/modules/info_reference.py
==============================
Moduł "Informacje" – statyczna baza wiedzy o popularnych portach TCP/UDP.

Zawiera:
  - Opisy 18 portów skanowanych przez moduł sieciowy + kilka dodatkowych
  - Pogrupowanie tematyczne: Web, Zdalne zarządzanie, Poczta, Sieć/Windows,
    Transfer plików, Bazy danych
  - Krótki wstęp czym są porty

Moduł jest czysto informacyjny – brak logiki sieciowej.
"""

import customtkinter as ctk


# ---------------------------------------------------------------------------
# Paleta kolorów
# ---------------------------------------------------------------------------
TEXT_PRIMARY   = ("#4c4f69", "#cdd6f4")
TEXT_SECONDARY = ("#6c6f85", "#a6adc8")
TEXT_MUTED     = ("#9ca0b0", "#6c7086")
CARD_BG        = ("#e6e9f0", "#313244")
SECTION_BG     = ("#dce0e8", "#2a2a3e")
HEADER_ACCENT  = ("#1e66f5", "#89b4fa")

# Kolory kategorii (badge tła)
CAT_COLORS = {
    "Web":                ("#bac8f5", "#1e3a6e"),
    "Zdalne zarzadzanie": ("#f5d0a9", "#5c3010"),
    "Poczta":             ("#c8f5ba", "#1a4d10"),
    "Siec i Windows":     ("#f5bac8", "#5c1020"),
    "Transfer plikow":    ("#e0baf5", "#3c1060"),
    "Bazy danych":        ("#baf5ee", "#0e4d42"),
}

# ---------------------------------------------------------------------------
# Dane portów pogrupowane tematycznie
# ---------------------------------------------------------------------------
# Format każdej pozycji:
#   (numer_portu, "NAZWA", "TCP/UDP", "opis usługi", "przykłady aplikacji")
# ---------------------------------------------------------------------------
PORT_CATEGORIES = [
    (
        "Web",
        "Protokoły komunikacji z serwerami WWW i aplikacjami webowymi.",
        [
            (80,   "HTTP",      "TCP",
             "HyperText Transfer Protocol – niezaszyfrowana komunikacja z serwerami WWW.",
             "Przeglądarki (Chrome, Firefox), curl, wget, Apache, Nginx, IIS"),

            (443,  "HTTPS",     "TCP",
             "HTTP Secure – szyfrowana wersja HTTP (TLS/SSL). Standard dla wszystkich "
             "współczesnych stron internetowych i API.",
             "Przeglądarki, REST API, Let's Encrypt, Cloudflare"),

            (8080, "HTTP-Alt",  "TCP",
             "Alternatywny port HTTP. Często używany przez serwery deweloperskie, "
             "proxy HTTP oraz aplikacje gdy port 80 jest zajęty.",
             "Tomcat, Node.js dev, Docker, proxy Squid, Jenkins"),

            (8443, "HTTPS-Alt", "TCP",
             "Alternatywny port HTTPS. Odpowiednik 8080 dla ruchu szyfrowanego. "
             "Popularny w środowiskach testowych i panelach administracyjnych.",
             "Tomcat SSL, Proxmox (panel web), pfSense"),
        ],
    ),
    (
        "Zdalne zarzadzanie",
        "Protokoły umożliwiające zdalny dostęp do systemów i urządzeń.",
        [
            (22,   "SSH",       "TCP",
             "Secure Shell – szyfrowane zdalne logowanie i wykonywanie poleceń "
             "w terminalu. Zastąpił niezaszyfrowany Telnet. Standard w systemach "
             "Linux/Unix i urządzeniach sieciowych.",
             "OpenSSH, PuTTY, WinSCP, FileZilla (SFTP), Git over SSH"),

            (23,   "Telnet",    "TCP",
             "Stary protokół zdalnego terminala – przesyła dane BEZ szyfrowania "
             "(login, hasło i dane widoczne w sieci). Dziś używany głównie w starszych "
             "urządzeniach sieciowych i systemach przemysłowych.",
             "Stare routery/switche Cisco, systemy przemysłowe SCADA"),

            (3389, "RDP",       "TCP",
             "Remote Desktop Protocol – graficzny pulpit zdalny Windows. Umożliwia "
             "pełną obsługę komputera z interfejsem graficznym przez sieć.",
             "Pulpit zdalny Windows (mstsc.exe), AnyDesk, MobaXterm"),

            (5900, "VNC",       "TCP",
             "Virtual Network Computing – platforma-niezależny protokół graficznego "
             "pulpitu zdalnego. Port bazowy to 5900; każdy kolejny ekran to +1 "
             "(5901, 5902...).",
             "RealVNC, TightVNC, TigerVNC, UltraVNC"),
        ],
    ),
    (
        "Poczta",
        "Protokoły wysyłania i odbierania wiadomości e-mail.",
        [
            (25,   "SMTP",      "TCP",
             "Simple Mail Transfer Protocol – wysyłanie i przekazywanie poczty "
             "między serwerami. Port 25 jest często blokowany przez dostawców "
             "internetu dla klientów końcowych (aby zapobiec spamowi). "
             "Klienty pocztowe używają portów 587 (STARTTLS) lub 465 (SMTPS).",
             "Postfix, Exim, Microsoft Exchange, sendmail"),

            (110,  "POP3",      "TCP",
             "Post Office Protocol v3 – pobieranie poczty z serwera na urządzenie "
             "lokalne. Wiadomości są zwykle usuwane z serwera po pobraniu "
             "(starsza metoda, wypierana przez IMAP).",
             "Mozilla Thunderbird, Outlook, Apple Mail"),

            (143,  "IMAP",      "TCP",
             "Internet Message Access Protocol – synchronizacja poczty z serwerem "
             "bez jej usuwania. Wiadomości pozostają na serwerze, co umożliwia "
             "dostęp z wielu urządzeń jednocześnie. Współczesny standard.",
             "Thunderbird, Outlook, Gmail (przez IMAP), Apple Mail"),
        ],
    ),
    (
        "Siec i Windows",
        "Protokoły podstawowej infrastruktury sieciowej i usług Windows.",
        [
            (53,   "DNS",       "TCP/UDP",
             "Domain Name System – tłumaczenie nazw domenowych na adresy IP "
             "(np. google.com → 142.250.74.46). UDP/53 do zapytań, "
             "TCP/53 do transferu stref i dużych odpowiedzi.",
             "Windows DNS, BIND, Unbound, Pi-hole, Cloudflare 1.1.1.1"),

            (135,  "RPC",       "TCP",
             "Remote Procedure Call – mechanizm wywoływania procedur na zdalnym "
             "komputerze. Używany przez wiele usług Windows jako punkt wejścia "
             "do dynamicznie przydzielanych portów wyższych.",
             "Windows (DCOM, WMI, harmonogram zadań, replikacja AD)"),

            (139,  "NetBIOS",   "TCP",
             "NetBIOS Session Service – stara implementacja udostępniania plików "
             "i drukarek w sieciach Windows. Poprzednik SMB. Dziś wymagany tylko "
             "w starszych środowiskach (Windows XP i starsze).",
             "Stare sieci Windows, Samba (tryb kompatybilności)"),

            (445,  "SMB",       "TCP",
             "Server Message Block – udostępnianie plików, drukarek i zasobów "
             "sieciowych w Windows (\\\\serwer\\udział). Nowsza wersja działa "
             "bezpośrednio przez TCP bez NetBIOS. Cel wielu ataków "
             "(WannaCry, NotPetya) – warto blokować na obwodzie sieci.",
             "Eksplorator Windows (\\\\), Samba, NAS Synology/QNAP"),
        ],
    ),
    (
        "Transfer plikow",
        "Protokoły przesyłania plików między komputerami.",
        [
            (21,   "FTP",       "TCP",
             "File Transfer Protocol – przesyłanie plików bez szyfrowania. "
             "Port 21 to kanał sterujący (komendy); dane przepływają przez "
             "losowy port (tryb pasywny) lub port 20 (tryb aktywny). "
             "Dziś zalecane jest użycie SFTP (SSH, port 22) lub FTPS (FTP+TLS).",
             "FileZilla Server/Client, WinSCP (FTP), hosting współdzielony"),
        ],
    ),
    (
        "Bazy danych",
        "Domyślne porty serwerów relacyjnych baz danych.",
        [
            (1433, "MSSQL",     "TCP",
             "Microsoft SQL Server – domyślny port serwera baz danych Microsoft. "
             "Narażony na ataki brute-force gdy dostępny z internetu. "
             "W środowiskach produkcyjnych zaleca się zmianę portu lub "
             "ograniczenie dostępu przez firewall.",
             "SQL Server Management Studio (SSMS), aplikacje .NET/ASP.NET"),

            (3306, "MySQL",     "TCP",
             "MySQL / MariaDB – najpopularniejszy open-source'owy serwer baz "
             "danych. Używany przez większość aplikacji webowych (WordPress, "
             "Drupal, Joomla). Nie powinien być dostępny spoza sieci lokalnej.",
             "phpMyAdmin, MySQL Workbench, aplikacje PHP/Python/Java"),
        ],
    ),
]


# ---------------------------------------------------------------------------
# Klasa modułu
# ---------------------------------------------------------------------------

class InfoReferenceModule(ctk.CTkFrame):
    """Panel informacyjny – baza wiedzy o portach sieciowych."""

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_header()
        self._build_content()

    # ------------------------------------------------------------------
    # Budowanie UI
    # ------------------------------------------------------------------

    def _build_header(self):
        hdr = ctk.CTkFrame(self, fg_color="transparent", height=70)
        hdr.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 0))
        hdr.grid_propagate(False)
        hdr.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            hdr,
            text="Informacje – Porty sieciowe",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            hdr,
            text="Opis popularnych portów TCP/UDP skanowanych przez moduł sieciowy.",
            font=ctk.CTkFont(size=11),
            text_color=TEXT_MUTED,
        ).grid(row=1, column=0, sticky="w")

    def _build_content(self):
        scroll = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_button_color=("#ccd0da", "#45475a"),
        )
        scroll.grid(row=1, column=0, sticky="nsew", padx=20, pady=(12, 16))
        scroll.grid_columnconfigure(0, weight=1)

        row = 0

        # --- Wstęp: czym są porty ---
        intro = ctk.CTkFrame(scroll, fg_color=CARD_BG, corner_radius=12)
        intro.grid(row=row, column=0, sticky="ew", pady=(0, 14))
        intro.grid_columnconfigure(0, weight=1)
        row += 1

        ctk.CTkLabel(
            intro,
            text="Czym jest port sieciowy?",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=HEADER_ACCENT,
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 4))

        intro_text = (
            "Port to liczba z zakresu 0–65535 identyfikująca konkretną usługę na danym komputerze. "
            "Adres IP wskazuje komputer w sieci, a port – którą aplikację na tym komputerze "
            "chcemy osiągnąć. Przykład: 192.168.1.10:80 oznacza serwer WWW na komputerze "
            "o adresie 192.168.1.10.\n\n"
            "Porty 0–1023 to porty uprzywilejowane (well-known ports) – zarezerwowane dla "
            "standardowych protokołów przez organizację IANA. Otwarcie ich na serwerze "
            "wymaga uprawnień administratora. Porty 1024–49151 to porty zarejestrowane "
            "(np. dla baz danych), a 49152–65535 to porty dynamiczne (efemeryczne), "
            "używane przez system do połączeń wychodzących."
        )
        ctk.CTkLabel(
            intro,
            text=intro_text,
            font=ctk.CTkFont(size=12),
            text_color=TEXT_SECONDARY,
            anchor="w",
            justify="left",
            wraplength=820,
        ).grid(row=1, column=0, sticky="w", padx=16, pady=(0, 14))

        # --- Sekcje kategorii ---
        for category, subtitle, ports in PORT_CATEGORIES:
            self._build_category_section(scroll, row, category, subtitle, ports)
            row += 1

    def _build_category_section(self, parent, row, category, subtitle, ports):
        """Buduje sekcję dla jednej kategorii portów."""
        section = ctk.CTkFrame(parent, fg_color=SECTION_BG, corner_radius=12)
        section.grid(row=row, column=0, sticky="ew", pady=(0, 14))
        section.grid_columnconfigure(0, weight=1)

        # Nagłówek sekcji
        cat_hdr = ctk.CTkFrame(section, fg_color="transparent")
        cat_hdr.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 6))

        cat_color = CAT_COLORS.get(category, ("#e0e0e0", "#404040"))
        badge = ctk.CTkFrame(cat_hdr, fg_color=cat_color, corner_radius=6, height=26)
        badge.pack(side="left")
        badge.pack_propagate(False)
        ctk.CTkLabel(
            badge,
            text=f"  {category}  ",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).pack(expand=True)

        ctk.CTkLabel(
            cat_hdr,
            text=f"  {subtitle}",
            font=ctk.CTkFont(size=11),
            text_color=TEXT_MUTED,
        ).pack(side="left")

        # Separator
        ctk.CTkFrame(
            section, height=1,
            fg_color=("#ccd0da", "#45475a"),
        ).grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 8))

        # Karty portów
        for port_row, (port, name, proto, desc, apps) in enumerate(ports):
            self._build_port_card(section, port_row + 2, port, name, proto, desc, apps)

        # Dolny odstęp
        ctk.CTkFrame(section, height=6, fg_color="transparent").grid(
            row=len(ports) + 2, column=0
        )

    def _build_port_card(self, parent, row, port, name, proto, desc, apps):
        """Buduje kartę pojedynczego portu."""
        card = ctk.CTkFrame(parent, fg_color=CARD_BG, corner_radius=8)
        card.grid(row=row, column=0, sticky="ew", padx=16, pady=(0, 8))
        card.grid_columnconfigure(1, weight=1)

        # Lewa kolumna: numer portu + nazwa + protokół
        left = ctk.CTkFrame(card, fg_color="transparent", width=130)
        left.grid(row=0, column=0, rowspan=2, sticky="nsw", padx=(14, 0), pady=12)
        left.grid_propagate(False)

        # Numer portu – duży, wyróżniony
        ctk.CTkLabel(
            left,
            text=str(port),
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=HEADER_ACCENT,
            anchor="w",
        ).pack(anchor="w")

        # Nazwa protokołu
        ctk.CTkLabel(
            left,
            text=name,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=TEXT_PRIMARY,
            anchor="w",
        ).pack(anchor="w")

        # Badge TCP/UDP
        proto_frame = ctk.CTkFrame(left, fg_color=("#ccd0da", "#45475a"), corner_radius=4, height=20)
        proto_frame.pack(anchor="w", pady=(3, 0))
        proto_frame.pack_propagate(False)
        ctk.CTkLabel(
            proto_frame,
            text=f" {proto} ",
            font=ctk.CTkFont(size=10),
            text_color=TEXT_SECONDARY,
        ).pack(expand=True)

        # Separator pionowy
        ctk.CTkFrame(card, width=1, fg_color=("#ccd0da", "#45475a")).grid(
            row=0, column=1, rowspan=2, sticky="ns", padx=(12, 16), pady=10
        )

        # Prawa kolumna: opis + aplikacje
        right = ctk.CTkFrame(card, fg_color="transparent")
        right.grid(row=0, column=2, sticky="ew", padx=(0, 16), pady=(12, 4))
        right.grid_columnconfigure(0, weight=1)
        card.grid_columnconfigure(2, weight=1)

        ctk.CTkLabel(
            right,
            text=desc,
            font=ctk.CTkFont(size=12),
            text_color=TEXT_PRIMARY,
            anchor="w",
            justify="left",
            wraplength=640,
        ).grid(row=0, column=0, sticky="w")

        # Aplikacje
        apps_frame = ctk.CTkFrame(card, fg_color="transparent")
        apps_frame.grid(row=1, column=2, sticky="ew", padx=(0, 16), pady=(0, 12))
        apps_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            apps_frame,
            text="Aplikacje:",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=TEXT_MUTED,
            width=60,
            anchor="w",
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            apps_frame,
            text=apps,
            font=ctk.CTkFont(size=11),
            text_color=TEXT_SECONDARY,
            anchor="w",
            justify="left",
            wraplength=590,
        ).grid(row=0, column=1, sticky="w")
