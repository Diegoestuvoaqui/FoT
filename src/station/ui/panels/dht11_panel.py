# ui/panels/dht11_panel.py
from __future__ import annotations

from collections.abc import Callable
from typing import Optional

import customtkinter as ctk

from ui.theme import FONT_TITLE, FONT_NORMAL, FONT_SMALL, COLORS
from ui.widgets.event_log import EventLog


class DHT11Panel(ctk.CTkFrame):
    def __init__(
        self,
        master,
        on_select_board: Optional[Callable[[str | None], None]] = None,
        on_export: Optional[Callable[[str], None]] = None,
        **kwargs,
    ):
        super().__init__(master, **kwargs)

        self.grid_columnconfigure(0, weight=1, minsize=240)
        self.grid_columnconfigure(1, weight=3)
        self.grid_rowconfigure(0, weight=3)
        self.grid_rowconfigure(1, weight=1, minsize=150)

        self._on_select_board = on_select_board
        self._on_export = on_export
        self._boards: list = []
        self._selected_board_id: str | None = None

        self._build_left()
        self._build_right()
        self._build_bottom()

    def _build_left(self):
        left = ctk.CTkFrame(self)
        left.grid(row=0, column=0, sticky="nsew", padx=(8, 4), pady=8)
        left.grid_rowconfigure(1, weight=1)
        left.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(left, text="Arduinos DHT11", font=FONT_TITLE).grid(
            row=0, column=0, pady=(10, 4), padx=10, sticky="w")

        # Lista de boards
        self._list_frame = ctk.CTkScrollableFrame(left, label_text="")
        self._list_frame.grid(row=1, column=0, sticky="nsew", padx=6, pady=4)
        self._list_frame.grid_columnconfigure(0, weight=1)

        # Botón exportar
        btn_frame = ctk.CTkFrame(left, fg_color="transparent")
        btn_frame.grid(row=2, column=0, pady=6, padx=6, sticky="ew")

        ctk.CTkButton(
            btn_frame, text="Exportar datos",
            font=FONT_SMALL,
            command=self._on_export_clicked,
        ).pack(fill="x", padx=2)

    def _build_right(self):
        right = ctk.CTkFrame(self)
        right.grid(row=0, column=1, sticky="nsew", padx=(4, 8), pady=8)
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(6, weight=1)

        row = 0
        self._lbl_title = ctk.CTkLabel(
            right, text="— Selecciona un Arduino —",
            font=FONT_TITLE,
        )
        self._lbl_title.grid(row=row, column=0, columnspan=2,
                            padx=12, pady=(12, 4), sticky="w")
        row += 1

        # Estado
        ctk.CTkLabel(right, text="Estado:", font=FONT_NORMAL).grid(
            row=row, column=0, padx=12, pady=4, sticky="w")
        self._lbl_status = ctk.CTkLabel(
            right, text="Sin conexión", width=130,
            font=("Roboto", 12, "bold"),
            corner_radius=6,
            fg_color="#6B7280",
            text_color="white",
        )
        self._lbl_status.grid(row=row, column=1, padx=12, pady=4, sticky="w")
        row += 1

        # Tarjetas de lectura
        self._sensor_labels = {}
        for label, key, unit in [("Temperatura", "temp", "°C"), ("Humedad", "hum", "%")]:
            frame = ctk.CTkFrame(right, corner_radius=8, border_width=1, border_color="#3F3F3F")
            frame.grid(row=row, column=0, columnspan=2, padx=12, pady=4, sticky="ew")
            ctk.CTkLabel(frame, text=f"{label} ({unit})", font=FONT_SMALL).pack(side="left", padx=8)
            lbl = ctk.CTkLabel(frame, text="—", font=FONT_NORMAL)
            lbl.pack(side="left", padx=8)
            self._sensor_labels[key] = lbl
            row += 1

        # Última lectura
        self._lbl_last = ctk.CTkLabel(
            right, text="Sin datos", font=FONT_SMALL, text_color="gray")
        self._lbl_last.grid(row=row, column=0, columnspan=2, padx=12, pady=(2, 8), sticky="w")
        row += 1

        # Separador
        ctk.CTkFrame(right, height=2, fg_color="#3F3F3F").grid(
            row=row, column=0, columnspan=2, sticky="ew", padx=12, pady=6)
        row += 1

        # Tabla de historial
        ctk.CTkLabel(right, text="Historial de lecturas", font=FONT_TITLE).grid(
            row=row, column=0, columnspan=2, padx=12, pady=(0, 8), sticky="w")
        row += 1

        self._history_table = ctk.CTkTextbox(
            right, font=("Courier New", 11), state="disabled", wrap="none")
        self._history_table.grid(row=row, column=0, columnspan=2, sticky="nsew", padx=12, pady=(0, 8))

    def _build_bottom(self):
        self.event_log = EventLog(self)
        self.event_log.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=8, pady=(0, 8))

    # --- API pública ---

    def set_boards(self, boards: list):
        self._boards = boards
        self._refresh_list()

    def update_board(self, board):
        for i, b in enumerate(self._boards):
            if b.id == board.id:
                self._boards[i] = board
                break
        else:
            self._boards.append(board)
        self._refresh_list()

    def update_reading(self, board_id: str, data: dict):
        if self._selected_board_id != board_id:
            return

        readings = data.get("data", {})
        ts = data.get("ts", 0)

        for key, lbl in self._sensor_labels.items():
            sensor = readings.get(key, {})
            if isinstance(sensor, dict) and "value" in sensor:
                val = sensor["value"]
                lbl.configure(text=f"{val:.1f}")
            else:
                lbl.configure(text="—")

        self._lbl_last.configure(
            text=f"Última lectura: {ts}ms",
            text_color=COLORS["accent"]
        )

        # Refrescar historial
        self._refresh_history(board_id)

    def show_history(self, board_id: str, readings: list[dict]):
        self._refresh_history_table(readings)

    def add_event(self, text: str, tipo: str = ""):
        self.event_log.add_line(text, tipo)

    # --- Interno ---

    def _refresh_list(self):
        for w in self._list_frame.winfo_children():
            w.destroy()

        for i, board in enumerate(self._boards):
            self._add_board_row(i, board)

    def _add_board_row(self, index: int, board):
        row = ctk.CTkFrame(self._list_frame, corner_radius=6,
                           border_width=1, border_color=COLORS["border"])
        row.grid(row=index, column=0, sticky="ew", pady=2, padx=2)
        row.grid_columnconfigure(0, weight=1)

        name = board.sketch_name or board.id
        lbl = ctk.CTkLabel(row, text=f"🌡️ {name}", font=FONT_NORMAL, anchor="w")
        lbl.grid(row=0, column=0, padx=10, pady=6, sticky="w")

        status = "●" if board.status == "Conectada" else "○"
        color = COLORS["accent"] if board.status == "Conectada" else "gray"
        st = ctk.CTkLabel(row, text=status, font=("Roboto", 14), text_color=color)
        st.grid(row=0, column=1, padx=10)

        for w in (row, lbl):
            w.bind("<Button-1>", lambda e, bid=board.id: self._select_board(bid))

    def _select_board(self, board_id: str):
        self._selected_board_id = board_id
        for w in self._list_frame.winfo_children():
            # Actualizar selección visual
            pass
        if self._on_select_board:
            self._on_select_board(board_id)

    def _on_export_clicked(self):
        if self._selected_board_id and self._on_export:
            self._on_export(self._selected_board_id)

    def _refresh_history(self, board_id: str):
        # Llamar a DB para obtener últimas lecturas
        pass

    def _refresh_history_table(self, readings: list[dict]):
        self._history_table.configure(state="normal")
        self._history_table.delete("1.0", "end")

        header = f"{'Fecha':<20} {'Sensor':<12} {'Valor':<10} {'Unidad':<8}\\n"
        self._history_table.insert("end", header)
        self._history_table.insert("end", "—" * 55 + "\\n")

        for r in readings[:50]:
            ts = r.get("ts_base", "")[:19]
            sensor = r.get("sensor_type", "—")
            val = r.get("valor")
            val_str = f"{val:.1f}" if val is not None else "—"
            unit = r.get("unidad", "—")
            line = f"{ts:<20} {sensor:<12} {val_str:<10} {unit:<8}\\n"
            self._history_table.insert("end", line)

        self._history_table.configure(state="disabled")