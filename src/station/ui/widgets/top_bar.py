# ui/widgets/top_bar.py
"""
Barra superior fija: logo, indicadores de conexión y campana de notificaciones.

Uso:
    bar = TopBar(root, notification_manager=mgr, on_bell_click=lambda: ...)
    bar.update_mqtt_status(connected=True)
    bar.update_boards_count(3)
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Optional

import customtkinter as ctk

from ui.theme import (
    COLORS, BG_TOPBAR, DIVIDER,
    FONT_LOGO, FONT_NORMAL, FONT_SMALL,
    TOPBAR_HEIGHT,
)


class TopBar(ctk.CTkFrame):
    """
    Barra horizontal en la parte superior de la ventana.

    Columnas:
        Izquierda  — logo "IoT" + subtítulo
        Derecha    — estado MQTT local | placas activas | campana notificaciones
    """

    def __init__(
            self,
            master,
            notification_manager=None,
            on_bell_click: Optional[Callable[[], None]] = None,
            **kwargs,
    ) -> None:
        kwargs.setdefault("height", TOPBAR_HEIGHT)
        kwargs.setdefault("corner_radius", 0)
        kwargs.setdefault("fg_color", BG_TOPBAR)
        super().__init__(master, **kwargs)

        self.pack_propagate(False)
        self._notif_mgr = notification_manager
        self._on_bell_click = on_bell_click
        self._notification_count = 0

        self._build()

        # Registrar observer para actualizar badge automáticamente
        if self._notif_mgr:
            self._notif_mgr.add_observer(self._update_badge)

    # ------------------------------------------------------------------
    # Construcción
    # ------------------------------------------------------------------

    def _build(self) -> None:
        # ── Bloque izquierdo: logo + subtítulo ──────────────────────
        left = ctk.CTkFrame(self, fg_color="transparent")
        left.pack(side="left", padx=(16, 0), pady=0)

        self._logo = ctk.CTkLabel(
            left,
            text="IoT",
            font=FONT_LOGO,
            text_color=COLORS["accent"],
        )
        self._logo.pack(side="left")

        self._subtitle = ctk.CTkLabel(
            left,
            text=" — Farm of Things",
            font=FONT_NORMAL,
            text_color=("gray40", "gray60"),
        )
        self._subtitle.pack(side="left", padx=(2, 0))

        # ── Bloque derecho: indicadores ──────────────────────────────
        right = ctk.CTkFrame(self, fg_color="transparent")
        right.pack(side="right", padx=16, pady=0)

        # Campana de notificaciones (con badge)
        self._bell_frame = ctk.CTkFrame(right, fg_color="transparent")
        self._bell_frame.pack(side="right", padx=(12, 0))

        self._bell_btn = ctk.CTkButton(
            self._bell_frame,
            text="🔔",
            width=36,
            height=36,
            corner_radius=8,
            fg_color="transparent",
            hover_color=("gray80", "#2e2e2e"),
            font=FONT_NORMAL,
            command=self._handle_bell,
        )
        self._bell_btn.pack()

        # Badge de conteo sobre la campana
        self._badge = ctk.CTkLabel(
            self._bell_frame,
            text="",
            font=("Roboto", 9, "bold"),
            width=16,
            height=16,
            corner_radius=8,
            fg_color=COLORS["badge_error"],
            text_color="white",
        )

        # Separador
        _separator(right)

        # Contador de placas activas
        self._boards_dot = ctk.CTkLabel(
            right,
            text="●",
            font=FONT_SMALL,
            text_color=COLORS["unknown"],
            width=12,
        )
        self._boards_dot.pack(side="right")

        self._boards_label = ctk.CTkLabel(
            right,
            text="0 placas",
            font=FONT_SMALL,
            text_color=("gray30", "gray70"),
        )
        self._boards_label.pack(side="right", padx=(0, 4))

        # Separador
        _separator(right)

        # Estado del broker MQTT local
        self._mqtt_text = ctk.CTkLabel(
            right,
            text="Broker local: detenido",
            font=FONT_SMALL,
            text_color=("gray30", "gray70"),
        )
        self._mqtt_text.pack(side="right", padx=(0, 4))

        self._mqtt_dot = ctk.CTkLabel(
            right,
            text="●",
            font=FONT_SMALL,
            text_color=COLORS["disconnected"],
            width=12,
        )
        self._mqtt_dot.pack(side="right")

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def update_mqtt_status(self, connected: bool) -> None:
        """Actualizar indicador de conexión al broker MQTT local."""
        color = COLORS["connected"] if connected else COLORS["disconnected"]
        text = "Broker local: activo" if connected else "Broker local: detenido"
        self._mqtt_dot.configure(text_color=color)
        self._mqtt_text.configure(text=text)

    def update_boards_count(self, count: int) -> None:
        """Actualizar contador de placas Arduino activas."""
        self._boards_label.configure(text=f"{count} placa{'s' if count != 1 else ''}")
        color = COLORS["connected"] if count > 0 else COLORS["unknown"]
        self._boards_dot.configure(text_color=color)

    def _update_badge(self) -> None:
        """Callback del NotificationManager para actualizar el badge."""
        if self._notif_mgr:
            count = self._notif_mgr.get_unread_count()
            self.update_notification_count(count)

    def update_notification_count(self, count: int) -> None:
        """
        Actualizar badge de la campana.
        count == 0 → ocultar badge.
        count > 0  → mostrar badge rojo con el número.
        """
        self._notification_count = count
        if count > 0:
            display = str(count) if count < 100 else "99+"
            self._badge.configure(text=display)
            self._badge.place(relx=0.65, rely=0.0, anchor="n")
            self._bell_btn.configure(text_color=COLORS["badge_error"])
        else:
            self._badge.place_forget()
            self._bell_btn.configure(text_color=("gray40", "gray60"))

    # ------------------------------------------------------------------
    # Interno
    # ------------------------------------------------------------------

    def _handle_bell(self) -> None:
        if self._notif_mgr:
            self._notif_mgr.mark_all_read()
        if callable(self._on_bell_click):
            self._on_bell_click()

    def destroy(self):
        """Limpieza al destruir el widget."""
        if self._notif_mgr:
            self._notif_mgr.remove_observer(self._update_badge)
        super().destroy()


# ---------------------------------------------------------------------------
# Helpers locales
# ---------------------------------------------------------------------------

def _separator(parent) -> None:
    """Línea vertical divisoria en la barra superior."""
    ctk.CTkFrame(
        parent,
        width=1,
        height=24,
        fg_color=DIVIDER,
        corner_radius=0,
    ).pack(side="right", padx=8)
