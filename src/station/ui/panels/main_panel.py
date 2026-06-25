"""
ui/panels/main_panel.py
Panel principal dividido en dos columnas:
- Izquierda: ParcelaList
- Derecha: detalle de parcela + SensorChart
- Abajo: EventLog
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Optional

import customtkinter as ctk

from ui.theme import FSM_COLORS, FONT_TITLE, FONT_NORMAL, FONT_SMALL
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
            on_irrigate: Optional[Callable[[], None]] = None,
            on_stop: Optional[Callable[[], None]] = None,
            **kwargs,
    ):
        super().__init__(master, **kwargs)

        # Configurar grid
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
            "irrigate": on_irrigate,
            "stop": on_stop,
        }

        self._selected_parcela_id: str | None = None
        self._build_left()
        self._build_right()
        self._build_bottom()

        # Vinculamos el clic en la lista para que llame a select_parcela
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

        # Puedes agregar botón eliminar si quieres
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
        # Título de parcela
        self.lbl_title = ctk.CTkLabel(
            right_frame, text="— Ninguna parcela seleccionada —",
            font=FONT_TITLE,
        )
        self.lbl_title.grid(row=row, column=0, columnspan=2,
                            padx=12, pady=(12, 4), sticky="w")
        row += 1

        # Estado FSM
        ctk.CTkLabel(right_frame, text="Estado:", font=FONT_NORMAL).grid(
            row=row, column=0, padx=12, pady=4, sticky="w")
        self.lbl_fsm = ctk.CTkLabel(
            right_frame, text="—", width=130,
            font=("Roboto", 12, "bold"),
            corner_radius=6,
            fg_color="#6B7280",
            text_color="white",
        )
        self.lbl_fsm.grid(row=row, column=1, padx=12, pady=4, sticky="w")
        row += 1

        # Lecturas de sensores (tarjetas pequeñas)
        self.sensor_labels = {}
        # DESPUÉS
        self.sensor_labels["hum_suelo"] = None  # sin sensor de suelo en hardware actual

        for label, key in [("Humedad aire (%)", "hum_aire"),
                           ("Temperatura (°C)", "temp")]:
            frame_sensor = ctk.CTkFrame(right_frame, corner_radius=8, border_width=1, border_color="#3F3F3F")
            frame_sensor.grid(row=row, column=0, columnspan=2, padx=12, pady=4, sticky="ew")
            ctk.CTkLabel(frame_sensor, text=label, font=FONT_SMALL).pack(side="left", padx=8)
            lbl_val = ctk.CTkLabel(frame_sensor, text="—", font=FONT_NORMAL)
            lbl_val.pack(side="left", padx=8)
            # Podrías añadir barra de progreso para humedad suelo
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

        # Controles: modo, umbrales, botones
        # Selector de modo
        self.option_modo = ctk.CTkSegmentedButton(
            right_frame,
            values=["Reposo"],  # "Automático" requiere sensor de suelo
            font=FONT_NORMAL,
            command=self._on_mode_changed,
        )

        self.option_modo.set("Reposo")
        self.option_modo.grid(row=row, column=1, padx=12, pady=4, sticky="w")
        row += 1

        # Umbrales
        ctk.CTkLabel(right_frame, text="Umbral mín (%):", font=FONT_NORMAL).grid(
            row=row, column=0, padx=12, pady=4, sticky="w")
        self.entry_min = ctk.CTkEntry(right_frame, width=80, font=FONT_NORMAL)
        self.entry_min.grid(row=row, column=1, padx=12, pady=4, sticky="w")
        row += 1

        # DESPUÉS
        self.entry_min = ctk.CTkEntry(right_frame, width=80, font=FONT_NORMAL, state="disabled")
        self.entry_min.grid(row=row, column=1, padx=12, pady=4, sticky="w")
        row += 1

        ctk.CTkLabel(right_frame, text="Umbral máx (%):", font=FONT_NORMAL).grid(
            row=row, column=0, padx=12, pady=4, sticky="w")
        self.entry_max = ctk.CTkEntry(right_frame, width=80, font=FONT_NORMAL, state="disabled")
        self.entry_max.grid(row=row, column=1, padx=12, pady=4, sticky="w")
        row += 1

        ctk.CTkButton(
            right_frame, text="Aplicar umbrales",
            font=FONT_NORMAL,
            state="disabled",  # sin sensor de suelo no aplica
            command=self._on_apply_thresholds,
        ).grid(row=row, column=0, columnspan=2, pady=6)
        row += 1

        ctk.CTkLabel(  # nota explicativa
            right_frame,
            text="⚠ Umbrales y modo automático requieren sensor de suelo",
            font=FONT_SMALL, text_color="#9CA3AF",
        ).grid(row=row, column=0, columnspan=2, padx=12, pady=(0, 4), sticky="w")
        row += 1

        # Botones de control manual
        ctrl_frame = ctk.CTkFrame(right_frame, fg_color="transparent")
        ctrl_frame.grid(row=row, column=0, columnspan=2, pady=6)
        self.btn_irrigate = ctk.CTkButton(
            ctrl_frame, text="▶ Activar riego",
            font=FONT_NORMAL,
            fg_color="#3B82F6", hover_color="#1D4ED8",
            state="disabled",
            command=self._on_irrigate,
        )
        self.btn_irrigate.pack(side="left", padx=8)
        self.btn_stop = ctk.CTkButton(
            ctrl_frame, text="■ Detener riego",
            font=FONT_NORMAL,
            fg_color="#EF4444", hover_color="#B91C1C",
            state="disabled",
            command=self._on_stop,
        )
        self.btn_stop.pack(side="left", padx=8)
        row += 1

        # Gráfico
        self.chart = SensorChart(right_frame)
        self.chart.grid(row=row, column=0, columnspan=2, sticky="nsew", padx=12, pady=(6, 4))
        right_frame.grid_rowconfigure(row, weight=1)  # para que el gráfico se expanda

        # Indicador de umbrales y alertas (debajo del gráfico, pero dentro del mismo grid)
        row += 1
        self.lbl_umbral_info = ctk.CTkLabel(
            right_frame, text="Umbral activo: —",
            font=FONT_SMALL, text_color="gray"
        )
        self.lbl_umbral_info.grid(row=row, column=0, columnspan=2, padx=12, pady=(0, 2), sticky="w")

        self.lbl_alerts = ctk.CTkLabel(
            right_frame, text="Alertas activas: —",
            font=FONT_SMALL, text_color="#EF4444"
        )
        self.lbl_alerts.grid(row=row + 1, column=0, columnspan=2, padx=12, sticky="w")

    def _build_bottom(self):
        self.event_log = EventLog(self)
        self.event_log.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=8, pady=(0, 8))

    # ------------------------------------------------------------------
    # Callbacks que conectan con MainWindow
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
        if self._callbacks["apply_thresholds"]:
            min_v = self.entry_min.get()
            max_v = self.entry_max.get()
            self._callbacks["apply_thresholds"](min_v, max_v)

    def _on_irrigate(self):
        if self._callbacks["irrigate"]:
            self._callbacks["irrigate"]()

    def _on_stop(self):
        if self._callbacks["stop"]:
            self._callbacks["stop"]()

    def _on_context_menu(self, parcela_id: str, action: str = "") -> None:
        if action == "delete":
            if self._callbacks.get("delete_parcela"):
                self._callbacks["delete_parcela"](parcela_id)
        elif action == "detail":
            # por ahora selecciona la parcela; el panel de detalle
            # completo se abrirá en el siguiente paso del plan
            self._on_parcela_selected(parcela_id)

    def _on_delete_parcela(self) -> None:
        # El botón "Eliminar" de la barra usa la parcela seleccionada
        if self._selected_parcela_id:
            if self._callbacks.get("delete_parcela"):
                self._callbacks["delete_parcela"](self._selected_parcela_id)

    # ------------------------------------------------------------------
    # Métodos para actualizar la UI desde el exterior
    def set_parcelas(self, parcelas):
        self.parcela_list.set_parcelas(parcelas)

    @staticmethod
    def _set_entry(entry: ctk.CTkEntry, value: str) -> None:
        """Actualiza el valor de un CTkEntry aunque esté deshabilitado."""
        entry.configure(state="normal")
        entry.delete(0, "end")
        entry.insert(0, value)
        entry.configure(state="disabled")

    def update_detail(self, parcela):
        """Mostrar los datos de una parcela en el panel derecho."""
        self.lbl_title.configure(text=parcela.get_name())
        fsm = getattr(parcela, "fsm_state", "Idle")
        self.lbl_fsm.configure(text=fsm, fg_color=FSM_COLORS.get(fsm, "#6B7280"))

        # Lecturas
        # DESPUÉS
        reading = parcela.get_latest_reading()
        # hum_suelo es None (sin sensor de suelo en hardware actual)
        if self.sensor_labels.get("hum_suelo"):
            self.sensor_labels["hum_suelo"].configure(text=_fmt(reading.get("hum_suelo")))
        self.sensor_labels["hum_aire"].configure(text=_fmt(reading.get("hum_aire")))
        self.sensor_labels["temp"].configure(text=_fmt(reading.get("temp")))
        last_ts = reading.get("timestamp", None)
        if last_ts:
            self.lbl_last_reading.configure(text=f"Hace {last_ts}")  # simplificado
        else:
            self.lbl_last_reading.configure(text="Sin datos")

        # Umbrales
        # DESPUÉS
        self._set_entry(self.entry_min, str(parcela.umbral_min))
        self._set_entry(self.entry_max, str(parcela.umbral_max))
        self.lbl_umbral_info.configure(
            text=f"Umbral activo: {parcela.umbral_min}% – {parcela.umbral_max}%"
        )

        # Modo
        modo = parcela.modo
        self.option_modo.set("Automático" if modo == "auto" else "Reposo")

        # Botones de riego (solo habilitados si el estado es Idle)
        state = "normal" if fsm == "Idle" else "disabled"
        self.btn_irrigate.configure(state=state)
        self.btn_stop.configure(state=state)

        # Chart: datos históricos (simulado por ahora)
        # Aquí deberías obtener las series temporales desde DB o parcela.
        # Por ahora, datos vacíos:
        self.chart.update_data([], [], [], [], parcela.umbral_min, parcela.umbral_max)

    def update_connection_status(self, parcela_id, connected: bool):
        """Actualiza el indicador de conexión de una fila."""
        # Podrías añadir lógica en parcela_list
        pass

    def add_event(self, text: str, tipo: str = ""):
        self.event_log.add_line(text, tipo)


def _fmt(value):
    if value is None:
        return "—"
    try:
        return f"{float(value):.1f}"
    except (TypeError, ValueError):
        return "—"
