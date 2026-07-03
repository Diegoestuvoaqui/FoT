# ui/widgets/sensor_chart.py
from __future__ import annotations

import tkinter as tk
from datetime import datetime, timedelta
from tkinter import filedialog

import customtkinter as ctk
import matplotlib

matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from ui.theme import FONT_SMALL


class SensorChart(ctk.CTkFrame):
    """
    Gráfico de lecturas de sensores.
    Adaptado para DHT11: temperatura y humedad (aire).
    Extensible para futuros sensores (humedad suelo, etc.).
    """

    # Series disponibles por tipo de sketch
    SERIES_CONFIG = {
        "dht11": [
            ("temp", "Temperatura (°C)", "#EF4444"),  # rojo
            ("hum", "Humedad (%)", "#3B82F6"),  # azul
        ],
        # Futuros sensores:
        # "suelo": [
        #     ("hum_suelo", "Hum. suelo (%)", "#22C55E"),  # verde
        #     ("temp", "Temperatura (°C)", "#EF4444"),
        # ],
    }

    def __init__(self, master, sketch_type: str = "dht11", **kwargs):
        super().__init__(master, fg_color="transparent", corner_radius=0)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._sketch_type = sketch_type
        self._series_config = self.SERIES_CONFIG.get(sketch_type, self.SERIES_CONFIG["dht11"])

        self._build_controls()
        self._build_chart()

        # Datos almacenados por serie
        self._data: dict[str, list] = {
            key: [] for key, _, _ in self._series_config
        }
        self._timestamps: list[datetime] = []

    def _build_controls(self):
        ctrl_frame = ctk.CTkFrame(self, fg_color="transparent")
        ctrl_frame.grid(row=0, column=0, sticky="ew", padx=6, pady=(6, 0))

        self._range_var = ctk.StringVar(value="1h")
        ranges = [("1 h", "1h"), ("6 h", "6h"), ("24 h", "24h"), ("7 d", "7d")]
        for i, (label, val) in enumerate(ranges):
            ctk.CTkRadioButton(
                ctrl_frame,
                text=label,
                variable=self._range_var,
                value=val,
                font=FONT_SMALL,
                command=self._on_range_changed,
            ).grid(row=0, column=i, padx=4)

    def _build_chart(self):
        self._canvas_frame = tk.Frame(self, bg="#1c1c1c")
        self._canvas_frame.grid(row=1, column=0, sticky="nsew", padx=4, pady=4)

        self._figure = Figure(figsize=(6, 3), dpi=100)
        self._figure.patch.set_facecolor("#1c1c1c")
        self._ax = self._figure.add_subplot(111)
        self._ax.set_facecolor("#1c1c1c")
        self._ax.tick_params(colors="white", labelcolor="white")
        self._ax.yaxis.label.set_color("white")
        self._ax.xaxis.label.set_color("white")

        self._mpl_canvas = FigureCanvasTkAgg(self._figure, master=self._canvas_frame)
        self._mpl_canvas.get_tk_widget().pack(fill="both", expand=True)

    def add_reading(self, timestamp: datetime, readings: dict) -> None:
        """
        Agrega una lectura al gráfico.

        Args:
            timestamp: momento de la lectura
            readings: dict con las series, ej. {"temp": 24.5, "hum": 60.0}
        """
        self._timestamps.append(timestamp)

        for key in self._data:
            value = readings.get(key)
            self._data[key].append(value if value is not None else float('nan'))

        # Limitar a últimas 1000 muestras para no saturar memoria
        if len(self._timestamps) > 1000:
            self._timestamps = self._timestamps[-1000:]
            for key in self._data:
                self._data[key] = self._data[key][-1000:]

        self._draw_chart()

    def clear_data(self) -> None:
        """Limpia todos los datos del gráfico."""
        self._timestamps.clear()
        for key in self._data:
            self._data[key].clear()
        self._draw_chart()

    def update_data(self, timestamps: list, hum_suelo: list | None = None,
                    hum_aire: list | None = None, temp: list | None = None) -> None:
        """
        Reemplaza todos los datos del gráfico de una sola vez.
        Usado al cargar historial desde DB o al reconstruir desde caché en tiempo real.
        Mapea las series genéricas (hum_suelo, hum_aire, temp) a las claves internas
        definidas en SERIES_CONFIG (por ahora "temp" y "hum" para dht11).
        """
        n = len(timestamps)

        def _pad(values: list | None) -> list:
            values = list(values) if values else []
            if len(values) < n:
                values = values + [None] * (n - len(values))
            return values[:n]

        source_by_key = {
            "temp": _pad(temp),
            "hum": _pad(hum_aire),
            "hum_suelo": _pad(hum_suelo),
        }

        self._timestamps = list(timestamps)
        for key in self._data:
            raw = source_by_key.get(key, [None] * n)
            self._data[key] = [v if v is not None else float('nan') for v in raw]

        # Mismo límite de 1000 muestras que usa add_reading()
        if len(self._timestamps) > 1000:
            self._timestamps = self._timestamps[-1000:]
            for key in self._data:
                self._data[key] = self._data[key][-1000:]

        self._draw_chart()


    def _on_range_changed(self):
        self._draw_chart()

    def _draw_chart(self):
        self._ax.clear()
        self._ax.set_facecolor("#1c1c1c")

        # Restaurar colores tras clear()
        self._ax.tick_params(colors="white", labelcolor="white", labelsize=8)
        self._ax.yaxis.label.set_color("white")
        self._ax.xaxis.label.set_color("white")
        for label in self._ax.get_xticklabels() + self._ax.get_yticklabels():
            label.set_color("white")

        if not self._timestamps:
            self._ax.text(0.5, 0.5, "Sin datos",
                          transform=self._ax.transAxes,
                          ha="center", va="center",
                          color="white", fontsize=10)
            self._mpl_canvas.draw()
            return

        # Filtrar por rango seleccionado
        range_str = self._range_var.get()
        delta = {
            "1h": timedelta(hours=1),
            "6h": timedelta(hours=6),
            "24h": timedelta(days=1),
            "7d": timedelta(days=7),
        }[range_str]

        now = datetime.now()
        start_idx = 0
        for i, ts in enumerate(self._timestamps):
            if ts >= (now - delta):
                start_idx = i
                break

        ts_slice = self._timestamps[start_idx:]

        # Dibujar cada serie configurada
        for key, label, color in self._series_config:
            values = self._data[key][start_idx:]
            if any(v == v for v in values):  # al menos un valor no-NaN
                self._ax.plot(ts_slice, values, label=label, color=color, linewidth=1.5)

        for spine in self._ax.spines.values():
            spine.set_edgecolor("#3F3F3F")

        self._ax.legend(fontsize=8, facecolor="#2B2B2B",
                        edgecolor="#3F3F3F", labelcolor="white")
        self._ax.set_xlabel("Tiempo", fontsize=8, color="white")
        self._ax.set_ylabel("Valor", fontsize=8, color="white")
        self._ax.grid(True, alpha=0.2, color="#3F3F3F")
        self._figure.autofmt_xdate()

        for label in self._ax.get_xticklabels() + self._ax.get_yticklabels():
            label.set_color("white")

        self._mpl_canvas.draw()