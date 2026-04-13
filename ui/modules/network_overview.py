"""
ui/modules/network_overview.py
================================
Moduł "Przegląd sieci" – główny panel aplikacji NetInfo.

Wyświetla karty dla każdego wykrytego interfejsu sieciowego.
Aktywny interfejs z bramą domyślną jest wizualnie wyróżniony.

Jak dodać nowy moduł:
  1. Skopiuj ten plik do ui/modules/nowy_modul.py
  2. Zmień nazwę klasy i treść metody _build_content()
  3. Zarejestruj w ui/app.py (MODULE_REGISTRY)
"""

import threading
import customtkinter as ctk
from typing import List, Optional

from core.network import InterfaceInfo, get_network_interfaces


# ---------------------------------------------------------------------------
# Stałe kolorów – definiowane jako krotki (ciemny, jasny) dla CTk
# ---------------------------------------------------------------------------

# Kolor akcentu dla aktywnego/głównego interfejsu
ACCENT_BORDER   = ("#1e66f5", "#89b4fa")   # niebieski
SUCCESS_COLOR   = ("#40a02b", "#a6e3a1")   # zielony (aktywny)
INACTIVE_COLOR  = ("#7c7f93", "#585b70")   # szary (nieaktywny)
WARNING_COLOR   = ("#df8e1d", "#f9e2af")   # żółty (ostrzeżenie)
CARD_BG         = ("#e6e9f0", "#313244")   # tło karty
CARD_HIGHLIGHT  = ("#d0d5e8", "#3d4059")   # tło wyróżnionej karty
BADGE_BG        = ("#ccd0da", "#45475a")   # tło badge'a (etykietki)

# Kolory tekstu
TEXT_PRIMARY    = ("#4c4f69", "#cdd6f4")
TEXT_SECONDARY  = ("#6c6f85", "#a6adc8")
TEXT_MUTED      = ("#9ca0b0", "#6c7086")
TEXT_VALUE      = ("#1e66f5", "#89b4fa")   # wartości w kolorze akcentu


class NetworkOverviewModule(ctk.CTkFrame):
    """
    Panel przeglądu sieci.

    Wewnętrznie używa wątku tła do pobrania danych, żeby UI
    nie zamrażał się podczas zapytań PowerShell.
    """

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._interfaces: List[InterfaceInfo] = []
        self._loading = False

        self._build_header()
        self._build_body()
        self.refresh()                     # Pierwsze załadowanie danych

    # ------------------------------------------------------------------
    # Budowanie stałych elementów UI
    # ------------------------------------------------------------------

    def _build_header(self):
        """Pasek nagłówka z tytułem, licznikiem i przyciskiem odświeżania."""
        header = ctk.CTkFrame(self, fg_color="transparent", height=60)
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 0))
        header.grid_columnconfigure(1, weight=1)
        header.grid_propagate(False)

        # Tytuł modułu
        ctk.CTkLabel(
            header,
            text="Przeglad sieci",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).grid(row=0, column=0, sticky="w")

        # Licznik interfejsów – aktualizowany po załadowaniu
        self._counter_label = ctk.CTkLabel(
            header,
            text="",
            font=ctk.CTkFont(size=12),
            text_color=TEXT_MUTED,
        )
        self._counter_label.grid(row=1, column=0, sticky="w")

        # Przycisk Odświeź
        self._refresh_btn = ctk.CTkButton(
            header,
            text="  Odswiez",
            width=120,
            height=36,
            corner_radius=8,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.refresh,
        )
        self._refresh_btn.grid(row=0, column=2, rowspan=2, sticky="e")

        # Status ładowania
        self._status_label = ctk.CTkLabel(
            header,
            text="",
            font=ctk.CTkFont(size=12),
            text_color=TEXT_MUTED,
        )
        self._status_label.grid(row=0, column=1, sticky="e", padx=(0, 10))

    def _build_body(self):
        """Przewijalna ramka na karty interfejsów."""
        self._scroll_frame = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_button_color=BADGE_BG,
        )
        self._scroll_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=16)
        self._scroll_frame.grid_columnconfigure(0, weight=1)

    # ------------------------------------------------------------------
    # Odświeżanie danych
    # ------------------------------------------------------------------

    def refresh(self):
        """
        Uruchamia pobieranie danych w wątku tła.
        Blokuje przycisk podczas ładowania.
        """
        if self._loading:
            return
        self._loading = True
        self._refresh_btn.configure(state="disabled", text="  Ladowanie...")
        self._status_label.configure(text="Pobieranie danych...")
        self._clear_cards()
        threading.Thread(target=self._fetch_data, daemon=True).start()

    def _fetch_data(self):
        """Pobiera dane sieciowe (uruchamiane w wątku tła)."""
        try:
            data = get_network_interfaces()
        except Exception as e:
            data = []
            self.after(0, lambda: self._show_error(str(e)))
        self.after(0, lambda: self._on_data_ready(data))

    def _on_data_ready(self, interfaces: List[InterfaceInfo]):
        """Callback wykonywany w wątku UI po zakończeniu pobierania."""
        self._interfaces = interfaces
        self._loading = False
        self._refresh_btn.configure(state="normal", text="  Odswiez")
        self._status_label.configure(text="")

        if not interfaces:
            self._show_empty()
            return

        active = sum(1 for i in interfaces if i.is_active)
        total = len(interfaces)
        self._counter_label.configure(
            text=f"{active} aktywnych  /  {total} lacznie"
        )
        self._render_cards(interfaces)

    # ------------------------------------------------------------------
    # Karty interfejsów
    # ------------------------------------------------------------------

    def _clear_cards(self):
        """Usuwa wszystkie karty z widoku."""
        for widget in self._scroll_frame.winfo_children():
            widget.destroy()

    def _render_cards(self, interfaces: List[InterfaceInfo]):
        """Tworzy i wyświetla kartę dla każdego interfejsu."""
        for idx, iface in enumerate(interfaces):
            card = self._build_interface_card(self._scroll_frame, iface)
            card.grid(row=idx, column=0, sticky="ew", pady=(0, 12))

    def _build_interface_card(self, parent, iface: InterfaceInfo) -> ctk.CTkFrame:
        """
        Buduje pojedynczą kartę interfejsu sieciowego.

        Karta głównego interfejsu (is_default=True) otrzymuje niebieski
        akcent i etykietę "Domyslny".
        """
        # Wybierz kolor tła karty
        bg_color = CARD_HIGHLIGHT if iface.is_default else CARD_BG
        # CTkFrame nie akceptuje "transparent" dla border_color,
        # dlatego gdy brak obramowania ustawiamy border_width=0 (kolor jest wtedy ignorowany)
        border_width = 2 if iface.is_default else 0

        card = ctk.CTkFrame(
            parent,
            fg_color=bg_color,
            corner_radius=12,
            border_width=border_width,
            border_color=ACCENT_BORDER,   # Aktywne tylko gdy border_width > 0
        )
        card.grid_columnconfigure(0, weight=1)

        # --- Nagłówek karty ---
        self._build_card_header(card, iface)

        # --- Separator ---
        ctk.CTkFrame(
            card,
            height=1,
            fg_color=BADGE_BG,
        ).grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 10))

        # --- Siatka danych ---
        self._build_card_data_grid(card, iface)

        return card

    def _build_card_header(self, card: ctk.CTkFrame, iface: InterfaceInfo):
        """Nagłówek karty: ikona typu, nazwa, badge statusu, badge domyślnego."""
        header = ctk.CTkFrame(card, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 8))
        header.grid_columnconfigure(1, weight=1)

        # Ikona typu interfejsu (unicode, bez emoji)
        type_icons = {
            "Ethernet":  "[E]",
            "Wi-Fi":     "[W]",
            "VPN":       "[V]",
            "Wirtualny": "[=]",
            "Bluetooth": "[B]",
            "Loopback":  "[L]",
            "Inne":      "[?]",
        }
        icon_text = type_icons.get(iface.iface_type, "[?]")

        icon_label = ctk.CTkLabel(
            header,
            text=icon_text,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=ACCENT_BORDER if iface.is_active else INACTIVE_COLOR,
            width=36,
        )
        icon_label.grid(row=0, column=0, rowspan=2, sticky="w", padx=(0, 10))

        # Nazwa interfejsu
        ctk.CTkLabel(
            header,
            text=iface.name,
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=TEXT_PRIMARY,
            anchor="w",
        ).grid(row=0, column=1, sticky="w")

        # Opis sprzętowy
        ctk.CTkLabel(
            header,
            text=iface.description,
            font=ctk.CTkFont(size=11),
            text_color=TEXT_SECONDARY,
            anchor="w",
        ).grid(row=1, column=1, sticky="w")

        # Ramka na badge'e (po prawej)
        badges = ctk.CTkFrame(header, fg_color="transparent")
        badges.grid(row=0, column=2, rowspan=2, sticky="e")

        # Badge: status (Aktywny / Nieaktywny)
        status_color = SUCCESS_COLOR if iface.is_active else INACTIVE_COLOR
        _make_badge(badges, iface.status, status_color, col=0)

        # Badge: typ interfejsu
        _make_badge(badges, iface.iface_type, BADGE_BG, col=1, padx=(4, 0))

        # Badge: "Domyslny" tylko dla głównego interfejsu
        if iface.is_default:
            _make_badge(badges, "Domyslny", ACCENT_BORDER, col=2, padx=(4, 0))

    def _build_card_data_grid(self, card: ctk.CTkFrame, iface: InterfaceInfo):
        """
        Siatka danych: 3 kolumny x N wierszy.
        Każda komórka to etykieta opisowa + wartość.
        """
        grid_frame = ctk.CTkFrame(card, fg_color="transparent")
        grid_frame.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 14))

        # Definiujemy wszystkie pola do wyświetlenia
        dns_text = ", ".join(iface.dns_servers) if iface.dns_servers else "Brak"
        speed_text = f"{iface.speed_mbps} Mb/s" if iface.speed_mbps else "Nieznana"
        mtu_text = str(iface.mtu) if iface.mtu else "Brak danych"
        mask_text = (
            f"{iface.ipv4_mask} /{iface.ipv4_prefix}"
            if iface.ipv4_mask else "Brak"
        )
        ipv4_text = iface.ipv4 or "Brak"
        ipv6_text = iface.ipv6 or "Brak"
        gw_text = iface.gateway or "Brak"
        dhcp_text = "Tak (DHCP)" if iface.dhcp_enabled else "Nie (Statyczny)"

        fields = [
            # (etykieta, wartość, wyróżnij_wartość?)
            ("Adres IPv4",     ipv4_text,   iface.is_active and bool(iface.ipv4)),
            ("Maska podsieci", mask_text,   False),
            ("Brama domyslna", gw_text,     iface.is_default),
            ("Adres IPv6",     ipv6_text,   False),
            ("Serwery DNS",    dns_text,    False),
            ("Adres MAC",      iface.mac,   False),
            ("Predkosc lacza", speed_text,  False),
            ("MTU",            mtu_text,    False),
            ("DHCP",           dhcp_text,   False),
        ]

        # Wyświetl w siatce 3 kolumn
        for i, (label, value, highlight) in enumerate(fields):
            col_pair = (i % 3) * 2         # 0, 2, 4 – kolumny siatki
            row_num = i // 3

            cell = ctk.CTkFrame(grid_frame, fg_color="transparent")
            cell.grid(row=row_num, column=col_pair, sticky="w", padx=(0, 20), pady=3)

            ctk.CTkLabel(
                cell,
                text=label,
                font=ctk.CTkFont(size=10),
                text_color=TEXT_MUTED,
                anchor="w",
            ).pack(anchor="w")

            val_color = TEXT_VALUE if highlight else TEXT_PRIMARY
            ctk.CTkLabel(
                cell,
                text=value,
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=val_color,
                anchor="w",
                wraplength=200,
            ).pack(anchor="w")

    # ------------------------------------------------------------------
    # Stany specjalne
    # ------------------------------------------------------------------

    def _show_empty(self):
        """Wyświetla komunikat gdy nie wykryto żadnych interfejsów."""
        self._counter_label.configure(text="Nie wykryto interfejsow")
        ctk.CTkLabel(
            self._scroll_frame,
            text="Brak interfejsow sieciowych.\nSprawdz polaczenie i uprawnienia.",
            font=ctk.CTkFont(size=14),
            text_color=TEXT_MUTED,
        ).grid(row=0, column=0, pady=40)

    def _show_error(self, msg: str):
        """Wyświetla komunikat o błędzie."""
        self._counter_label.configure(text="Blad pobierania danych")
        ctk.CTkLabel(
            self._scroll_frame,
            text=f"Wystapil blad:\n{msg}",
            font=ctk.CTkFont(size=12),
            text_color=WARNING_COLOR,
        ).grid(row=0, column=0, pady=40)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _make_badge(
    parent: ctk.CTkFrame,
    text: str,
    color,
    col: int = 0,
    padx=(0, 0),
):
    """Tworzy mały badge (zaokrąglona etykieta) z podanym tekstem i kolorem."""
    badge = ctk.CTkFrame(
        parent,
        fg_color=color,
        corner_radius=6,
        height=24,
    )
    badge.grid(row=0, column=col, sticky="e", padx=padx)
    badge.grid_propagate(False)

    ctk.CTkLabel(
        badge,
        text=text,
        font=ctk.CTkFont(size=10, weight="bold"),
        text_color=("#ffffff", "#11111b"),
        padx=8,
        pady=2,
    ).pack(expand=True, fill="both")
