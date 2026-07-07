from __future__ import annotations

import math
import customtkinter as ctk

from ui.theme import FONT_NORMAL, FONT_TITLE, FONT_SMALL


class GaugeWidget(ctk.CTkFrame):
    """
    Medidor circular tipo gauge.
    Ideal para mostrar temperatura y humedad actuales de forma visual.
    """

    def __init__(
        self,
        master,
        title: str = "Sensor",
        unit: str = "",
        min_val: float = 0.0,
        max_val: float = 100.0,
        color_low: str = "#3B82F6",   # azul
        color_mid: str = "#F59E0B",   # naranja
        color_high: str = "#EF4444",  # rojo
        size: int = 160,
        **kwargs,
    ):
        super().__init__(master, corner_radius=16, border_width=1, border_color="#3F3F3F", **kwargs)
        self._title = title
        self._unit = unit
        self._min_val = min_val
        self._max_val = max_val
        self._colors = (color_low, color_mid, color_high)
        self._size = size
        self._value: float | None = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._canvas = ctk.CTkCanvas(
            self, width=size, height=size,
            bg=self._get_bg(), highlightthickness=0,
        )
        self._canvas.grid(row=0, column=0, padx=12, pady=(12, 4))

        self._lbl_value = ctk.CTkLabel(
            self, text="—", font=("Roboto", 28, "bold"),
        )
        self._lbl_value.grid(row=1, column=0, pady=(0, 2))

        self._lbl_title = ctk.CTkLabel(
            self, text=title, font=FONT_SMALL, text_color="gray",
        )
        self._lbl_title.grid(row=2, column=0, pady=(0, 12))

        self._draw_gauge()

    def _get_bg(self) -> str:
        # customtkinter no expone bg directamente, usamos el color del frame
        return "#2B2B2B"

    def set_value(self, value: float | None):
        self._value = value
        if value is None:
            self._lbl_value.configure(text="—")
        else:
            self._lbl_value.configure(text=f"{value:.1f} {self._unit}")
        self._draw_gauge()

    def _draw_gauge(self):
        self._canvas.delete("all")
        size = self._size
        cx, cy = size // 2, size // 2
        radius = (size // 2) - 20
        start_angle = 135
        end_angle = 405
        total_angle = end_angle - start_angle

        # Arco de fondo
        self._canvas.create_arc(
            cx - radius, cy - radius, cx + radius, cy + radius,
            start=start_angle, extent=total_angle,
            style="arc", outline="#3F3F3F", width=12,
        )

        if self._value is None:
            return

        # Color según valor
        ratio = (self._value - self._min_val) / (self._max_val - self._min_val)
        ratio = max(0.0, min(1.0, ratio))
        if ratio < 0.5:
            color = self._colors[0]
        elif ratio < 0.8:
            color = self._colors[1]
        else:
            color = self._colors[2]

        # Arco de valor
        extent = total_angle * ratio
        self._canvas.create_arc(
            cx - radius, cy - radius, cx + radius, cy + radius,
            start=start_angle, extent=extent,
            style="arc", outline=color, width=12,
        )

        # Aguja
        angle_rad = math.radians(start_angle + extent)
        needle_len = radius - 8
        x2 = cx + needle_len * math.cos(angle_rad)
        y2 = cy - needle_len * math.sin(angle_rad)
        self._canvas.create_line(cx, cy, x2, y2, fill="white", width=2)
        self._canvas.create_oval(cx - 4, cy - 4, cx + 4, cy + 4, fill="white", outline="")

        # Marcas
        for i in range(0, 6):
            mark_ratio = i / 5
            mark_angle = math.radians(start_angle + total_angle * mark_ratio)
            r1 = radius - 18
            r2 = radius - 6
            x1 = cx + r1 * math.cos(mark_angle)
            y1 = cy - r1 * math.sin(mark_angle)
            x2 = cx + r2 * math.cos(mark_angle)
            y2 = cy - r2 * math.sin(mark_angle)
            self._canvas.create_line(x1, y1, x2, y2, fill="#6B7280", width=2)

            # Labels de min/max
            val_label = self._min_val + (self._max_val - self._min_val) * mark_ratio
            tx = cx + (radius - 28) * math.cos(mark_angle)
            ty = cy - (radius - 28) * math.sin(mark_angle)
            self._canvas.create_text(
                int(tx), int(ty), text=f"{val_label:.0f}",
                fill="#9CA3AF", font=("Roboto", 8),
            )
