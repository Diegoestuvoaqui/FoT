"""
ui/panels/arduino_panel.py
Panel de gestión de Arduinos.
Izquierda: lista de placas con estado, asignación, firmware.
Derecha: detalle de la placa seleccionada (sensores, actuadores, módulos).
"""
from __future__ import annotations

import customtkinter as ctk

from domain.boards import Board
from ui.theme import FONT_TITLE, FONT_NORMAL, FONT_SMALL, COLORS

# Tipos de conexión
CONN_ICONS = {
    "usb": "🔌 USB",
    "wifi": "📶 WiFi",
    "bluetooth": "📡 BT",
    "unknown": "❓"
}


class ArduinoPanel(ctk.CTkFrame):
    def __init__(
            self,
            master,
            on_assign=None,
            on_unassign=None,
            on_firmware_update=None,
            on_scan_bluetooth=None,
            **kwargs
    ):
        super().__init__(master, **kwargs)

        self.grid_columnconfigure(0, weight=1, minsize=300)
        self.grid_columnconfigure(1, weight=3)
        self.grid_rowconfigure(0, weight=1)

        # Callbacks
        self._on_assign = on_assign  # placa_id -> abre diálogo
        self._on_unassign = on_unassign  # placa_id -> desasigna
        self._on_firmware_update = on_firmware_update  # placa_id -> abre diálogo firmware
        self._on_scan_bluetooth = on_scan_bluetooth  # función para escanear BT

        self._boards: list[Board] = []  # lista de objetos Board (definidos abajo)
        self._selected_board_id = None

        self._build_left()
        self._build_right()

    # ------------------------------------------------------------------
    # Panel izquierdo: lista de placas + botón escanear BT
    # ------------------------------------------------------------------
    def _build_left(self):
        left = ctk.CTkFrame(self)
        left.grid(row=0, column=0, sticky="nsew", padx=(8, 4), pady=8)
        left.grid_rowconfigure(1, weight=1)
        left.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(left, text="Placas Arduino", font=FONT_TITLE).grid(
            row=0, column=0, pady=(10, 4), padx=10, sticky="w")

        # Lista scrollable
        self._list_frame = ctk.CTkScrollableFrame(left, label_text="")
        self._list_frame.grid(row=1, column=0, sticky="nsew", padx=6, pady=4)
        self._list_frame.grid_columnconfigure(0, weight=1)

        # Botones inferiores
        btn_frame = ctk.CTkFrame(left, fg_color="transparent")
        btn_frame.grid(row=2, column=0, pady=6, padx=6, sticky="ew")
        ctk.CTkButton(
            btn_frame, text="Buscar placas Bluetooth",
            font=FONT_SMALL,
            command=self._on_scan_bluetooth
        ).pack(side="left", padx=4, fill="x", expand=True)

    # ------------------------------------------------------------------
    # Panel derecho: detalle de placa seleccionada
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
            ("Parcela asignada:", "parcela"),
            ("Firmware:", "firmware"),
        ]
        for label, key in fields:
            ctk.CTkLabel(right, text=label, font=FONT_NORMAL).grid(
                row=row, column=0, padx=12, pady=2, sticky="w")
            lbl = ctk.CTkLabel(right, text="—", font=FONT_NORMAL)
            lbl.grid(row=row, column=1, padx=12, pady=2, sticky="w")
            self._info_labels[key] = lbl
            row += 1

        # Botones de acción
        btn_frame = ctk.CTkFrame(right, fg_color="transparent")
        btn_frame.grid(row=row, column=0, columnspan=2, pady=8)
        self._btn_assign = ctk.CTkButton(
            btn_frame, text="Asignar a parcela",
            font=FONT_SMALL,
            command=lambda: self._on_assign(self._selected_board_id) if self._selected_board_id else None
        )
        self._btn_assign.pack(side="left", padx=4)
        self._btn_unassign = ctk.CTkButton(
            btn_frame, text="Desasignar",
            font=FONT_SMALL,
            fg_color="#EF4444", hover_color="#B91C1C",
            command=lambda: self._on_unassign(self._selected_board_id) if self._selected_board_id else None
        )
        self._btn_unassign.pack(side="left", padx=4)
        self._btn_firmware = ctk.CTkButton(
            btn_frame, text="Actualizar firmware",
            font=FONT_SMALL,
            command=lambda: self._on_firmware_update(self._selected_board_id) if self._selected_board_id else None
        )
        self._btn_firmware.pack(side="left", padx=4)
        row += 1

        # Periféricos (detalle fijo)
        ctk.CTkLabel(right, text="Periféricos", font=FONT_NORMAL).grid(
            row=row, column=0, padx=12, pady=(12, 4), sticky="w")
        row += 1

        self._periph_text = ctk.CTkTextbox(
            right, height=120,
            font=FONT_SMALL,
            state="disabled", wrap="word"
        )
        self._periph_text.grid(row=row, column=0, columnspan=2, padx=12, pady=(0, 12), sticky="nsew")
        right.grid_rowconfigure(row, weight=1)

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------
    def set_boards(self, boards: list):
        """Actualizar la lista completa de placas."""
        self._boards = boards
        self._refresh_list()

    def update_board(self, board):
        """Actualizar o añadir una placa sin rehacer toda la lista."""
        # Buscar si ya existe
        for i, b in enumerate(self._boards):
            if b.id == board.id:
                self._boards[i] = board
                break
        else:
            self._boards.append(board)
        self._refresh_list()

    def show_board_detail(self, board_id: str):
        """Muestra el detalle de la placa con ese ID."""
        self._selected_board_id = board_id
        board = next((b for b in self._boards if b.id == board_id), None)
        if not board:
            self._lbl_title.configure(text="Placa no encontrada")
            return
        self._lbl_title.configure(text=f"Placa {board.id}")
        self._info_labels["id"].configure(text=board.id)
        self._info_labels["conn"].configure(text=CONN_ICONS.get(board.conn, board.conn))
        self._info_labels["status"].configure(text=board.status)
        self._info_labels["parcela"].configure(text=board.parcela or "Sin asignar")
        self._info_labels["firmware"].configure(text=board.firmware_version or "Desconocido")

        # Periféricos (simulación, luego vendrán de la placa)
        periph = (
            f"Sensores: DHT22 (temp/hum, pin D2), Capacitivo suelo (A0)\n"
            f"Actuadores: Relay bomba (pin D3)\n"
            f"Comunicación: {board.conn_module or 'No definido'}"
        )
        self._periph_text.configure(state="normal")
        self._periph_text.delete("1.0", "end")
        self._periph_text.insert("end", periph)
        self._periph_text.configure(state="disabled")

        # Habilitar botones
        self._btn_assign.configure(state="normal")
        self._btn_unassign.configure(state="normal")
        self._btn_firmware.configure(state="normal")

    # ------------------------------------------------------------------
    # Interno
    # ------------------------------------------------------------------
    def _refresh_list(self):
        for w in self._list_frame.winfo_children():
            w.destroy()

        for i, board in enumerate(self._boards):
            row = ctk.CTkFrame(self._list_frame, corner_radius=6,
                               border_width=1, border_color=COLORS["border"])
            row.grid(row=i, column=0, sticky="ew", pady=2, padx=2)
            row.grid_columnconfigure(0, weight=1)

            # Nombre / ID
            lbl_name = ctk.CTkLabel(row, text=board.id, font=FONT_NORMAL, anchor="w")
            lbl_name.grid(row=0, column=0, padx=10, pady=(6, 0), sticky="w")

            # Info secundaria
            info = f"{CONN_ICONS.get(board.conn, board.conn)} • {board.status} • {board.parcela or 'Sin asignar'}"
            lbl_info = ctk.CTkLabel(row, text=info, font=FONT_SMALL, text_color="gray")
            lbl_info.grid(row=1, column=0, padx=10, pady=(0, 6), sticky="w")

            # Botón asignar/desasignar (mini)
            btn_frame = ctk.CTkFrame(row, fg_color="transparent")
            btn_frame.grid(row=0, column=1, rowspan=2, padx=4, sticky="e")

            if board.parcela:
                ctk.CTkButton(
                    btn_frame, text="Desasignar",
                    width=80, height=24, font=("Roboto", 10),
                    fg_color="#EF4444", hover_color="#B91C1C",
                    command=lambda bid=board.id: self._on_unassign(bid)
                ).pack(side="left", padx=2)
            else:
                ctk.CTkButton(
                    btn_frame, text="Asignar",
                    width=70, height=24, font=("Roboto", 10),
                    command=lambda bid=board.id: self._on_assign(bid)
                ).pack(side="left", padx=2)

            # Clic en la fila → seleccionar
            for w in (row, lbl_name, lbl_info):
                w.bind("<Button-1>", lambda e, bid=board.id: self.show_board_detail(bid))
