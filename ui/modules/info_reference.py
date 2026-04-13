"""
ui/modules/info_reference.py
==============================
Moduł "Informacje" – statyczna baza wiedzy o popularnych portach TCP/UDP.

Układ kart (pionowy, bez stałych szerokości):
  [Nagłówek: numer | nazwa | badge TCP/UDP]
  [separator]
  [Opis protokołu – pełna szerokość]
  [Aplikacje – pełna szerokość]

Dzięki układowi pionowemu tekst nigdy nie nachodzi na siebie
i wszystkie karty są wyrównane do jednej kolumny.
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
SEPARATOR_CLR  = ("#ccd0da", "#45475a")
HEADER_ACCENT  = ("#1e66f5", "#89b4fa")
APPS_BG        = ("#d8dce8", "#2e2e42")

CAT_COLORS = {
    "Web":                ("#bac8f5", "#1e3a6e"),
    "Zdalne zarzadzanie": ("#f5d0a9", "#5c3010"),
    "Poczta":             ("#c8f5ba", "#1a4d10"),
    "Siec i Windows":     ("#f5bac8", "#5c1020"),
    "Transfer plikow":    ("#e0baf5", "#3c1060"),
    "Bazy danych":        ("#baf5ee", "#0e4d42"),
}

# ---------------------------------------------------------------------------
# Dane portów
# ---------------------------------------------------------------------------
PORT_CATEGORIES = [
    (
        "Web",
        "Protokoły komunikacji z serwerami WWW i aplikacjami webowymi.",
        [
            (80,   "HTTP",      "TCP",
             "HyperText Transfer Protocol – niezaszyfrowana komunikacja z serwerami WWW. "
             "Wszystkie przeglądarki rozumieją ten protokół. Dane przesyłane są jawnym "
             "tekstem, dlatego współcześnie zaleca się wyłącznie HTTPS.",
             "Chrome, Firefox, Edge, curl, wget  •  Serwery: Apache, Nginx, IIS"),

            (443,  "HTTPS",     "TCP",
             "HTTP Secure – szyfrowana wersja HTTP z użyciem protokołu TLS (dawniej SSL). "
             "Dziś absolutny standard dla wszystkich stron internetowych, sklepów, banków "
             "i REST API. Certyfikaty TLS wydaje m.in. Let's Encrypt (bezpłatnie).",
             "Przeglądarki, REST API, Let's Encrypt, Cloudflare  •  Serwery: Apache, Nginx"),

            (8080, "HTTP-Alt",  "TCP",
             "Alternatywny port HTTP. Używany gdy port 80 jest zajęty lub zarezerwowany. "
             "Typowy w środowiskach deweloperskich, serwerach proxy oraz kontenerach Docker "
             "gdzie mapowanie portów jest standardową praktyką.",
             "Apache Tomcat, Node.js dev, Docker, proxy Squid, Jenkins, Spring Boot"),

            (8443, "HTTPS-Alt", "TCP",
             "Alternatywny port HTTPS – odpowiednik 8080 dla ruchu szyfrowanego TLS. "
             "Popularny w panelach administracyjnych urządzeń sieciowych i serwerach "
             "aplikacyjnych działających obok głównego serwera WWW na porcie 443.",
             "Tomcat SSL, Proxmox VE (panel web), pfSense, Plesk, cPanel"),
        ],
    ),
    (
        "Zdalne zarzadzanie",
        "Protokoły umożliwiające zdalny dostęp do systemów i urządzeń.",
        [
            (22,   "SSH",       "TCP",
             "Secure Shell – szyfrowane zdalne logowanie i wykonywanie poleceń w terminalu. "
             "Całkowicie zastąpił niezaszyfrowany Telnet. Standard administracji systemami "
             "Linux/Unix oraz urządzeniami sieciowymi. Obsługuje też tunelowanie portów, "
             "transfer plików (SFTP/SCP) i zdalne wykonywanie skryptów.",
             "OpenSSH, PuTTY, WinSCP, FileZilla (SFTP), MobaXterm, Git over SSH"),

            (23,   "Telnet",    "TCP",
             "Stary protokół zdalnego terminala – przesyła WSZYSTKIE dane jawnym tekstem, "
             "w tym login i hasło. Ktokolwiek podsłuchuje sieć widzi pełną sesję. "
             "Dziś używany wyłącznie w starszych urządzeniach sieciowych (switche, routery) "
             "i systemach przemysłowych, które nie obsługują SSH. Nie należy go używać "
             "w sieciach publicznych ani korporacyjnych.",
             "Stare routery/switche Cisco, systemy przemysłowe SCADA, terminale retro"),

            (3389, "RDP",       "TCP",
             "Remote Desktop Protocol – protokół graficznego pulpitu zdalnego firmy Microsoft. "
             "Umożliwia pełną obsługę komputera z Windows przez sieć z interfejsem graficznym. "
             "Często atakowany metodą brute-force (słownikowe łamanie haseł) – zaleca się "
             "zmianę portu, VPN lub uwierzytelnianie dwuskładnikowe.",
             "Pulpit zdalny Windows (mstsc.exe), AnyDesk, MobaXterm, Remmina (Linux)"),

            (5900, "VNC",       "TCP",
             "Virtual Network Computing – wieloplatformowy protokół graficznego pulpitu "
             "zdalnego. Działa na Windows, Linux i macOS. Port bazowy to 5900; "
             "każdy kolejny wirtualny ekran używa kolejnego portu (5901, 5902...). "
             "Dane mogą być nieszyfrowane – zaleca się tunelowanie przez SSH.",
             "RealVNC, TightVNC, TigerVNC, UltraVNC, Remmina"),
        ],
    ),
    (
        "Poczta",
        "Protokoły wysyłania i odbierania wiadomości e-mail.",
        [
            (25,   "SMTP",      "TCP",
             "Simple Mail Transfer Protocol – protokół wysyłania i przekazywania poczty "
             "między serwerami. Port 25 jest powszechnie blokowany przez dostawców internetu "
             "dla użytkowników domowych (zapobieganie spamowi). Klienty pocztowe używają "
             "portu 587 (STARTTLS) lub 465 (SMTPS) do wysyłania przez serwer.",
             "Postfix, Exim, Microsoft Exchange, sendmail, Haraka"),

            (110,  "POP3",      "TCP",
             "Post Office Protocol v3 – protokół pobierania poczty z serwera na urządzenie "
             "lokalne. Po pobraniu wiadomości są domyślnie usuwane z serwera. Starsza metoda "
             "wypierana przez IMAP, ponieważ nie umożliwia wygodnej synchronizacji między "
             "wieloma urządzeniami.",
             "Mozilla Thunderbird, Outlook, Apple Mail, The Bat!"),

            (143,  "IMAP",      "TCP",
             "Internet Message Access Protocol – protokół synchronizacji poczty z serwerem. "
             "W przeciwieństwie do POP3 wiadomości pozostają na serwerze, co umożliwia "
             "dostęp z komputera, telefonu i tabletu jednocześnie – wszystkie urządzenia "
             "widzą ten sam stan skrzynki. Współczesny standard obsługi poczty.",
             "Thunderbird, Outlook, Gmail (przez IMAP), Apple Mail, K-9 Mail"),
        ],
    ),
    (
        "Siec i Windows",
        "Protokoły podstawowej infrastruktury sieciowej i usług Windows.",
        [
            (53,   "DNS",       "TCP/UDP",
             "Domain Name System – system tłumaczenia nazw domenowych na adresy IP "
             "(np. google.com → 142.250.74.46). Zapytania DNS wysyłane są przez UDP/53 "
             "(szybkie, małe pakiety). TCP/53 używany jest do transferu stref DNS "
             "i odpowiedzi przekraczających 512 bajtów. Bez DNS musielibyśmy pamiętać "
             "adresy IP wszystkich odwiedzanych stron.",
             "Windows DNS Server, BIND 9, Unbound, Pi-hole, Cloudflare 1.1.1.1, Google 8.8.8.8"),

            (135,  "RPC",       "TCP",
             "Remote Procedure Call (Endpoint Mapper) – mechanizm wywoływania procedur "
             "na zdalnym komputerze Windows. Służy jako punkt wejścia do dynamicznie "
             "przydzielanych portów wyższych używanych przez usługi Windows. "
             "Wymagany przez WMI, DCOM, replikację Active Directory i harmonogram zadań.",
             "Windows (DCOM, WMI, harmonogram zadań, replikacja AD, SCCM)"),

            (139,  "NetBIOS",   "TCP",
             "NetBIOS Session Service – stara implementacja udostępniania plików i drukarek "
             "w sieciach Windows, poprzednik protokołu SMB. Wymagany przez bardzo stare "
             "systemy (Windows 95/98/XP). W nowoczesnych sieciach Windows można go wyłączyć "
             "– SMB działa bezpośrednio przez TCP na porcie 445.",
             "Stare sieci Windows, Samba (tryb kompatybilności z Windows 9x)"),

            (445,  "SMB",       "TCP",
             "Server Message Block – protokół udostępniania plików, drukarek i zasobów "
             "sieciowych w Windows (ścieżka: \\\\serwer\\udział). Nowsza wersja (SMB 2/3) "
             "działa bezpośrednio przez TCP bez NetBIOS. Był celem głośnych ataków "
             "ransomware WannaCry i NotPetya (2017). Zaleca się blokowanie portu 445 "
             "na zaporze obwodowej i wyłączenie SMB v1.",
             "Eksplorator Windows (\\\\), Samba, NAS Synology/QNAP/TrueNAS"),
        ],
    ),
    (
        "Transfer plikow",
        "Protokoły przesyłania plików między komputerami.",
        [
            (21,   "FTP",       "TCP",
             "File Transfer Protocol – jeden z najstarszych protokołów internetu (1971). "
             "Przesyła pliki BEZ szyfrowania: dane, login i hasło są widoczne w sieci. "
             "Port 21 to kanał sterujący (komendy); dane przepływają przez osobne połączenie "
             "– losowy port w trybie pasywnym lub port 20 w trybie aktywnym. "
             "Zalecane zamienniki: SFTP (przez SSH, port 22) lub FTPS (FTP+TLS, port 990).",
             "FileZilla Server/Client, WinSCP, Total Commander, hosting współdzielony"),
        ],
    ),
    (
        "Bazy danych",
        "Domyślne porty serwerów relacyjnych baz danych.",
        [
            (1433, "MSSQL",     "TCP",
             "Microsoft SQL Server – domyślny port serwera relacyjnych baz danych firmy "
             "Microsoft. Często atakowany metodą brute-force gdy jest dostępny z internetu. "
             "W środowiskach produkcyjnych zaleca się: zmianę portu na niestandardowy, "
             "ograniczenie dostępu przez firewall wyłącznie do znanych adresów IP "
             "oraz wyłączenie logowania konta 'sa'.",
             "SQL Server Management Studio (SSMS), Azure Data Studio, aplikacje .NET/ASP.NET, Entity Framework"),

            (3306, "MySQL",     "TCP",
             "MySQL / MariaDB – najpopularniejszy open-source'owy serwer relacyjnych baz "
             "danych. Używany przez zdecydowaną większość aplikacji webowych: WordPress, "
             "Drupal, Joomla, Magento. Domyślnie nasłuchuje tylko na localhost (127.0.0.1) "
             "– nie powinien być dostępny spoza sieci lokalnej bez VPN lub tunelu SSH.",
             "phpMyAdmin, MySQL Workbench, DBeaver, aplikacje PHP/Python/Java/Ruby"),
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
        hdr.grid(row=0, column=0, sticky="ew", padx=24, pady=(18, 0))
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
            text="Opis popularnych portów TCP/UDP – czym są, jakie usługi z nich korzystają i przykładowe aplikacje.",
            font=ctk.CTkFont(size=12),
            text_color=TEXT_MUTED,
        ).grid(row=1, column=0, sticky="w")

    def _build_content(self):
        scroll = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_button_color=SEPARATOR_CLR,
        )
        scroll.grid(row=1, column=0, sticky="nsew", padx=24, pady=(14, 18))
        scroll.grid_columnconfigure(0, weight=1)

        row = 0

        # --- Blok wstępny ---
        self._build_intro(scroll, row)
        row += 1

        # --- Sekcje kategorii ---
        for category, subtitle, ports in PORT_CATEGORIES:
            self._build_category_section(scroll, row, category, subtitle, ports)
            row += 1

    # ------------------------------------------------------------------
    # Blok wstępny
    # ------------------------------------------------------------------

    def _build_intro(self, parent, row):
        intro = ctk.CTkFrame(parent, fg_color=CARD_BG, corner_radius=12)
        intro.grid(row=row, column=0, sticky="ew", pady=(0, 16))
        intro.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            intro,
            text="Czym jest port sieciowy?",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=HEADER_ACCENT,
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=20, pady=(16, 6))

        intro_text = (
            "Port to liczba z zakresu 0–65535, która identyfikuje konkretną usługę działającą "
            "na danym komputerze. Adres IP wskazuje komputer w sieci, a numer portu określa, "
            "która aplikacja na tym komputerze ma odebrać dane.\n\n"
            "Przykład:  192.168.1.10 : 80  →  serwer WWW na komputerze o adresie 192.168.1.10.\n\n"
            "Podział portów według organizacji IANA:\n"
            "  •  0 – 1023     Porty uprzywilejowane (well-known) – zarezerwowane dla standardowych protokołów. "
            "Wymagają uprawnień administratora do otwarcia.\n"
            "  •  1024 – 49151  Porty zarejestrowane – przypisane konkretnym aplikacjom (np. bazy danych).\n"
            "  •  49152 – 65535  Porty dynamiczne (efemeryczne) – używane przez system operacyjny "
            "do połączeń wychodzących."
        )
        ctk.CTkLabel(
            intro,
            text=intro_text,
            font=ctk.CTkFont(size=13),
            text_color=TEXT_SECONDARY,
            anchor="w",
            justify="left",
            wraplength=780,
        ).grid(row=1, column=0, sticky="w", padx=20, pady=(0, 18))

    # ------------------------------------------------------------------
    # Sekcja kategorii
    # ------------------------------------------------------------------

    def _build_category_section(self, parent, row, category, subtitle, ports):
        section = ctk.CTkFrame(parent, fg_color=SECTION_BG, corner_radius=12)
        section.grid(row=row, column=0, sticky="ew", pady=(0, 16))
        section.grid_columnconfigure(0, weight=1)

        # Nagłówek kategorii
        cat_hdr = ctk.CTkFrame(section, fg_color="transparent")
        cat_hdr.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 10))

        cat_color = CAT_COLORS.get(category, ("#e0e0e0", "#404040"))
        badge = ctk.CTkFrame(cat_hdr, fg_color=cat_color, corner_radius=6)
        badge.pack(side="left")
        ctk.CTkLabel(
            badge,
            text=f"  {category}  ",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=TEXT_PRIMARY,
            pady=4,
        ).pack()

        ctk.CTkLabel(
            cat_hdr,
            text=f"   {subtitle}",
            font=ctk.CTkFont(size=12),
            text_color=TEXT_MUTED,
        ).pack(side="left")

        # Separator pod nagłówkiem kategorii
        ctk.CTkFrame(section, height=1, fg_color=SEPARATOR_CLR).grid(
            row=1, column=0, sticky="ew", padx=20, pady=(0, 10)
        )

        # Karty portów
        for i, (port, name, proto, desc, apps) in enumerate(ports):
            self._build_port_card(section, i + 2, port, name, proto, desc, apps)

        # Dolny margines wewnętrzny sekcji
        ctk.CTkFrame(section, height=10, fg_color="transparent").grid(
            row=len(ports) + 2, column=0
        )

    # ------------------------------------------------------------------
    # Karta pojedynczego portu
    # ------------------------------------------------------------------

    def _build_port_card(self, parent, row, port, name, proto, desc, apps):
        """
        Układ pionowy karty:
          [wiersz A] numer portu | nazwa protokołu | badge TCP/UDP
          [separator poziomy]
          [wiersz B] ramka z opisem protokołu
          [wiersz C] ramka z aplikacjami (kompaktowa – dopasowana do treści)
        """
        # Karta z subtelną obwódką oddzielającą ją od tła sekcji
        card = ctk.CTkFrame(
            parent,
            fg_color=CARD_BG,
            corner_radius=10,
            border_width=1,
            border_color=SEPARATOR_CLR,
        )
        card.grid(row=row, column=0, sticky="ew", padx=20, pady=(0, 10))
        card.grid_columnconfigure(0, weight=1)

        # ---- Wiersz A: nagłówek portu ----
        port_hdr = ctk.CTkFrame(card, fg_color="transparent")
        port_hdr.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 8))

        ctk.CTkLabel(
            port_hdr,
            text=str(port),
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color=HEADER_ACCENT,
        ).pack(side="left")

        ctk.CTkLabel(
            port_hdr,
            text=f"  {name}",
            font=ctk.CTkFont(size=17, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).pack(side="left", pady=(6, 0))

        proto_badge = ctk.CTkFrame(port_hdr, fg_color=SEPARATOR_CLR, corner_radius=6)
        proto_badge.pack(side="left", padx=(12, 0), pady=(6, 0))
        ctk.CTkLabel(
            proto_badge,
            text=f"  {proto}  ",
            font=ctk.CTkFont(size=12),
            text_color=TEXT_SECONDARY,
            pady=3,
        ).pack()

        # ---- Separator poziomy ----
        ctk.CTkFrame(card, height=1, fg_color=SEPARATOR_CLR).grid(
            row=1, column=0, sticky="ew", padx=16, pady=(0, 8)
        )

        # ---- Wiersz B: ramka opisu protokołu ----
        desc_frame = ctk.CTkFrame(
            card,
            fg_color="transparent",
            corner_radius=6,
            border_width=1,
            border_color=SEPARATOR_CLR,
        )
        desc_frame.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 8))
        desc_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            desc_frame,
            text=desc,
            font=ctk.CTkFont(size=13),
            text_color=TEXT_PRIMARY,
            anchor="w",
            justify="left",
            wraplength=750,
        ).grid(row=0, column=0, sticky="w", padx=12, pady=10)

        # ---- Wiersz C: ramka aplikacji (kompaktowa) ----
        apps_frame = ctk.CTkFrame(
            card,
            fg_color=APPS_BG,
            corner_radius=6,
            border_width=1,
            border_color=SEPARATOR_CLR,
        )
        apps_frame.grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 12))
        apps_frame.grid_columnconfigure(2, weight=1)

        ctk.CTkLabel(
            apps_frame,
            text="Aplikacje",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=TEXT_MUTED,
            width=68,
            anchor="e",
        ).grid(row=0, column=0, padx=(10, 0), pady=5, sticky="e")

        # Separator pionowy między etykietą a wartością
        ctk.CTkFrame(apps_frame, width=1, fg_color=SEPARATOR_CLR).grid(
            row=0, column=1, sticky="ns", padx=8, pady=4
        )

        ctk.CTkLabel(
            apps_frame,
            text=apps,
            font=ctk.CTkFont(size=12),
            text_color=TEXT_SECONDARY,
            anchor="w",
            justify="left",
            wraplength=660,
        ).grid(row=0, column=2, padx=(0, 10), pady=5, sticky="w")
