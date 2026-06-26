"""
ui/panels/main_panel.py
Panel principal simplificado: lista de parcelas + lecturas del sensor.
Sin controles de riego ni umbrales complejos.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Optional

import customtkinter as ctk

from ui.theme import FONT_TITLE, FONT_NORMAL, FONT_SMALL
from ui.widgets.event_log import EventLog
from ui.widgets.parcela_list import ParcelaList
from ui.widgets.sensor_chart import SensorChart


class MainPanel(ctk.CTkFrame):
    def __init__(
            self,
            master,
            on_add_parcela: Optional[Callable[[], None]] = None,
            on_delete_parcela: Optional[Callable[[str], None]] = None,
            on_select_parcela: Optional[Callable[[str], None]] = None,
            on_apply_thresholds: Optional[Callable[[str, str], None]] = None,
            on_mode_change: Optional[Callable[[str], None]] = None,
            **kwargs,
    ):
        super().__init__(master, **kwargs)

        self.grid_columnconfigure(0, weight=1, minsize=240)
        self.grid_columnconfigure(1, weight=3)
        self.grid_rowconfigure(0, weight=3)
        self.grid_rowconfigure(1, weight=1, minsize=150)

        self._callbacks = {
            "add_parcela": on_add_parcela,
            "select_parcela": on_select_parcela,
            "apply_thresholds": on_apply_thresholds,
            "delete_parcela": on_delete_parcela,
            "mode_change": on_mode_change,
        }

        self._selected_parcela_id: str | None = None
        self._build_left()
        self._build_right()
        self._build_bottom()

        self.parcela_list._on_select = self._on_parcela_selected

    # ------------------------------------------------------------------
    def _build_left(self):
        left_frame = ctk.CTkFrame(self)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(8, 4), pady=8)
        left_frame.grid_rowconfigure(1, weight=1)
        left_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(left_frame, text="Parcelas", font=FONT_TITLE).grid(
            row=0, column=0, pady=(10, 4), padx=10, sticky="w")

        self.parcela_list = ParcelaList(
            left_frame,
            on_context_menu=self._on_context_menu,
        )
        self.parcela_list.grid(row=1, column=0, sticky="nsew", padx=6, pady=4)

        btn_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        btn_frame.grid(row=2, column=0, pady=6, padx=6, sticky="ew")
        btn_frame.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkButton(
            btn_frame, text="+ Añadir parcela",
            font=FONT_SMALL,
            command=self._on_add_parcela,
        ).grid(row=0, column=0, padx=2, sticky="ew")

        ctk.CTkButton(
            btn_frame, text="Eliminar",
            font=FONT_SMALL,
            fg_color="#EF4444", hover_color="#B91C1C",
            command=self._on_delete_parcela,
        ).grid(row=0, column=1, padx=2, sticky="ew")

    def _build_right(self):
        right_frame = ctk.CTkFrame(self)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(4, 8), pady=8)
        right_frame.grid_columnconfigure(1, weight=1)

        row = 0
        # Título
        self.lbl_title = ctk.CTkLabel(
            right_frame, text="— Ninguna parcela seleccionada —",
            font=FONT_TITLE,
        )
        self.lbl_title.grid(row=row, column=0, columnspan=2,
                            padx=12, pady=(12, 4), sticky="w")
        row += 1

        # Estado de conexión (simplificado)
        ctk.CTkLabel(right_frame, text="Estado:", font=FONT_NORMAL).grid(
            row=row, column=0, padx=12, pady=4, sticky="w")
        self.lbl_status = ctk.CTkLabel(
            right_frame, text="Sin conexión", width=130,
            font=("Roboto", 12, "bold"),
            corner_radius=6,
            fg_color="#6B7280",
            text_color="white",
        )
        self.lbl_status.grid(row=row, column=1, padx=12, pady=4, sticky="w")
        row += 1

        # Lecturas de sensores (tarjetas)
        self.sensor_labels = {}

        for label, key, unit in [
            ("Temperatura", "temp", "°C"),
            ("Humedad", "hum", "%")
        ]:
            frame_sensor = ctk.CTkFrame(right_frame, corner_radius=8, border_width=1, border_color="#3F3F3F")
            frame_sensor.grid(row=row, column=0, columnspan=2, padx=12, pady=4, sticky="ew")
            ctk.CTkLabel(frame_sensor, text=f"{label} ({unit})", font=FONT_SMALL).pack(side="left", padx=8)
            lbl_val = ctk.CTkLabel(frame_sensor, text="—", font=FONT_NORMAL)
            lbl_val.pack(side="left", padx=8)
            self.sensor_labels[key] = lbl_val
            row += 1

        # Estado última lectura
        self.lbl_last_reading = ctk.CTkLabel(
            right_frame, text="Sin datos", font=FONT_SMALL, text_color="gray")
        self.lbl_last_reading.grid(row=row, column=0, columnspan=2, padx=12, pady=(2, 8), sticky="w")
        row += 1

        # Separador
        ctk.CTkFrame(right_frame, height=2, fg_color="#3F3F3F").grid(
            row=row, column=0, columnspan=2, sticky="ew", padx=12, pady=6)
        row += 1

        # Modo (solo visual, sin umbrales complejos)
        ctk.CTkLabel(right_frame, text="Modo:", font=FONT_NORMAL).grid(
            row=row, column=0, padx=12, pady=4, sticky="w")
        self.lbl_modo = ctk.CTkLabel(right_frame, text="manual", font=FONT_NORMAL)
        self.lbl_modo.grid(row=row, column=1, padx=12, pady=4, sticky="w")
        row += 1

        # Gráfico
        self.chart = SensorChart(right_frame)
        self.chart.grid(row=row, column=0, columnspan=2, sticky="nsew", padx=12, pady=(6, 4))
        right_frame.grid_rowconfigure(row, weight=1)

    def _build_bottom(self):
        self.event_log = EventLog(self)
        self.event_log.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=8, pady=(0, 8))

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------
    def _on_add_parcela(self):
        if self._callbacks["add_parcela"]:
            self._callbacks["add_parcela"]()

    def _on_parcela_selected(self, parcela_id):
        self._selected_parcela_id = parcela_id
        if self._callbacks["select_parcela"]:
            self._callbacks["select_parcela"](parcela_id)

    def _on_mode_changed(self, value):
        if self._callbacks["mode_change"]:
            self._callbacks["mode_change"](value.lower())

    def _on_apply_thresholds(self):
        # Simplificado: no hay umbrales en UI
        pass

    def _on_context_menu(self, parcela_id: str, action: str = "") -> None:
        if action == "delete":
            if self._callbacks.get("delete_parcela"):
                self._callbacks["delete_parcela"](parcela_id)
        elif action == "detail":
            self._on_parcela_selected(parcela_id)

    def _on_delete_parcela(self) -> None:
        if self._selected_parcela_id:
            if self._callbacks.get("delete_parcela"):
                self._callbacks["delete_parcela"](self._selected_parcela_id)

    # ------------------------------------------------------------------
    # Métodos para actualizar la UI desde el exterior
    # ------------------------------------------------------------------
    def set_parcelas(self, parcelas):
        self.parcela_list.set_parcelas(parcelas)

    def update_detail(self, parcela):
        self.lbl_title.configure(text=parcela.get_name())

        # Estado simplificado: conectado o no
        has_board = getattr(parcela, "board_id", None) is not None
        self.lbl_status.configure(
            text="Conectada" if has_board else "Sin placa",
            fg_color="#22C55E" if has_board else "#6B7280"
        )

        # Lecturas
        reading = parcela.get_latest_reading()
        self.sensor_labels["temp"].configure(text=_fmt(reading.get("temp")))
        self.sensor_labels["hum"].configure(text=_fmt(reading.get("hum")))

        last_ts = reading.get("ts", None)
        if last_ts:
            self.lbl_last_reading.configure(text=f"Última lectura: {last_ts}ms")
        else:
            self.lbl_last_reading.configure(text="Sin datos")

        # Modo
        self.lbl_modo.configure(text=parcela.modo or "manual")

        # Chart: datos históricos
        self.chart.update_data([], [], [], [], None, None)

    def add_event(self, text: str, tipo: str = ""):
        self.event_log.add_line(text, tipo)


def _fmt(value):
    if value is None:
        return "—"
    try:
        return f"{float(value):.1f}"
    except (TypeError, ValueError):
        return "—"
