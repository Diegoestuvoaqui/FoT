# ui/panels/arduino_panel.py
from __future__ import annotations

import customtkinter as ctk

from domain.boards import Board
from ui.theme import FONT_TITLE, FONT_NORMAL, FONT_SMALL, COLORS
from ui.widgets.board_list import BoardList


class ArduinoPanel(ctk.CTkFrame):
    def __init__(
            self,
            master,
            on_register=None,
            on_connect=None,
            on_disconnect=None,
            on_remove=None,
            on_read_now=None,
            on_scan_bluetooth=None,
            on_scan_wifi=None,
            on_firmware_update=None,
            **kwargs
    ):
        super().__init__(master, **kwargs)

        self.grid_columnconfigure(0, weight=1, minsize=280)
        self.grid_columnconfigure(1, weight=3)
        self.grid_rowconfigure(0, weight=1)

        self._on_register = on_register
        self._on_connect = on_connect
        self._on_disconnect = on_disconnect
        self._on_remove = on_remove
        self._on_read_now = on_read_now
        self._on_scan_bluetooth = on_scan_bluetooth
        self._on_scan_wifi = on_scan_wifi
        self._on_firmware_update = on_firmware_update

        self._boards: list[Board] = []
        self._selected_board_id: str | None = None

        self._build_left()
        self._build_right()

    def _build_left(self):
        left = ctk.CTkFrame(self)
        left.grid(row=0, column=0, sticky="nsew", padx=(8, 4), pady=8)
        left.grid_rowconfigure(1, weight=1)
        left.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(left, text="Placas Detectadas", font=FONT_TITLE).grid(
            row=0, column=0, pady=(10, 4), padx=10, sticky="w")

        # ← USAR BoardList en vez de construir lista manual
        self._board_list = BoardList(
            left,
            on_select=self._on_board_selected,
        )
        self._board_list.grid(row=1, column=0, sticky="nsew", padx=6, pady=4)

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
            command=self._on_scan_wifi
        ).pack(side="left", padx=4, fill="x", expand=True)

    def _build_right(self):
        right = ctk.CTkFrame(self)
        right.grid(row=0, column=1, sticky="nsew", padx=(4, 8), pady=8)
        right.grid_columnconfigure(1, weight=1)

        self._lbl_title = ctk.CTkLabel(
            right, text="Selecciona una placa",
            font=FONT_TITLE, anchor="w"
        )
        self._lbl_title.grid(row=0, column=0, columnspan=2,
                             padx=12, pady=(12, 8), sticky="ew")

        # === INFORMACIÓN DE IDENTIDAD ===
        row = 1
        self._info_labels = {}

        identity_fields = [
            ("ID:", "id"),
            ("Conexión:", "conn"),
            ("Estado:", "status"),
            ("Sketch:", "sketch"),
            ("Versión:", "version"),
        ]
        for label, key in identity_fields:
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

        # === DATOS DE FÁBRICA (Hardware) ===
        ctk.CTkLabel(right, text="Datos de fábrica", font=FONT_TITLE).grid(
            row=row, column=0, columnspan=2, padx=12, pady=(0, 8), sticky="w")
        row += 1

        self._factory_labels = {}
        factory_fields = [
            ("Fabricante:", "manufacturer"),
            ("Producto:", "product"),
            ("Nº Serie:", "serial_number"),
            ("VID/PID:", "vid_pid"),
            ("HW ID:", "hwid"),
            ("Ubicación USB:", "location"),
        ]
        for label, key in factory_fields:
            ctk.CTkLabel(right, text=label, font=FONT_SMALL, text_color="gray").grid(
                row=row, column=0, padx=12, pady=1, sticky="w")
            lbl = ctk.CTkLabel(right, text="—", font=FONT_SMALL)
            lbl.grid(row=row, column=1, padx=12, pady=1, sticky="w")
            self._factory_labels[key] = lbl
            row += 1

        # Separador
        ctk.CTkFrame(right, height=2, fg_color=COLORS["border"]).grid(
            row=row, column=0, columnspan=2, sticky="ew", padx=12, pady=8)
        row += 1

        # === PUERTO Y CONEXIÓN ===
        ctk.CTkLabel(right, text="Puerto", font=FONT_TITLE).grid(
            row=row, column=0, columnspan=2, padx=12, pady=(0, 8), sticky="w")
        row += 1

        self._port_label = ctk.CTkLabel(right, text="—", font=FONT_NORMAL)
        self._port_label.grid(row=row, column=0, columnspan=2,
                              padx=12, pady=2, sticky="w")
        row += 1

        # Última vez visto
        self._lbl_last_seen = ctk.CTkLabel(
            right, text="Sin datos", font=FONT_SMALL, text_color="gray")
        self._lbl_last_seen.grid(row=row, column=0, columnspan=2,
                                 padx=12, pady=8, sticky="w")
        row += 1

        # Separador
        ctk.CTkFrame(right, height=2, fg_color=COLORS["border"]).grid(
            row=row, column=0, columnspan=2, sticky="ew", padx=12, pady=8)
        row += 1

        # === BOTONES DE ACCIÓN ===
        btn_frame = ctk.CTkFrame(right, fg_color="transparent")
        btn_frame.grid(row=row, column=0, columnspan=2, pady=8)

        self._btn_register = ctk.CTkButton(
            btn_frame, text="Registrar Arduino",
            font=FONT_SMALL,
            command=self._on_register_clicked
        )
        self._btn_register.pack(side="left", padx=4)

        self._btn_connect = ctk.CTkButton(
            btn_frame, text="Conectar",
            font=FONT_SMALL,
            command=self._on_connect_clicked
        )
        self._btn_connect.pack(side="left", padx=4)

        self._btn_disconnect = ctk.CTkButton(
            btn_frame, text="Desconectar",
            font=FONT_SMALL,
            fg_color="#EF4444", hover_color="#B91C1C",
            command=self._on_disconnect_clicked
        )
        self._btn_disconnect.pack(side="left", padx=4)

        self._btn_read = ctk.CTkButton(
            btn_frame, text="🔄 Identificar",
            font=FONT_SMALL,
            state="disabled",
            command=self._on_read_clicked
        )
        self._btn_read.pack(side="left", padx=4)

        self._btn_firmware = ctk.CTkButton(
            btn_frame, text="Cargar .hex",
            font=FONT_SMALL,
            command=self._on_firmware_clicked
        )
        self._btn_firmware.pack(side="left", padx=4)

        self._btn_remove = ctk.CTkButton(
            btn_frame, text="Eliminar",
            font=FONT_SMALL,
            fg_color="#6B7280", hover_color="#4B5563",
            command=self._on_remove_clicked
        )
        self._btn_remove.pack(side="left", padx=4)

        row += 1

        # === LOG (solo eventos de conexión, no lecturas) ===
        ctk.CTkLabel(right, text="Log de conexión", font=FONT_SMALL, text_color="gray").grid(
            row=row, column=0, padx=12, pady=(8, 0), sticky="w")
        row += 1

        self._log = ctk.CTkTextbox(
            right, height=100,
            font=FONT_SMALL,
            state="disabled", wrap="word"
        )
        self._log.grid(row=row, column=0, columnspan=2,
                       padx=12, pady=(0, 12), sticky="nsew")
        right.grid_rowconfigure(row, weight=1)

    # --- API pública ---

    def set_boards(self, boards: list):
        self._boards = boards
        self._board_list.set_boards(boards)

    def update_board(self, board: Board):
        self._board_list.update_board(board)

        # Actualizar detalle si es la seleccionada
        if self._selected_board_id == board.id:
            self._update_detail(board)

    def update_reading(self, board_id: str, data: dict):
        # Las lecturas se muestran en DHT11Panel, aquí solo log de conexión
        pass

    # --- Callbacks internos ---

    def _on_board_selected(self, board_id: str):
        self._selected_board_id = board_id
        board = next((b for b in self._boards if b.id == board_id), None)
        if board:
            self._update_detail(board)

    def _update_detail(self, board: Board):
        self._lbl_title.configure(text=f"Placa {board.id}")

        # Identidad
        self._info_labels["id"].configure(text=board.id)
        self._info_labels["conn"].configure(
            text=f"{self._conn_icon(board.conn)} {board.conn.upper()}"
        )
        self._info_labels["status"].configure(text=board.status)
        sketch = f"{board.sketch_name or 'Desconocido'} ({board.sketch_id or '?'})"
        self._info_labels["sketch"].configure(text=sketch)
        self._info_labels["version"].configure(text=board.sketch_version or "—")

        # Datos de fábrica
        self._factory_labels["manufacturer"].configure(
            text=board.manufacturer or "No disponible")
        self._factory_labels["product"].configure(
            text=board.product or "No disponible")
        self._factory_labels["serial_number"].configure(
            text=board.serial_number or "No disponible")

        vid_pid = "No disponible"
        if board.vid is not None and board.pid is not None:
            vid_pid = f"{board.vid:04X}:{board.pid:04X} ({board.get_vendor_name()})"
        self._factory_labels["vid_pid"].configure(text=vid_pid)

        self._factory_labels["hwid"].configure(
            text=board.hwid or "No disponible")
        self._factory_labels["location"].configure(
            text=board.location or "No disponible")

        # Puerto
        self._port_label.configure(text=board.port or "No asignado")

        # Última vez visto
        if board.last_seen:
            self._lbl_last_seen.configure(
                text=f"Última vez vista: {board.last_seen}",
                text_color="gray")
        else:
            self._lbl_last_seen.configure(text="Sin registro de actividad", text_color="gray")

        # Estados de botones
        is_connected = board.status == "Conectada"
        is_registered = board.sketch_id is not None

        self._btn_register.configure(
            state="disabled" if is_registered else "normal"
        )
        self._btn_connect.configure(
            state="normal" if not is_connected else "disabled"
        )
        self._btn_disconnect.configure(
            state="normal" if is_connected else "disabled"
        )
        self._btn_read.configure(
            state="normal" if is_connected else "disabled"
        )

    def _on_register_clicked(self):
        if self._selected_board_id and self._on_register:
            self._on_register(self._selected_board_id)

    def _on_connect_clicked(self):
        if self._selected_board_id and self._on_connect:
            self._on_connect(self._selected_board_id)

    def _on_disconnect_clicked(self):
        if self._selected_board_id and self._on_disconnect:
            self._on_disconnect(self._selected_board_id)

    def _on_read_clicked(self):
        if self._selected_board_id and self._on_read_now:
            self._on_read_now(self._selected_board_id)

    def _on_firmware_clicked(self):
        if self._selected_board_id and self._on_firmware_update:
            self._on_firmware_update(self._selected_board_id)

    def _on_remove_clicked(self):
        if self._selected_board_id and self._on_remove:
            self._on_remove(self._selected_board_id)

    def _log_add(self, text: str):
        self._log.configure(state="normal")
        self._log.insert("end", text + "\n")
        self._log.see("end")
        self._log.configure(state="disabled")

    @staticmethod
    def _conn_icon(conn: str) -> str:
        icons = {
            "usb": "🔌",
            "bluetooth": "📡",
            "wifi": "📶",
        }
        return icons.get(conn, "❓")