from __future__ import annotations

import customtkinter as ctk

from ui.theme import FONT_NORMAL, FONT_SMALL, COLORS


class SensorCard(ctk.CTkFrame):
    """
    Tarjeta moderna con valor numérico grande y barra de progreso.
    Alternativa compacta al gauge circular.
    """

    def __init__(
        self,
        master,
        title: str = "Sensor",
        unit: str = "",
        min_val: float = 0.0,
        max_val: float = 100.0,
        color: str = "#3B82F6",
        **kwargs,
    ):
        super().__init__(
            master, corner_radius=12, border_width=1,
            border_color=COLORS["border"], fg_color="#2B2B2B",
            **kwargs,
        )
        self._min_val = min_val
        self._max_val = max_val
        self._color = color

        self.grid_columnconfigure(0, weight=1)

        # Título
        ctk.CTkLabel(self, text=title, font=FONT_SMALL, text_color="gray").grid(
            row=0, column=0, padx=12, pady=(10, 2), sticky="w")

        # Valor grande
        self._lbl_value = ctk.CTkLabel(
            self, text="—", font=("Roboto", 32, "bold"),
        )
        self._lbl_value.grid(row=1, column=0, padx=12, pady=2, sticky="w")

        # Barra de progreso
        self._progress = ctk.CTkProgressBar(
            self, height=8, corner_radius=4,
            progress_color=color, fg_color="#3F3F3F",
        )
        self._progress.grid(row=2, column=0, padx=12, pady=(4, 10), sticky="ew")
        self._progress.set(0)

    def set_value(self, value: float | None):
        if value is None:
            self._lbl_value.configure(text="—")
            self._progress.set(0)
            return

        ratio = (value - self._min_val) / (self._max_val - self._min_val)
        ratio = max(0.0, min(1.0, ratio))
        self._progress.set(ratio)
        self._lbl_value.configure(text=f"{value:.1f}")
