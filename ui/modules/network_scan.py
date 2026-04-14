"""
ui/modules/network_scan.py
============================
Moduł "Skanowanie sieci" – wykrywa aktywne urządzenia w podanym zakresie.

Tryby wejścia:
  - Sieć CIDR:  wpisz adres np. "192.168.1.0" i maskę "/24"
  - Zakres IP:  wpisz "od" i "do", np. 192.168.1.1 – 192.168.1.254

Wyniki pokazują się w czasie rzeczywistym (hosty dodawane na bieżąco),
a po zakończeniu tabela jest przerysowana z kompletnymi danymi (MAC + hostname).
"""

import queue
import threading
import customtkinter as ctk
from typing import List, Optional

from core.scanner import (
    COMMON_PORTS,
    ScanResult,
    parse_targets,
    validate_target_size,
    scan_network,
)


# ---------------------------------------------------------------------------
# Paleta kolorów (krotki: jasny / ciemny – format CTk)
# ---------------------------------------------------------------------------
TEXT_PRIMARY   = ("#4c4f69", "#cdd6f4")
TEXT_SECONDARY = ("#6c6f85", "#a6adc8")
TEXT_MUTED     = ("#9ca0b0", "#6c7086")
TEXT_VALUE     = ("#1e66f5", "#89b4fa")
SUCCESS_COLOR  = ("#40a02b", "#a6e3a1")
WARNING_COLOR  = ("#df8e1d", "#f9e2af")
ERROR_COLOR    = ("#d20f39", "#f38ba8")
CARD_BG        = ("#e6e9f0", "#313244")
HEADER_BG      = ("#ccd0da", "#45475a")
ROW_EVEN_BG    = ("#dce0e8", "#2a2a3e")
ROW_ODD_BG     = ("#e6e9f0", "#313244")

# Szerokości kolumn tabeli (proporcjonalne)
COL_WIDTHS = {
    0: 40,   # #
    1: 150,  # Adres IP
    2: 200,  # Nazwa hosta
    3: 160,  # Adres MAC
    4: 90,   # Ping (ms)
}


class NetworkScanModule(ctk.CTkFrame):
    """Panel skanowania sieci."""

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # Stan skanowania
        self._scan_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._result_queue: queue.Queue = queue.Queue()
        self._live_count = 0      # liczba wykrytych hostów w trakcie skanowania
        self._row_count = 0       # liczba wierszy w tabeli

        self._build_header()
        self._build_input_panel()
        self._build_results_panel()

    # ------------------------------------------------------------------
    # Budowanie UI – sekcje stałe
    # ------------------------------------------------------------------

    def _build_header(self):
        hdr = ctk.CTkFrame(self, fg_color="transparent", height=60)
        hdr.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 0))
        hdr.grid_propagate(False)
        hdr.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            hdr,
            text="Skanowanie sieci",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            hdr,
            text="Wykrywanie aktywnych urządzeń: ICMP Ping  →  ARP (MAC)  →  Reverse DNS",
            font=ctk.CTkFont(size=11),
            text_color=TEXT_MUTED,
        ).grid(row=1, column=0, sticky="w")

    def _build_input_panel(self):
        """Karta sterowania: wybór trybu, pola wejściowe, timeout, przyciski."""
        panel = ctk.CTkFrame(self, fg_color=CARD_BG, corner_radius=12)
        panel.grid(row=1, column=0, sticky="ew", padx=20, pady=(12, 0))
        panel.grid_columnconfigure(0, weight=1)

        # --- Wiersz 1: wybór trybu ---
        row1 = ctk.CTkFrame(panel, fg_color="transparent")
        row1.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 6))

        ctk.CTkLabel(
            row1,
            text="Tryb skanowania:",
            font=ctk.CTkFont(size=12),
            text_color=TEXT_SECONDARY,
        ).pack(side="left", padx=(0, 12))

        self._mode_var = ctk.StringVar(value="Sieć CIDR")
        self._mode_btn = ctk.CTkSegmentedButton(
            row1,
            values=["Sieć CIDR", "Zakres IP"],
            variable=self._mode_var,
            font=ctk.CTkFont(size=12),
            height=32,
            command=self._on_mode_change,
        )
        self._mode_btn.pack(side="left")

        # --- Wiersz 2: pola wejściowe (zmieniają się z trybem) ---
        self._input_frame = ctk.CTkFrame(panel, fg_color="transparent")
        self._input_frame.grid(row=1, column=0, sticky="ew", padx=16, pady=2)
        self._build_cidr_inputs()

        # --- Wiersz 3: timeout ---
        row3 = ctk.CTkFrame(panel, fg_color="transparent")
        row3.grid(row=2, column=0, sticky="ew", padx=16, pady=(6, 2))

        ctk.CTkLabel(
            row3,
            text="Timeout pinga:",
            font=ctk.CTkFont(size=11),
            text_color=TEXT_MUTED,
        ).pack(side="left", padx=(0, 8))

        self._timeout_var = ctk.IntVar(value=500)

        self._timeout_val_label = ctk.CTkLabel(
            row3,
            text="500 ms",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=TEXT_VALUE,
            width=55,
        )
        self._timeout_val_label.pack(side="left", padx=(0, 6))

        ctk.CTkSlider(
            row3,
            from_=100,
            to=2000,
            number_of_steps=19,
            variable=self._timeout_var,
            width=180,
            command=self._on_timeout_change,
        ).pack(side="left")

        ctk.CTkLabel(
            row3,
            text="(krócej = szybciej, ale może przeoczyć wolne hosty)",
            font=ctk.CTkFont(size=10),
            text_color=TEXT_MUTED,
        ).pack(side="left", padx=(10, 0))

        # --- Wiersz 3b: opcja skanowania portów ---
        row3b = ctk.CTkFrame(panel, fg_color="transparent")
        row3b.grid(row=3, column=0, sticky="ew", padx=16, pady=(2, 4))

        self._port_scan_var = ctk.BooleanVar(value=False)
        self._port_scan_cb = ctk.CTkCheckBox(
            row3b,
            text="Skanuj popularne porty TCP",
            variable=self._port_scan_var,
            font=ctk.CTkFont(size=12),
            command=self._on_port_scan_toggle,
        )
        self._port_scan_cb.pack(side="left")

        # Lista portów do sprawdzenia (tooltip-like)
        port_names = ", ".join(
            f"{port}/{name}" for port, name in COMMON_PORTS.items()
        )
        ctk.CTkLabel(
            row3b,
            text=f"  ({len(COMMON_PORTS)} portów: {port_names})",
            font=ctk.CTkFont(size=10),
            text_color=TEXT_MUTED,
            wraplength=550,
            justify="left",
        ).pack(side="left", padx=(6, 0))

        # Timeout połączenia TCP per port
        self._port_timeout_frame = ctk.CTkFrame(panel, fg_color="transparent")
        self._port_timeout_frame.grid(row=4, column=0, sticky="ew", padx=16, pady=(0, 4))
        self._port_timeout_frame.grid_remove()  # domyślnie ukryty

        ctk.CTkLabel(
            self._port_timeout_frame,
            text="Timeout portu:",
            font=ctk.CTkFont(size=11),
            text_color=TEXT_MUTED,
        ).pack(side="left", padx=(0, 8))

        self._port_timeout_var = ctk.IntVar(value=400)
        self._port_timeout_label = ctk.CTkLabel(
            self._port_timeout_frame,
            text="400 ms",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=TEXT_VALUE,
            width=55,
        )
        self._port_timeout_label.pack(side="left", padx=(0, 6))

        ctk.CTkSlider(
            self._port_timeout_frame,
            from_=100,
            to=1000,
            number_of_steps=9,
            variable=self._port_timeout_var,
            width=160,
            command=lambda v: self._port_timeout_label.configure(text=f"{int(v)} ms"),
        ).pack(side="left")

        ctk.CTkLabel(
            self._port_timeout_frame,
            text="  (niski timeout = szybciej, ale może przeoczyć wolne usługi)",
            font=ctk.CTkFont(size=10),
            text_color=TEXT_MUTED,
        ).pack(side="left")

        # --- Wiersz 5: przyciski + komunikat błędu ---
        row4 = ctk.CTkFrame(panel, fg_color="transparent")
        row4.grid(row=5, column=0, sticky="ew", padx=16, pady=(8, 14))

        self._scan_btn = ctk.CTkButton(
            row4,
            text="  Skanuj",
            width=130,
            height=38,
            corner_radius=8,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._on_scan_click,
        )
        self._scan_btn.pack(side="left")

        self._stop_btn = ctk.CTkButton(
            row4,
            text="  Zatrzymaj",
            width=130,
            height=38,
            corner_radius=8,
            font=ctk.CTkFont(size=13),
            fg_color=("#d0d5e8", "#45475a"),
            text_color=TEXT_PRIMARY,
            hover_color=("#c0c5d8", "#585b70"),
            state="disabled",
            command=self._on_stop_click,
        )
        self._stop_btn.pack(side="left", padx=(8, 0))

        self._msg_label = ctk.CTkLabel(
            row4,
            text="",
            font=ctk.CTkFont(size=11),
            text_color=ERROR_COLOR,
            anchor="w",
        )
        self._msg_label.pack(side="left", padx=(12, 0), fill="x", expand=True)

    def _build_results_panel(self):
        """Sekcja wyników: progress bar + etykieta statusu + tabela."""
        outer = ctk.CTkFrame(self, fg_color="transparent")
        outer.grid(row=2, column=0, sticky="nsew", padx=20, pady=(12, 16))
        outer.grid_columnconfigure(0, weight=1)
        outer.grid_rowconfigure(2, weight=1)

        # Pasek postępu
        self._progress = ctk.CTkProgressBar(outer, height=8, corner_radius=4)
        self._progress.set(0)
        self._progress.grid(row=0, column=0, sticky="ew", pady=(0, 6))

        # Etykieta statusu / podsumowanie
        self._status_label = ctk.CTkLabel(
            outer,
            text="Gotowy do skanowania. Wpisz adres sieci i kliknij Skanuj.",
            font=ctk.CTkFont(size=11),
            text_color=TEXT_MUTED,
            anchor="w",
        )
        self._status_label.grid(row=1, column=0, sticky="w", pady=(0, 8))

        # Ramka tabeli (nagłówek + przewijana lista)
        table_frame = ctk.CTkFrame(outer, fg_color="transparent")
        table_frame.grid(row=2, column=0, sticky="nsew")
        table_frame.grid_columnconfigure(0, weight=1)
        table_frame.grid_rowconfigure(1, weight=1)

        self._table_frame = table_frame   # zapamiętaj do przebudowania nagłówka
        self._build_table_header(table_frame, show_ports=False)

        # Przewijana lista wyników
        self._scroll = ctk.CTkScrollableFrame(
            table_frame,
            fg_color=ROW_ODD_BG,
            corner_radius=0,
            scrollbar_button_color=HEADER_BG,
        )
        self._scroll.grid(row=1, column=0, sticky="nsew")
        self._scroll.grid_columnconfigure(0, weight=1)

        # Placeholder (widoczny gdy brak wyników)
        self._placeholder = ctk.CTkLabel(
            self._scroll,
            text="Wyniki pojawią się tutaj po zakończeniu skanowania.",
            font=ctk.CTkFont(size=12),
            text_color=TEXT_MUTED,
        )
        self._placeholder.pack(pady=50)

    def _build_table_header(self, parent, show_ports: bool = False):
        """
        Wiersz nagłówkowy tabeli.
        show_ports=True dodaje kolumnę "Otwarte porty".
        Przechowuje referencję jako self._table_header – przy każdym nowym skanie
        nagłówek jest odbudowywany, by pasował do aktualnego trybu.
        """
        if hasattr(self, "_table_header") and self._table_header.winfo_exists():
            self._table_header.destroy()

        hdr = ctk.CTkFrame(
            parent,
            fg_color=HEADER_BG,
            corner_radius=8,
            height=36,
        )
        hdr.grid(row=0, column=0, sticky="ew", pady=(0, 2))
        hdr.grid_propagate(False)
        self._table_header = hdr

        columns = [
            ("#",             40,  "center"),
            ("Adres IP",      150, "w"),
            ("Nazwa hosta",   190, "w"),
            ("Adres MAC",     155, "w"),
            ("Ping (ms)",     80,  "w"),
        ]
        if show_ports:
            columns.append(("Otwarte porty", 220, "w"))

        for col, (label, width, anchor) in enumerate(columns):
            ctk.CTkLabel(
                hdr,
                text=label,
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=TEXT_SECONDARY,
                width=width,
                anchor=anchor,
            ).grid(row=0, column=col, padx=(10, 4), pady=4, sticky="w")

    # ------------------------------------------------------------------
    # Pola wejściowe – dwa tryby
    # ------------------------------------------------------------------

    def _build_cidr_inputs(self):
        """Pola dla trybu CIDR: [adres IP] / [maska]."""
        for w in self._input_frame.winfo_children():
            w.destroy()

        ctk.CTkLabel(
            self._input_frame,
            text="Adres sieci:",
            font=ctk.CTkFont(size=12),
            text_color=TEXT_SECONDARY,
        ).pack(side="left", padx=(0, 8))

        self._cidr_ip = ctk.CTkEntry(
            self._input_frame,
            placeholder_text="np. 192.168.1.0",
            width=175,
            height=34,
            font=ctk.CTkFont(size=12),
        )
        self._cidr_ip.pack(side="left")

        ctk.CTkLabel(
            self._input_frame,
            text=" /",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=TEXT_SECONDARY,
        ).pack(side="left", padx=(6, 4))

        self._cidr_prefix = ctk.CTkEntry(
            self._input_frame,
            placeholder_text="24",
            width=56,
            height=34,
            font=ctk.CTkFont(size=12),
        )
        self._cidr_prefix.pack(side="left")

        ctk.CTkLabel(
            self._input_frame,
            text="  bity maski (1–32)",
            font=ctk.CTkFont(size=10),
            text_color=TEXT_MUTED,
        ).pack(side="left")

    def _build_range_inputs(self):
        """Pola dla trybu zakres IP: [od] – [do]."""
        for w in self._input_frame.winfo_children():
            w.destroy()

        ctk.CTkLabel(
            self._input_frame,
            text="Od:",
            font=ctk.CTkFont(size=12),
            text_color=TEXT_SECONDARY,
        ).pack(side="left", padx=(0, 6))

        self._range_start = ctk.CTkEntry(
            self._input_frame,
            placeholder_text="192.168.1.1",
            width=165,
            height=34,
            font=ctk.CTkFont(size=12),
        )
        self._range_start.pack(side="left")

        ctk.CTkLabel(
            self._input_frame,
            text="  Do:",
            font=ctk.CTkFont(size=12),
            text_color=TEXT_SECONDARY,
        ).pack(side="left", padx=(12, 6))

        self._range_end = ctk.CTkEntry(
            self._input_frame,
            placeholder_text="192.168.1.254",
            width=165,
            height=34,
            font=ctk.CTkFont(size=12),
        )
        self._range_end.pack(side="left")

    # ------------------------------------------------------------------
    # Obsługa zdarzeń
    # ------------------------------------------------------------------

    def _on_mode_change(self, mode: str):
        if mode == "Sieć CIDR":
            self._build_cidr_inputs()
        else:
            self._build_range_inputs()

    def _on_timeout_change(self, value):
        self._timeout_val_label.configure(text=f"{int(value)} ms")

    def _on_port_scan_toggle(self):
        """Pokazuje lub ukrywa opcje timeoutu portów."""
        if self._port_scan_var.get():
            self._port_timeout_frame.grid()
        else:
            self._port_timeout_frame.grid_remove()

    def _get_target_text(self) -> str:
        """Odczytuje pola wejściowe i zwraca tekst zakresu."""
        mode = self._mode_var.get()
        if mode == "Sieć CIDR":
            ip = self._cidr_ip.get().strip()
            prefix = self._cidr_prefix.get().strip()
            return f"{ip}/{prefix}" if ip and prefix else ip
        else:
            start = self._range_start.get().strip()
            end = self._range_end.get().strip()
            return f"{start}-{end}" if start and end else start

    def _on_scan_click(self):
        """Waliduje wejście i uruchamia skanowanie."""
        self._msg_label.configure(text="", text_color=ERROR_COLOR)

        target_text = self._get_target_text()
        targets, error = parse_targets(target_text)
        if error:
            self._msg_label.configure(text=f"  {error}")
            return

        # Sprawdź rozmiar zakresu
        size_check = validate_target_size(len(targets))
        if size_check:
            kind, msg = size_check.split(":", 1)
            if kind == "error":
                self._msg_label.configure(text=f"  {msg}")
                return
            # Ostrzeżenie – wyświetl i pozwól kontynuować
            self._msg_label.configure(
                text=f"  Uwaga: {msg}",
                text_color=WARNING_COLOR,
            )

        # Przygotuj UI do skanowania
        self._clear_table()
        self._live_count = 0
        self._row_count = 0
        self._progress.set(0)
        self._status_label.configure(
            text=f"Skanowanie {len(targets)} adresów...",
            text_color=TEXT_MUTED,
        )
        self._scan_btn.configure(state="disabled")
        self._stop_btn.configure(state="normal")

        # Zapamiętaj czy skanujemy porty (do decyzji o kolumnie w tabeli)
        self._do_ports = self._port_scan_var.get()

        # Uruchom skanowanie w wątku tła
        self._stop_event.clear()
        self._scan_thread = threading.Thread(
            target=scan_network,
            args=(targets, self._result_queue, self._stop_event),
            kwargs={
                "timeout_ms":     self._timeout_var.get(),
                "max_workers":    min(150, max(10, len(targets))),
                "do_port_scan":   self._do_ports,
                "port_timeout_ms": self._port_timeout_var.get(),
            },
            daemon=True,
        )
        self._scan_thread.start()
        self._poll_queue()

    def _on_stop_click(self):
        """Zatrzymuje aktywne skanowanie."""
        self._stop_event.set()
        self._stop_btn.configure(state="disabled")
        self._status_label.configure(
            text="Zatrzymywanie... (czekam na koniec aktywnych pingów)",
            text_color=WARNING_COLOR,
        )

    # ------------------------------------------------------------------
    # Polling kolejki wyników (wątek UI)
    # ------------------------------------------------------------------

    def _poll_queue(self):
        """
        Sprawdza kolejkę wyników co 100 ms.
        Każde wywołanie przetwarza wszystkie dostępne wiadomości.
        """
        try:
            while True:
                msg = self._result_queue.get(block=False)
                kind = msg[0]

                if kind == "progress":
                    _, scanned, total = msg
                    self._progress.set(scanned / total)
                    self._status_label.configure(
                        text=(
                            f"Skanowanie: {scanned}/{total}"
                            f"  |  Wykryto hostów: {self._live_count}"
                        ),
                        text_color=TEXT_MUTED,
                    )

                elif kind == "found_live":
                    _, result = msg
                    self._live_count += 1
                    self._add_row(result, partial=True)

                elif kind == "status":
                    _, text = msg
                    self._status_label.configure(text=text, text_color=TEXT_MUTED)

                elif kind == "done":
                    _, final = msg
                    self._on_scan_finished(final)
                    return  # Kończymy polling

        except queue.Empty:
            pass

        self.after(100, self._poll_queue)

    # ------------------------------------------------------------------
    # Zarządzanie tabelą
    # ------------------------------------------------------------------

    def _clear_table(self, rebuild_header: bool = False):
        """
        Usuwa wszystkie wiersze z tabeli.
        rebuild_header=True przebudowuje nagłówek (wywoływane przed finalnym renderem).
        """
        for w in self._scroll.winfo_children():
            w.destroy()
        self._row_count = 0
        self._live_count = 0
        if rebuild_header:
            self._build_table_header(self._table_frame, show_ports=getattr(self, "_do_ports", False))

    def _add_row(self, result: ScanResult, partial: bool = False):
        """
        Dodaje jeden wiersz do tabeli wyników.
        partial=True: dane tymczasowe podczas skanowania (bez MAC, hostname, portów).
        partial=False: kompletne dane finalne.
        """
        self._row_count += 1
        row_num = self._row_count
        bg = ROW_EVEN_BG if row_num % 2 == 0 else ROW_ODD_BG

        ping_text  = f"{int(result.response_ms)} ms" if result.response_ms >= 0 else "-"
        hostname   = "..." if partial else result.hostname
        mac        = "..." if partial else result.mac
        show_ports = getattr(self, "_do_ports", False)

        # Formatowanie listy otwartych portów: "SSH(22), HTTP(80), HTTPS(443)"
        if partial or not show_ports:
            ports_text = "..." if (partial and show_ports) else ""
        elif result.open_ports:
            parts = []
            for p in result.open_ports:
                name = COMMON_PORTS.get(p, "?")
                parts.append(f"{name}({p})")
            ports_text = ", ".join(parts)
        else:
            ports_text = "brak"

        row = ctk.CTkFrame(
            self._scroll,
            fg_color=bg,
            corner_radius=0,
            height=36,
        )
        row.pack(fill="x", pady=1)
        row.pack_propagate(False)

        # Kolumny stałe: # | IP | Hostname | MAC | Ping
        data = [
            (str(row_num),  40,  "center", TEXT_MUTED),
            (result.ip,     150, "w",      TEXT_VALUE),
            (hostname,      190, "w",      TEXT_PRIMARY),
            (mac,           155, "w",      TEXT_SECONDARY),
            (ping_text,     80,  "w",      SUCCESS_COLOR),
        ]
        for text, width, anchor, color in data:
            ctk.CTkLabel(
                row,
                text=text,
                font=ctk.CTkFont(size=12),
                text_color=color,
                width=width,
                anchor=anchor,
            ).pack(side="left", padx=(10, 0))

        # Kolumna portów (tylko gdy włączona opcja)
        if show_ports:
            port_color = TEXT_VALUE if result.open_ports else TEXT_MUTED
            ctk.CTkLabel(
                row,
                text=ports_text,
                font=ctk.CTkFont(size=11),
                text_color=port_color,
                width=220,
                anchor="w",
                wraplength=215,
            ).pack(side="left", padx=(10, 0))

    def _on_scan_finished(self, results: List[ScanResult]):
        """
        Callback po zakończeniu skanowania.
        Przerysowuje tabelę z kompletnymi danymi (MAC + nazwy hostów).
        """
        self._scan_btn.configure(state="normal")
        self._stop_btn.configure(state="disabled")
        self._progress.set(1.0)

        stopped = self._stop_event.is_set()
        count = len(results)

        if count == 0:
            suffix = " (skanowanie zatrzymane)" if stopped else ""
            self._status_label.configure(
                text=f"Nie wykryto żadnych aktywnych hostów.{suffix}",
                text_color=TEXT_MUTED,
            )
        else:
            suffix = f"  (zatrzymano po {self._live_count} pingach)" if stopped else ""
            self._status_label.configure(
                text=f"Znaleziono {count} aktywnych hostów{suffix}",
                text_color=SUCCESS_COLOR,
            )

        # Przerysuj tabelę z pełnymi danymi (zamienia "..." na wartości).
        # rebuild_header=True aktualizuje nagłówek – dodaje/usuwa kolumnę portów.
        self._clear_table(rebuild_header=True)
        for r in results:
            self._add_row(r, partial=False)

        if not results:
            ctk.CTkLabel(
                self._scroll,
                text="Brak odpowiedzi. Sprawdź zakres i timeout.",
                font=ctk.CTkFont(size=12),
                text_color=TEXT_MUTED,
            ).pack(pady=40)
