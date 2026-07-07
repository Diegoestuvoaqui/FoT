from __future__ import annotations

import math
from datetime import datetime, timedelta
from typing import Callable

import customtkinter as ctk

from ui.theme import FONT_SMALL, FONT_NORMAL


class CanvasLineChart(ctk.CTkFrame):
    """
    Gráfico de líneas liviano usando CTkCanvas.
    Rápido, bonito y sin dependencias pesadas.
    """

    def __init__(
        self,
        master,
        series: list[tuple[str, str, str]] | None = None,
        max_points: int = 200,
        **kwargs,
    ):
        super().__init__(master, fg_color="transparent", corner_radius=12, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # series: [(key, label, color), ...]
        self._series = series or [
            ("temp", "Temperatura (°C)", "#EF4444"),
            ("hum", "Humedad (%)", "#3B82F6"),
        ]
        self._max_points = max_points
        self._data: dict[str, list[float | None]] = {
            k: [] for k, _, _ in self._series
        }
        self._timestamps: list[datetime] = []

        self._hover_callback: Callable | None = None
        self._hover_idx: int | None = None

        self._build_controls()
        self._build_canvas()

    def _build_controls(self):
        ctrl = ctk.CTkFrame(self, fg_color="transparent")
        ctrl.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 0))

        self._range_var = ctk.StringVar(value="1h")
        for i, (label, val) in enumerate([("1 h", "1h"), ("6 h", "6h"), ("24 h", "24h"), ("7 d", "7d")]):
            ctk.CTkRadioButton(
                ctrl, text=label, variable=self._range_var, value=val,
                font=FONT_SMALL, command=self._draw_chart,
            ).grid(row=0, column=i, padx=4)

    def _build_canvas(self):
        self._canvas = ctk.CTkCanvas(
            self, bg="#1c1c1c", highlightthickness=0,
        )
        self._canvas.grid(row=1, column=0, sticky="nsew", padx=8, pady=8)
        self._canvas.bind("<Configure>", lambda e: self._draw_chart())
        self._canvas.bind("<Motion>", self._on_mouse_move)
        self._canvas.bind("<Leave>", lambda e: self._clear_tooltip())

    # --- API pública ---

    def add_reading(self, timestamp: datetime, readings: dict):
        self._timestamps.append(timestamp)
        for key, _, _ in self._series:
            val = readings.get(key)
            self._data[key].append(val if val is not None else None)

        if len(self._timestamps) > self._max_points:
            self._timestamps = self._timestamps[-self._max_points:]
            for key in self._data:
                self._data[key] = self._data[key][-self._max_points:]

        self._draw_chart()

    def update_data(self, timestamps: list[datetime], **series_data):
        n = len(timestamps)
        self._timestamps = list(timestamps)
        for key, _, _ in self._series:
            raw = series_data.get(key, [None] * n)
            self._data[key] = [v if v is not None else None for v in raw[:n]]
        self._draw_chart()

    def clear(self):
        self._timestamps.clear()
        for k in self._data:
            self._data[k].clear()
        self._draw_chart()

    # --- Dibujo ---

    def _draw_chart(self):
        self._canvas.delete("all")
        w = self._canvas.winfo_width()
        h = self._canvas.winfo_height()
        if w < 50 or h < 50:
            self.after(100, self._draw_chart)
            return

        margin_left = 50
        margin_right = 20
        margin_top = 20
        margin_bottom = 40
        chart_w = w - margin_left - margin_right
        chart_h = h - margin_top - margin_bottom

        # Fondo
        self._canvas.create_rectangle(0, 0, w, h, fill="#1c1c1c", outline="")

        # Filtrar por rango
        ts_slice, data_slice = self._filter_by_range()
        if not ts_slice:
            self._canvas.create_text(
                w // 2, h // 2, text="Sin datos",
                fill="#9CA3AF", font=("Roboto", 14),
            )
            return

        # Calcular escalas
        all_vals = [v for key in self._data for v in data_slice.get(key, []) if v is not None]
        if not all_vals:
            return

        y_min = min(all_vals) * 0.95
        y_max = max(all_vals) * 1.05
        if y_min == y_max:
            y_min -= 1
            y_max += 1

        def x_of(i: int) -> float:
            return margin_left + (i / max(1, len(ts_slice) - 1)) * chart_w

        def y_of(v: float | None) -> float | None:
            if v is None:
                return None
            return margin_top + chart_h - ((v - y_min) / (y_max - y_min)) * chart_h

        # Grid horizontal
        steps = 5
        for i in range(steps + 1):
            val = y_min + (y_max - y_min) * (i / steps)
            y = y_of(val)
            self._canvas.create_line(
                margin_left, y, margin_left + chart_w, y,
                fill="#2B2B2B", width=1,
            )
            self._canvas.create_text(
                margin_left - 8, int(y), text=f"{val:.1f}",
                fill="#9CA3AF", font=FONT_SMALL, anchor="e",
            )

        # Líneas de series
        for key, label, color in self._series:
            values = data_slice.get(key, [])
            points = []
            for i, v in enumerate(values):
                y = y_of(v)
                if y is not None:
                    points.append((x_of(i), y))

            if len(points) < 2:
                continue

            # Dibujar área bajo la curva (efecto visual)
            area_pts = [margin_left, margin_top + chart_h]
            for px, py in points:
                area_pts.extend([px, py])
            area_pts.extend([margin_left + chart_w, margin_top + chart_h])
            self._canvas.create_polygon(
                area_pts, fill=color, stipple="gray25", outline="",
            )

            # Línea suavizada (simple polyline, rápida)
            flat = []
            for px, py in points:
                flat.extend([px, py])
            self._canvas.create_line(
                flat, fill=color, width=2, smooth=True,
            )

            # Puntos en los extremos
            for px, py in [points[0], points[-1]]:
                r = 3
                self._canvas.create_oval(
                    px - r, py - r, px + r, py + r,
                    fill=color, outline="white", width=1,
                )

        # Eje X: horas
        if len(ts_slice) > 1:
            x_labels = 4
            for i in range(x_labels):
                idx = int(i * (len(ts_slice) - 1) / max(1, x_labels - 1))
                ts = ts_slice[idx]
                x = x_of(idx)
                label = ts.strftime("%H:%M")
                self._canvas.create_text(
                    int(x), h - margin_bottom + 18, text=label,
                    fill="#9CA3AF", font=FONT_SMALL, anchor="n",
                )

        # Leyenda
        legend_x = w - margin_right - 10
        legend_y = margin_top + 10
        for key, label, color in reversed(self._series):
            self._canvas.create_rectangle(
                legend_x - 80, legend_y - 6, legend_x - 70, legend_y + 4,
                fill=color, outline="",
            )
            self._canvas.create_text(
                legend_x - 65, legend_y, text=label,
                fill="white", font=FONT_SMALL, anchor="w",
            )
            legend_y += 18

        # Tooltip si hay hover
        if self._hover_idx is not None and 0 <= self._hover_idx < len(ts_slice):
            self._draw_tooltip(ts_slice, data_slice, x_of, y_of)

    def _filter_by_range(self):
        if not self._timestamps:
            return [], {}
        delta = {
            "1h": timedelta(hours=1),
            "6h": timedelta(hours=6),
            "24h": timedelta(days=1),
            "7d": timedelta(days=7),
        }[self._range_var.get()]
        cutoff = datetime.now() - delta
        start_idx = 0
        for i, ts in enumerate(self._timestamps):
            if ts >= cutoff:
                start_idx = i
                break
        ts_slice = self._timestamps[start_idx:]
        data_slice = {k: v[start_idx:] for k, v in self._data.items()}
        return ts_slice, data_slice

    def _on_mouse_move(self, event):
        w = self._canvas.winfo_width()
        margin_left = 50
        margin_right = 20
        chart_w = w - margin_left - margin_right
        x = event.x - margin_left
        ts_slice, data_slice = self._filter_by_range()
        if not ts_slice or chart_w <= 0:
            return
        n = len(ts_slice)
        idx = int(round((x / chart_w) * (n - 1)))
        idx = max(0, min(n - 1, idx))
        if idx != self._hover_idx:
            self._hover_idx = idx
            self._draw_chart()

    def _draw_tooltip(self, ts_slice, data_slice, x_of, y_of):
        idx = self._hover_idx
        x = int(x_of(idx))
        ts = ts_slice[idx]
        lines = [ts.strftime("%H:%M:%S")]
        for key, label, color in self._series:
            vals = data_slice.get(key, [])
            if idx < len(vals) and vals[idx] is not None:
                lines.append(f"{label.split()[0]}: {vals[idx]:.1f}")

        # Caja de tooltip
        text = "\n".join(lines)
        bbox = self._canvas.bbox(self._canvas.create_text(0, 0, text=text, font=FONT_SMALL))
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        tx = min(x + 10, self._canvas.winfo_width() - tw - 20)
        ty = 30
        self._canvas.create_rectangle(
            tx - 6, ty - 4, tx + tw + 6, ty + th + 4,
            fill="#2B2B2B", outline="#3F3F3F", width=1,
        )
        self._canvas.create_text(tx, ty, text=text, fill="white", font=FONT_SMALL, anchor="nw")
        # Línea vertical
        self._canvas.create_line(x, 20, x, self._canvas.winfo_height() - 40, fill="white", dash=(2, 4))

    def _clear_tooltip(self):
        if self._hover_idx is not None:
            self._hover_idx = None
            self._draw_chart()
