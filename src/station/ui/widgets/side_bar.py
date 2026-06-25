# ui/widgets/side_bar.py
"""
ui/widgets/side_bar.py
Barra lateral de navegación.
"""
from __future__ import annotations

import customtkinter as ctk

from ui.theme import (
    COLORS, BG_SIDEBAR,
    FONT_NORMAL, NAV_ITEMS, NAV_BOTTOM_ITEMS,
    SIDEBAR_WIDTH,
)


class SideBar(ctk.CTkFrame):
    """
    Barra lateral con botones de navegación.
    """

    def __init__(
            self,
            master,
            on_navigate: callable,
            **kwargs,
    ) -> None:
        kwargs.setdefault("width", SIDEBAR_WIDTH)
        kwargs.setdefault("corner_radius", 0)
        kwargs.setdefault("fg_color", BG_SIDEBAR)
        super().__init__(master, **kwargs)

        self.pack_propagate(False)
        self._on_navigate = on_navigate
        self._active: str | None = None
        self._buttons: dict[str, ctk.CTkButton] = {}

        self._build()

    # ------------------------------------------------------------------
    # Construcción
    # ------------------------------------------------------------------

    def _build(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent", height=16)
        header.pack(fill="x")

        # ── Botones principales ─────────────────────────────────────
        self._top_group = ctk.CTkFrame(self, fg_color="transparent")
        self._top_group.pack(fill="x", padx=8, pady=(4, 0))

        for section, label, tooltip in NAV_ITEMS:
            btn = self._make_nav_button(self._top_group, section, label, tooltip)
            btn.pack(fill="x", pady=2)
            self._buttons[section] = btn

        # ── Separador ───────────────────────────────────────────────
        ctk.CTkFrame(
            self,
            height=1,
            fg_color=("gray75", "#2e2e2e"),
            corner_radius=0,
        ).pack(fill="x", padx=16, pady=12)

        # ── Botón de ajustes (fondo) ─────────────────────────────────
        self._bottom_group = ctk.CTkFrame(self, fg_color="transparent")
        self._bottom_group.pack(side="bottom", fill="x", padx=8, pady=8)

        for section, label, tooltip in NAV_BOTTOM_ITEMS:
            btn = self._make_nav_button(self._bottom_group, section, label, tooltip)
            btn.pack(fill="x", pady=2)
            self._buttons[section] = btn

    def _make_nav_button(
            self,
            parent,
            section: str,
            label: str,
            tooltip: str,
    ) -> ctk.CTkButton:
        btn = ctk.CTkButton(
            parent,
            text=label,
            font=FONT_NORMAL,
            height=40,
            corner_radius=8,
            anchor="w",
            fg_color="transparent",
            text_color=("gray20", "gray80"),
            hover_color=("gray80", COLORS["nav_hover"]),
            command=lambda s=section: self._handle_click(s),
        )
        _attach_tooltip(btn, tooltip)
        return btn

    # ------------------------------------------------------------------
    # API pública dinámica
    # ------------------------------------------------------------------

    def add_nav_button(self, section: str, label: str, tooltip: str) -> None:
        """Añade un botón de navegación en tiempo de ejecución (ej. Admin)."""
        if section in self._buttons:
            return
        btn = self._make_nav_button(self._top_group, section, label, tooltip)
        # Insertar antes del separador (al final del top_group)
        btn.pack(fill="x", pady=2)
        self._buttons[section] = btn

    def remove_nav_button(self, section: str) -> None:
        """Elimina un botón de navegación dinámico."""
        btn = self._buttons.pop(section, None)
        if btn:
            btn.destroy()

    def set_active(self, section: str) -> None:
        """
        Resaltar el botón de la sección activa.
        """
        if self._active and self._active in self._buttons:
            self._buttons[self._active].configure(
                fg_color="transparent",
                text_color=("gray20", "gray80"),
                font=FONT_NORMAL,
            )

        if section in self._buttons:
            self._buttons[section].configure(
                fg_color=("gray82", COLORS["nav_active"]),
                text_color=(COLORS["accent"], COLORS["accent"]),
                font=("Roboto", 13, "bold"),
            )
            self._active = section

    # ------------------------------------------------------------------
    # Interno
    # ------------------------------------------------------------------

    def _handle_click(self, section: str) -> None:
        self.set_active(section)
        if callable(self._on_navigate):
            self._on_navigate(section)


# ---------------------------------------------------------------------------
# Tooltip mínimo
# ---------------------------------------------------------------------------

class _Tooltip:
    DELAY_MS = 600

    def __init__(self, widget, text: str) -> None:
        self._widget = widget
        self._text = text
        self._win = None
        self._after = None

        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<Button>", self._hide, add="+")

    def _schedule(self, _event=None) -> None:
        self._after = self._widget.after(self.DELAY_MS, self._show)

    def _show(self, _event=None) -> None:
        if self._win:
            return
        x = self._widget.winfo_rootx() + self._widget.winfo_width() + 4
        y = self._widget.winfo_rooty() + self._widget.winfo_height() // 2 - 10
        self._win = ctk.CTkToplevel(self._widget)
        self._win.wm_overrideredirect(True)
        self._win.wm_geometry(f"+{x}+{y}")
        ctk.CTkLabel(
            self._win,
            text=self._text,
            font=("Roboto", 11),
            fg_color=("gray20", "#2e2e2e"),
            text_color=("white", "gray90"),
            corner_radius=4,
            padx=8,
            pady=4,
        ).pack()

    def _hide(self, _event=None) -> None:
        if self._after:
            self._widget.after_cancel(self._after)
            self._after = None
        if self._win:
            self._win.destroy()
            self._win = None


def _attach_tooltip(widget, text: str) -> None:
    _Tooltip(widget, text)
