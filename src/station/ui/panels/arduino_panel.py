# src/station/ui/panels/arduino_panel.py
"""
ui/panels/arduino_panel.py
Panel de gestión de placas Arduino.
Soporta USB, Bluetooth y WiFi (UNO R4).
"""
from __future__ import annotations

import customtkinter as ctk

from domain.boards import Board
from ui.theme import FONT_TITLE, FONT_NORMAL, FONT_SMALL, COLORS

CONN_ICONS = {
    "usb": "🔌",
    "bluetooth": "📡",
    "wifi": "📶",
    "unknown": "❓"
}

CONN_NAMES = {
    "usb": "USB",
    "bluetooth": "Bluetooth",
    "wifi": "WiFi",
    "unknown": "Desconocido"
}


class ArduinoPanel(ctk.CTkFrame):
    def __init__(
            self,
            master,
            on_assign=None,
            on_unassign=None,
            on_read_now=None,
            on_scan_bluetooth=None,
            on_scan_wifi=None,  # NUEVO: escanear redes WiFi
            **kwargs
    ):
        super().__init__(master, **kwargs)

        self.grid_columnconfigure(0, weight=1, minsize=280)
        self.grid_columnconfigure(1, weight=3)
        self.grid_rowconfigure(0, weight=1)

        self._on_assign = on_assign
        self._on_unassign = on_unassign
        self._on_read_now = on_read_now
        self._on_scan_bluetooth = on_scan_bluetooth
        self._on_scan_wifi = on_scan_wifi  # NUEVO

        self._boards: list[Board] = []
        self._selected_board_id: str | None = None
        self._last_reading: dict = {}

        self._build_left()
        self._build_right()

    # ------------------------------------------------------------------
    # Panel izquierdo: lista de placas
    # ------------------------------------------------------------------
    def _build_left(self):
        left = ctk.CTkFrame(self)
        left.grid(row=0, column=0, sticky="nsew", padx=(8, 4), pady=8)
        left.grid_rowconfigure(1, weight=1)
        left.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(left, text="Placas Detectadas", font=FONT_TITLE).grid(
            row=0, column=0, pady=(10, 4), padx=10, sticky="w")

        # Lista scrollable
        self._list_frame = ctk.CTkScrollableFrame(left, label_text="")
        self._list_frame.grid(row=1, column=0, sticky="nsew", padx=6, pady=4)
        self._list_frame.grid_columnconfigure(0, weight=1)

        # Botones inferiores
        btn_frame = ctk.CTkFrame(left, fg_color="transparent")
        btn_frame.grid(row=2, column=0, pady=6, padx=6, sticky="ew")

        ctk.CTkButton(
            btn_frame, text="Buscar Bluetooth",
            font=FONT_SMALL,
            command=self._on_scan_bluetooth
        ).pack(side="left", padx=4, fill="x", expand=True)

        ctk.CTkButton(
            btn_frame, text="Buscar WiFi",
            font=FONT_SMALL,
            command=self._on_scan_wifi  # NUEVO
        ).pack(side="left", padx=4, fill="x", expand=True)

    # ------------------------------------------------------------------
    # Panel derecho: detalle + lecturas
    # ------------------------------------------------------------------
    def _build_right(self):
        right = ctk.CTkFrame(self)
        right.grid(row=0, column=1, sticky="nsew", padx=(4, 8), pady=8)
        right.grid_columnconfigure(0, weight=1)

        # Título
        self._lbl_title = ctk.CTkLabel(
            right, text="Selecciona una placa",
            font=FONT_TITLE, anchor="w"
        )
        self._lbl_title.grid(row=0, column=0, padx=12, pady=(12, 8), sticky="ew")

        # Información general
        row = 1
        self._info_labels = {}
        fields = [
            ("ID:", "id"),
            ("Conexión:", "conn"),
            ("Estado:", "status"),
            ("Parcela:", "parcela"),
            ("Sketch:", "sketch"),
        ]
        for label, key in fields:
            ctk.CTkLabel(right, text=label, font=FONT_NORMAL).grid(
                row=row, column=0, padx=12, pady=2, sticky="w")
            lbl = ctk.CTkLabel(right, text="—", font=FONT_NORMAL)
            lbl.grid(row=row, column=1, padx=12, pady=2, sticky="w")
            self._info_labels[key] = lbl
            row += 1

        # Separador
        ctk.CTkFrame(right, height=2, fg_color=COLORS["border"]).grid(
            row=row, column=0, columnspan=2, sticky="ew", padx=12, pady=8)
        row += 1

        # Lecturas del sensor
        ctk.CTkLabel(right, text="Lecturas del sensor", font=FONT_TITLE).grid(
            row=row, column=0, columnspan=2, padx=12, pady=(0, 8), sticky="w")
        row += 1

        self._reading_cards: dict[str, ctk.CTkLabel] = {}
        reading_frame = ctk.CTkFrame(right, fg_color="transparent")
        reading_frame.grid(row=row, column=0, columnspan=2, sticky="ew", padx=12)
        reading_frame.grid_columnconfigure((0, 1), weight=1)

        # Tarjeta temperatura
        temp_card = ctk.CTkFrame(reading_frame, corner_radius=8, border_width=1,
                                 border_color=COLORS["border"])
        temp_card.grid(row=0, column=0, padx=4, pady=4, sticky="nsew")
        ctk.CTkLabel(temp_card, text="Temperatura", font=FONT_SMALL).pack(pady=(8, 0))
        self._reading_cards["temp"] = ctk.CTkLabel(
            temp_card, text="—", font=("Roboto", 24, "bold"))
        self._reading_cards["temp"].pack(pady=(0, 8))
        ctk.CTkLabel(temp_card, text="°C", font=FONT_SMALL, text_color="gray").pack()

        # Tarjeta humedad
        hum_card = ctk.CTkFrame(reading_frame, corner_radius=8, border_width=1,
                                border_color=COLORS["border"])
        hum_card.grid(row=0, column=1, padx=4, pady=4, sticky="nsew")
        ctk.CTkLabel(hum_card, text="Humedad", font=FONT_SMALL).pack(pady=(8, 0))
        self._reading_cards["hum"] = ctk.CTkLabel(
            hum_card, text="—", font=("Roboto", 24, "bold"))
        self._reading_cards["hum"].pack(pady=(0, 8))
        ctk.CTkLabel(hum_card, text="%", font=FONT_SMALL, text_color="gray").pack()

        row += 1

        # Timestamp última lectura
        self._lbl_last_reading = ctk.CTkLabel(
            right, text="Sin datos", font=FONT_SMALL, text_color="gray")
        self._lbl_last_reading.grid(row=row, column=0, columnspan=2, padx=12, pady=8, sticky="w")
        row += 1

        # Botones de acción
        btn_frame = ctk.CTkFrame(right, fg_color="transparent")
        btn_frame.grid(row=row, column=0, columnspan=2, pady=8)

        self._btn_read = ctk.CTkButton(
            btn_frame, text="🔄 Leer ahora",
            font=FONT_SMALL,
            state="disabled",
            command=self._on_read_clicked
        )
        self._btn_read.pack(side="left", padx=4)

        self._btn_assign = ctk.CTkButton(
            btn_frame, text="Asignar a parcela",
            font=FONT_SMALL,
            command=self._on_assign_clicked
        )
        self._btn_assign.pack(side="left", padx=4)

        self._btn_unassign = ctk.CTkButton(
            btn_frame, text="Desasignar",
            font=FONT_SMALL,
            fg_color="#EF4444", hover_color="#B91C1C",
            command=self._on_unassign_clicked
        )
        self._btn_unassign.pack(side="left", padx=4)

        row += 1

        # Log de comunicación
        ctk.CTkLabel(right, text="Log", font=FONT_SMALL, text_color="gray").grid(
            row=row, column=0, padx=12, pady=(8, 0), sticky="w")
        row += 1

        self._log = ctk.CTkTextbox(
            right, height=100,
            font=FONT_SMALL,
            state="disabled", wrap="word"
        )
        self._log.grid(row=row, column=0, columnspan=2, padx=12, pady=(0, 12), sticky="nsew")
        right.grid_rowconfigure(row, weight=1)

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def set_boards(self, boards: list):
        self._boards = boards
        self._refresh_list()

    def update_board(self, board: Board):
        for i, b in enumerate(self._boards):
            if b.id == board.id:
                self._boards[i] = board
                break
        else:
            self._boards.append(board)

        if self._selected_board_id == board.id:
            self._update_detail(board)

        self._refresh_list()

    def update_reading(self, board_id: str, data: dict):
        if self._selected_board_id != board_id:
            return

        self._last_reading = data
        readings = data.get("data", {})

        for key, lbl in self._reading_cards.items():
            sensor_data = readings.get(key, {})
            if isinstance(sensor_data, dict) and "value" in sensor_data:
                val = sensor_data["value"]
                lbl.configure(text=f"{val:.1f}")
            else:
                lbl.configure(text="—")

        ts = data.get("ts", 0)
        self._lbl_last_reading.configure(
            text=f"Última lectura: {ts}ms",
            text_color=COLORS["accent"]
        )

        self._log_add(f"[RX] {board_id}: temp={readings.get('temp', {}).get('value', '?')} "
                      f"hum={readings.get('hum', {}).get('value', '?')}")

    # ------------------------------------------------------------------
    # Interno
    # ------------------------------------------------------------------

    def _refresh_list(self):
        for w in self._list_frame.winfo_children():
            w.destroy()

        for i, board in enumerate(self._boards):
            self._add_board_row(i, board)

    def _add_board_row(self, index: int, board: Board):
        row = ctk.CTkFrame(self._list_frame, corner_radius=6,
                           border_width=1, border_color=COLORS["border"])
        row.grid(row=index, column=0, sticky="ew", pady=2, padx=2)
        row.grid_columnconfigure(0, weight=1)

        icon = CONN_ICONS.get(board.conn, "❓")
        lbl_name = ctk.CTkLabel(
            row, text=f"{icon} {board.id}",
            font=FONT_NORMAL, anchor="w"
        )
        lbl_name.grid(row=0, column=0, padx=10, pady=(6, 0), sticky="w")

        status_color = COLORS["accent"] if board.status == "Conectada" else "gray"
        info = f"{CONN_NAMES.get(board.conn, board.conn)} • {board.status}"
        lbl_info = ctk.CTkLabel(
            row, text=info,
            font=FONT_SMALL, text_color=status_color, anchor="w"
        )
        lbl_info.grid(row=1, column=0, padx=10, pady=(0, 6), sticky="w")

        for w in (row, lbl_name, lbl_info):
            w.bind("<Button-1>", lambda e, bid=board.id: self._select_board(bid))

    def _select_board(self, board_id: str):
        self._selected_board_id = board_id
        board = next((b for b in self._boards if b.id == board_id), None)
        if board:
            self._update_detail(board)
        self._refresh_list()

    def _update_detail(self, board: Board):
        self._lbl_title.configure(text=f"Placa {board.id}")

        self._info_labels["id"].configure(text=board.id)
        self._info_labels["conn"].configure(
            text=f"{CONN_ICONS.get(board.conn, '❓')} {CONN_NAMES.get(board.conn, board.conn)}"
        )
        self._info_labels["status"].configure(text=board.status)
        self._info_labels["parcela"].configure(text=board.parcela or "Sin asignar")
        self._info_labels["sketch"].configure(text=board.conn_module or "Desconocido")

        is_connected = board.status == "Conectada"
        self._btn_read.configure(state="normal" if is_connected else "disabled")
        self._btn_assign.configure(state="normal" if not board.parcela else "disabled")
        self._btn_unassign.configure(state="normal" if board.parcela else "disabled")

        if not self._last_reading.get("board_id") == board.id:
            for lbl in self._reading_cards.values():
                lbl.configure(text="—")
            self._lbl_last_reading.configure(text="Sin datos", text_color="gray")

    def _on_read_clicked(self):
        if self._selected_board_id and self._on_read_now:
            self._on_read_now(self._selected_board_id)
            self._log_add(f"[TX] read → {self._selected_board_id}")

    def _on_assign_clicked(self):
        if self._selected_board_id and self._on_assign:
            self._on_assign(self._selected_board_id)

    def _on_unassign_clicked(self):
        if self._selected_board_id and self._on_unassign:
            self._on_unassign(self._selected_board_id)

    def _log_add(self, text: str):
        self._log.configure(state="normal")
        self._log.insert("end", text + "\n")
        self._log.see("end")
        self._log.configure(state="disabled")
