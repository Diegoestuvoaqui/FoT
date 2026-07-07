# ui/panels/dht11_panel_v2.py
# Ejemplo de cómo quedaría tu panel usando los widgets nuevos
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Optional

import customtkinter as ctk

from ui.theme import FONT_TITLE, FONT_NORMAL, FONT_SMALL, COLORS
from ui.widgets.event_log import EventLog
from ui.widgets.canvas_chart import CanvasLineChart
from ui.widgets.gauge_widget import GaugeWidget
from ui.utils.time_utils import ms_timestamp_to_local, format_elapsed


class DHT11Panel(ctk.CTkFrame):
    """
    Panel DHT11 mejorado:
    - Gauges circulares para valores actuales.
    - Gráfico Canvas nativo (rápido, sin matplotlib).
    - Unidades correctas: °C y % HR.
    - Tiempo formateado correctamente desde ms.
    """

    def __init__(
        self,
        master,
        on_select_board: Optional[Callable[[str | None], None]] = None,
        **kwargs,
    ):
        super().__init__(master, **kwargs)

        self.grid_columnconfigure(0, weight=1, minsize=240)
        self.grid_columnconfigure(1, weight=3)
        self.grid_rowconfigure(0, weight=2)
        self.grid_rowconfigure(1, weight=1, minsize=120)

        self._on_select_board = on_select_board
        self._boards: list = []
        self._selected_board_id: str | None = None
        self._readings_cache: list[dict] = []

        self._build_left()
        self._build_right()
        self._build_bottom()

    # --- Construcción ---

    def _build_left(self):
        left = ctk.CTkFrame(self, corner_radius=12, border_width=1, border_color=COLORS["border"])
        left.grid(row=0, column=0, sticky="nsew", padx=(8, 4), pady=8)
        left.grid_rowconfigure(1, weight=1)
        left.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(left, text="🌡️ Arduinos DHT11", font=FONT_TITLE).grid(
            row=0, column=0, pady=(10, 4), padx=10, sticky="w")

        self._list_frame = ctk.CTkScrollableFrame(left, label_text="", corner_radius=8)
        self._list_frame.grid(row=1, column=0, sticky="nsew", padx=6, pady=4)
        self._list_frame.grid_columnconfigure(0, weight=1)

    def _build_right(self):
        right = ctk.CTkFrame(self, corner_radius=12, border_width=1, border_color=COLORS["border"])
        right.grid(row=0, column=1, sticky="nsew", padx=(4, 8), pady=8)
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(3, weight=1)

        # Título
        self._lbl_title = ctk.CTkLabel(
            right, text="— Selecciona un Arduino —", font=FONT_TITLE,
        )
        self._lbl_title.grid(row=0, column=0, columnspan=2, padx=12, pady=(12, 4), sticky="w")

        # Estado con badge de color
        status_frame = ctk.CTkFrame(right, fg_color="transparent")
        status_frame.grid(row=1, column=0, columnspan=2, padx=12, pady=4, sticky="w")
        ctk.CTkLabel(status_frame, text="Estado:", font=FONT_NORMAL).pack(side="left", padx=(0, 8))
        self._lbl_status = ctk.CTkLabel(
            status_frame, text="Sin conexión", width=130,
            font=("Roboto", 12, "bold"), corner_radius=6,
            fg_color="#6B7280", text_color="white",
        )
        self._lbl_status.pack(side="left")

        # Gauges para temperatura y humedad (más bonitos que texto plano)
        gauges_frame = ctk.CTkFrame(right, fg_color="transparent")
        gauges_frame.grid(row=2, column=0, columnspan=2, padx=12, pady=8, sticky="ew")
        gauges_frame.grid_columnconfigure((0, 1), weight=1)

        self._gauge_temp = GaugeWidget(
            gauges_frame, title="Temperatura", unit="°C",
            min_val=-10, max_val=50,
            color_low="#3B82F6", color_mid="#F59E0B", color_high="#EF4444",
            size=140,
        )
        self._gauge_temp.grid(row=0, column=0, padx=8, pady=4)

        self._gauge_hum = GaugeWidget(
            gauges_frame, title="Humedad Relativa", unit="%",
            min_val=0, max_val=100,
            color_low="#EF4444", color_mid="#F59E0B", color_high="#3B82F6",
            size=140,
        )
        self._gauge_hum.grid(row=0, column=1, padx=8, pady=4)

        # Timestamp de última lectura
        self._lbl_last = ctk.CTkLabel(
            right, text="Sin datos", font=FONT_SMALL, text_color="gray",
        )
        self._lbl_last.grid(row=3, column=0, columnspan=2, padx=12, pady=(2, 4), sticky="w")

        # Separador
        ctk.CTkFrame(right, height=2, fg_color="#3F3F3F").grid(
            row=4, column=0, columnspan=2, sticky="ew", padx=12, pady=6)

        # Gráfico Canvas nativo (reemplaza a matplotlib)
        ctk.CTkLabel(right, text="📈 Historial de lecturas", font=FONT_TITLE).grid(
            row=5, column=0, columnspan=2, padx=12, pady=(0, 8), sticky="w")

        self._sensor_chart = CanvasLineChart(right, max_points=300)
        self._sensor_chart.grid(row=6, column=0, columnspan=2, sticky="nsew", padx=12, pady=(0, 8))

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
        ts_ms = data.get("ts", 0)

        # Temperatura
        temp = None
        temp_data = readings.get("temp", {})
        if isinstance(temp_data, dict) and "value" in temp_data:
            val = temp_data["value"]
            if val is not None and isinstance(val, (int, float)):
                temp = float(val)
        self._gauge_temp.set_value(temp)

        # Humedad
        hum = None
        hum_data = readings.get("hum", {})
        if isinstance(hum_data, dict) and "value" in hum_data:
            val = hum_data["value"]
            if val is not None and isinstance(val, (int, float)):
                hum = float(val)
        self._gauge_hum.set_value(hum)

        # Tiempo: asumimos que ts es un timestamp epoch en ms
        # Si tu Arduino envía tiempo transcurrido, usa format_elapsed(ts_ms)
        time_str = ms_timestamp_to_local(ts_ms) if ts_ms > 1_000_000_000 else format_elapsed(ts_ms)
        self._lbl_last.configure(
            text=f"Última lectura: {time_str}",
            text_color=COLORS["accent"],
        )

        # Agregar al gráfico si hay datos válidos
        if temp is not None or hum is not None:
            now = datetime.now()
            self._sensor_chart.add_reading(now, {"temp": temp, "hum": hum})

            # Cache para historial
            self._readings_cache.append({
                "ts_base": now.isoformat(),
                "temp": temp,
                "hum": hum,
            })
            if len(self._readings_cache) > 500:
                self._readings_cache = self._readings_cache[-500:]

    def show_history(self, board_id: str, readings: list[dict]):
        """Carga historial desde DB al seleccionar una placa."""
        self._readings_cache = readings
        self._refresh_chart_from_cache()

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
        # Reset visual
        self._gauge_temp.set_value(None)
        self._gauge_hum.set_value(None)
        self._sensor_chart.clear()
        self._lbl_title.configure(text=f"Arduino: {board_id}")
        if self._on_select_board:
            self._on_select_board(board_id)

    def _refresh_chart_from_cache(self):
        timestamps = []
        temps = []
        hums = []
        for r in self._readings_cache:
            ts_str = r.get("ts_base", "")
            try:
                dt = datetime.fromisoformat(ts_str)
            except (ValueError, TypeError):
                continue
            timestamps.append(dt)
            temps.append(r.get("temp"))
            hums.append(r.get("hum"))

        self._sensor_chart.update_data(
            timestamps=timestamps,
            temp=temps,
            hum=hums,
        )
