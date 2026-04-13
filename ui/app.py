"""
ui/app.py
=========
Główne okno aplikacji NetInfo.

Architektura:
  - Lewy sidebar (220 px, stały) – nawigacja między modułami
  - Prawy obszar treści                – wyświetla aktywny moduł

Jak dodać nowy moduł do nawigacji:
  1. Utwórz plik ui/modules/nowy_modul.py z klasą dziedziczącą ctk.CTkFrame
  2. Zaimportuj klasę poniżej
  3. Dodaj wpis do słownika MODULE_REGISTRY
  4. Dodaj wpis do listy NAV_ITEMS
"""

import customtkinter as ctk

from ui.modules.network_overview import NetworkOverviewModule
from ui.modules.network_scan import NetworkScanModule
from ui.modules.info_reference import InfoReferenceModule

# ---------------------------------------------------------------------------
# Rejestr modułów – klucz: id nawigacji, wartość: klasa CTkFrame
# ---------------------------------------------------------------------------
MODULE_REGISTRY = {
    "network": NetworkOverviewModule,
    "scan":    NetworkScanModule,
    "info":    InfoReferenceModule,
    # "monitor": TrafficMonitorModule,   # przykład: dodanie w przyszłości
    # "ports":   PortCheckerModule,
}

# ---------------------------------------------------------------------------
# Definicja pozycji nawigacji w sidebarze
# ---------------------------------------------------------------------------
# (klucz, etykieta_wyswietlana, dostepny_teraz)
NAV_ITEMS = [
    ("network", "Przeglad sieci",    True),
    ("scan",    "Skanowanie sieci",  True),
    ("info",    "Informacje",        True),
    ("monitor", "Monitor ruchu",     False),
    ("ports",   "Sprawdz porty",     False),
]


class NetInfoApp(ctk.CTk):
    """
    Klasa głównego okna aplikacji.
    Dziedziczy po ctk.CTk (okno CustomTkinter).
    """

    def __init__(self):
        super().__init__()

        # Domyślnie ciemny motyw
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self._dark_mode = True

        self._setup_window()
        self._build_layout()
        self._navigate("network")       # Załaduj domyślny moduł

    # ------------------------------------------------------------------
    # Konfiguracja okna
    # ------------------------------------------------------------------

    def _setup_window(self):
        """Ustawia tytuł, rozmiar i wyśrodkowanie okna."""
        self.title("NetInfo  |  Informacje Sieciowe")
        self.geometry("1100x720")
        self.minsize(900, 580)

        # Wyśrodkuj na ekranie
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - 1100) // 2
        y = max(0, (sh - 720) // 2 - 30)
        self.geometry(f"1100x720+{x}+{y}")

    # ------------------------------------------------------------------
    # Budowanie układu
    # ------------------------------------------------------------------

    def _build_layout(self):
        """Tworzy główny układ: sidebar (lewo) | content (prawo)."""
        self.configure(fg_color=("#eff1f5", "#1e1e2e"))
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()

        # Ramka obszaru głównego
        self._content_area = ctk.CTkFrame(
            self,
            fg_color=("#eff1f5", "#1e1e2e"),
            corner_radius=0,
        )
        self._content_area.grid(row=0, column=1, sticky="nsew")
        self._content_area.grid_columnconfigure(0, weight=1)
        self._content_area.grid_rowconfigure(0, weight=1)

        # Słownik buforowanych modułów: klucz → widget CTkFrame
        # Moduły są tworzone raz (przy pierwszym wejściu) i później tylko
        # ukrywane/pokazywane – dzięki temu stan (wpisane wartości) jest zachowany.
        self._module_cache: dict = {}
        self._active_nav_key = None

    def _build_sidebar(self):
        """Buduje panel boczny z nawigacją i przełącznikiem motywu."""
        sidebar = ctk.CTkFrame(
            self,
            width=220,
            fg_color=("#dce0e8", "#181825"),
            corner_radius=0,
        )
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)
        sidebar.grid_columnconfigure(0, weight=1)
        # Wiersz 3 (nav_frame) rozciąga się – "wypycha" dolną część na dół
        sidebar.grid_rowconfigure(3, weight=1)

        # --- Logo ---
        logo_frame = ctk.CTkFrame(sidebar, fg_color="transparent", height=70)
        logo_frame.grid(row=0, column=0, sticky="ew", padx=16, pady=(18, 0))
        logo_frame.grid_propagate(False)

        ctk.CTkLabel(
            logo_frame,
            text="NetInfo",
            font=ctk.CTkFont(size=26, weight="bold"),
            text_color=("#1e66f5", "#89b4fa"),
        ).pack(side="left")

        ctk.CTkLabel(
            logo_frame,
            text=" v1.0",
            font=ctk.CTkFont(size=11),
            text_color=("#9ca0b0", "#585b70"),
        ).pack(side="left", pady=(10, 0))

        # --- Separator ---
        ctk.CTkFrame(
            sidebar,
            height=1,
            fg_color=("#ccd0da", "#313244"),
        ).grid(row=1, column=0, sticky="ew", padx=16, pady=(10, 8))

        # --- Nagłówek sekcji ---
        ctk.CTkLabel(
            sidebar,
            text="  NARZEDZIA",
            font=ctk.CTkFont(size=9, weight="bold"),
            text_color=("#9ca0b0", "#585b70"),
            anchor="w",
        ).grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 4))

        # --- Przyciski nawigacji ---
        nav_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        nav_frame.grid(row=3, column=0, sticky="nsew", padx=8)
        nav_frame.grid_columnconfigure(0, weight=1)

        self._nav_buttons = {}

        for row_idx, (key, label, available) in enumerate(NAV_ITEMS):
            btn = ctk.CTkButton(
                nav_frame,
                text=f"  {label}",
                anchor="w",
                height=42,
                corner_radius=8,
                font=ctk.CTkFont(size=13),
                fg_color="transparent",
                text_color=(
                    ("#4c4f69", "#cdd6f4") if available
                    else ("#9ca0b0", "#45475a")
                ),
                hover_color=(
                    ("#d0d5e8", "#313244") if available
                    else ("#dce0e8", "#181825")   # Kolor sidebara – wizualnie brak efektu hover
                ),
                state="normal" if available else "disabled",
                command=(lambda k=key: self._navigate(k)) if available else None,
            )
            btn.grid(row=row_idx, column=0, sticky="ew", pady=2)
            self._nav_buttons[key] = btn

        # Informacja o planowanych modułach
        ctk.CTkLabel(
            nav_frame,
            text="  Wkrotce dostepne...",
            font=ctk.CTkFont(size=10),
            text_color=("#9ca0b0", "#45475a"),
            anchor="w",
        ).grid(row=len(NAV_ITEMS), column=0, sticky="w", padx=8, pady=(8, 0))

        # --- Dolna część: separator + przełącznik motywu ---
        bottom = ctk.CTkFrame(sidebar, fg_color="transparent")
        bottom.grid(row=4, column=0, sticky="ew", padx=16, pady=(0, 16))
        bottom.grid_columnconfigure(0, weight=1)

        ctk.CTkFrame(
            bottom,
            height=1,
            fg_color=("#ccd0da", "#313244"),
        ).grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))

        ctk.CTkLabel(
            bottom,
            text="Ciemny motyw",
            font=ctk.CTkFont(size=12),
            text_color=("#6c6f85", "#a6adc8"),
        ).grid(row=1, column=0, sticky="w")

        self._theme_switch = ctk.CTkSwitch(
            bottom,
            text="",
            width=46,
            command=self._toggle_theme,
        )
        self._theme_switch.grid(row=1, column=1, sticky="e")
        self._theme_switch.select()        # domyślnie włączony (ciemny)

    # ------------------------------------------------------------------
    # Nawigacja między modułami
    # ------------------------------------------------------------------

    def _navigate(self, key: str):
        """
        Przełącza widoczny moduł.

        Strategia buforowania:
          - Moduł jest tworzony tylko raz (przy pierwszym wejściu).
          - Przy opuszczaniu: grid_remove() – widget znika z ekranu, ale żyje w pamięci.
          - Przy powrocie: grid() – widget wraca z dokładnie tym samym stanem (wpisane
            wartości, wyniki skanowania, ustawienia checkboxów itp.).
        """
        if key == self._active_nav_key:
            return

        # --- Aktualizuj wygląd przycisków nawigacji ---
        for nav_key, btn in self._nav_buttons.items():
            if nav_key == key:
                btn.configure(
                    fg_color=("#d0d5e8", "#313244"),
                    text_color=("#1e66f5", "#89b4fa"),
                )
            else:
                if btn.cget("state") == "normal":
                    btn.configure(
                        fg_color="transparent",
                        text_color=("#4c4f69", "#cdd6f4"),
                    )

        # --- Ukryj aktualnie wyświetlany moduł ---
        if self._active_nav_key and self._active_nav_key in self._module_cache:
            self._module_cache[self._active_nav_key].grid_remove()

        # --- Pokaż lub utwórz docelowy moduł ---
        module_class = MODULE_REGISTRY.get(key)
        if not module_class:
            return

        if key not in self._module_cache:
            # Pierwsze wejście – utwórz instancję i zapamiętaj
            widget = module_class(self._content_area)
            widget.grid(row=0, column=0, sticky="nsew")
            self._module_cache[key] = widget
        else:
            # Kolejne wejście – przywróć zapisany widget
            self._module_cache[key].grid(row=0, column=0, sticky="nsew")

        self._active_nav_key = key

    # ------------------------------------------------------------------
    # Przełączanie motywu
    # ------------------------------------------------------------------

    def _toggle_theme(self):
        """Przełącza między ciemnym a jasnym motywem CustomTkinter."""
        self._dark_mode = bool(self._theme_switch.get())
        mode = "dark" if self._dark_mode else "light"
        ctk.set_appearance_mode(mode)
