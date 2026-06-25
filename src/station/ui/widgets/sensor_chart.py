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
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", corner_radius=0)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

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

        ctk.CTkButton(
            ctrl_frame,
            text="Exportar PNG",
            font=FONT_SMALL,
            width=100,
            command=self._export_png,
        ).grid(row=0, column=len(ranges), padx=8, sticky="e")
        ctrl_frame.grid_columnconfigure(len(ranges), weight=1)

        self._canvas_frame = tk.Frame(self, bg="#1c1c1c")
        self._canvas_frame.grid(row=1, column=0, sticky="nsew", padx=4, pady=4)

        self._figure = Figure(figsize=(6, 3), dpi=100)
        self._figure.patch.set_facecolor("#1c1c1c")
        self._ax = self._figure.add_subplot(111)
        self._ax.set_facecolor("#1c1c1c")
        self._ax.tick_params(colors="white", labelcolor="white")  # ← estado inicial
        self._ax.yaxis.label.set_color("white")
        self._ax.xaxis.label.set_color("white")

        self._mpl_canvas = FigureCanvasTkAgg(self._figure, master=self._canvas_frame)
        self._mpl_canvas.get_tk_widget().pack(fill="both", expand=True)

        self._timestamps = []
        self._hum_suelo = []
        self._hum_aire = []
        self._temp = []
        self._umbral_min = None
        self._umbral_max = None

    def update_data(self, timestamps, hum_suelo, hum_aire, temp,
                    umbral_min=None, umbral_max=None):
        self._timestamps = timestamps
        self._hum_suelo = hum_suelo
        self._hum_aire = hum_aire
        self._temp = temp
        self._umbral_min = umbral_min
        self._umbral_max = umbral_max
        self._draw_chart()

    def _on_range_changed(self):
        self._draw_chart()

    def _draw_chart(self):
        self._ax.clear()
        self._ax.set_facecolor("#1c1c1c")

        # Restaurar colores tras clear() — matplotlib los resetea al default
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

        range_str = self._range_var.get()
        delta = {
            "1h": timedelta(hours=1),
            "6h": timedelta(hours=6),
            "24h": timedelta(days=1),
            "7d": timedelta(days=7),
        }[range_str]

        now = datetime.now()
        mask = [ts >= (now - delta) for ts in self._timestamps]
        ts = [self._timestamps[i] for i, m in enumerate(mask) if m]
        hs = [self._hum_suelo[i] for i, m in enumerate(mask) if m]
        ha = [self._hum_aire[i] for i, m in enumerate(mask) if m]
        tp = [self._temp[i] for i, m in enumerate(mask) if m]

        if ts:
            self._ax.plot(ts, hs, label="Hum. suelo (%)", color="#22C55E")
            self._ax.plot(ts, ha, label="Hum. aire (%)", color="#3B82F6")
            self._ax.plot(ts, tp, label="Temp. (°C)", color="#EF4444")

        if self._umbral_min is not None and ts:
            self._ax.axhline(y=self._umbral_min, color="orange",
                             linestyle="--", label="Umbral mín")
        if self._umbral_max is not None and ts:
            self._ax.axhline(y=self._umbral_max, color="red",
                             linestyle="--", label="Umbral máx")

        for spine in self._ax.spines.values():
            spine.set_edgecolor("#3F3F3F")

        self._ax.legend(fontsize=8, facecolor="#2B2B2B",
                        edgecolor="#3F3F3F", labelcolor="white")
        self._ax.set_xlabel("Tiempo", fontsize=8, color="white")
        self._ax.grid(True, alpha=0.2, color="#3F3F3F")
        self._figure.autofmt_xdate()

        # Volver a aplicar color blanco después de autofmt_xdate()
        # ya que también puede resetear las etiquetas del eje X
        for label in self._ax.get_xticklabels() + self._ax.get_yticklabels():
            label.set_color("white")

        self._mpl_canvas.draw()

    def _export_png(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG", "*.png")],
            title="Guardar gráfico como PNG",
        )
        if path:
            self._figure.savefig(path, dpi=150, facecolor="#1c1c1c")
