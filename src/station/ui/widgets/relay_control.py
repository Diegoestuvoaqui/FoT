# ui/widgets/relay_control.py
from __future__ import annotations

from typing import Callable, Optional

import customtkinter as ctk

from ui.theme import FONT_NORMAL, FONT_SMALL, COLORS


class RelayControl(ctk.CTkFrame):
    """Switch de relé con 3 estados visuales: OFF / ON / Pendiente de ack."""

    def __init__(self, master, on_toggle: Optional[Callable[[bool], None]] = None,
                 title: str = "Relé", **kwargs):
        super().__init__(master, corner_radius=10, border_width=1,
                         border_color=COLORS["border"], **kwargs)
        self._on_toggle = on_toggle
        self._suppress_switch_event = False

        self.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self, text=title, font=FONT_NORMAL,
                     anchor="w").grid(row=0, column=0, padx=(12, 6),
                                      pady=(10, 2), sticky="w")

        self._switch = ctk.CTkSwitch(
            self, text="", command=self._on_switch_changed, width=50)
        self._switch.grid(row=0, column=1, padx=(0, 12),
                          pady=(10, 2), sticky="e")

        self._lbl_state = ctk.CTkLabel(
            self, text="—", font=FONT_SMALL, text_color="gray",
            anchor="w", justify="left")
        self._lbl_state.grid(row=1, column=0, columnspan=2,
                             padx=12, pady=(0, 4), sticky="ew")

        self._lbl_detail = ctk.CTkLabel(
            self, text="", font=FONT_SMALL, text_color="gray",
            anchor="w", justify="left")
        self._lbl_detail.grid(row=2, column=0, columnspan=2,
                              padx=12, pady=(0, 10), sticky="ew")

    def update_state(self,
                     reported: int | None,
                     desired: int | None,
                     connected: bool,
                     enabled: bool,
                     last_change_text: str = "") -> None:
        """Refresca el switch sin disparar on_toggle."""
        pending = (
            connected
            and reported is not None
            and desired is not None
            and bool(reported) != bool(desired)
        )
        target = bool(desired if desired is not None else reported or 0)

        self._suppress_switch_event = True
        if target:
            self._switch.select()
        else:
            self._switch.deselect()
        self._suppress_switch_event = False

        self._switch.configure(state="normal" if enabled else "disabled")

        if not connected:
            self._lbl_state.configure(
                text="Sin conexión", text_color=COLORS["unknown"])
        elif pending:
            self._lbl_state.configure(
                text="Confirmando…", text_color=COLORS["warning"])
        elif reported:
            self._lbl_state.configure(
                text="Encendido", text_color=COLORS["accent"])
        else:
            self._lbl_state.configure(
                text="Apagado", text_color="gray")

        self._lbl_detail.configure(text=last_change_text or "")

    def _on_switch_changed(self) -> None:
        if self._suppress_switch_event:
            return
        if self._on_toggle is None:
            return
        self._on_toggle(bool(self._switch.get()))