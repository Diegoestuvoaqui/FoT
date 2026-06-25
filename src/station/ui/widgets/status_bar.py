"""
ui/widgets/status_bar.py
Barra inferior de estado: última sincronización, alertas, broker MQTT y USB.

Uso:
    bar = StatusBar(root)
    bar.pack(side="bottom", fill="x")
    bar.start_clock(root)        # actualiza el reloj de sync cada segundo

    # Desde callbacks:
    bar.mark_sync()              # llamar al recibir cualquier mensaje MQTT
    bar.update_mqtt(True)
    bar.update_alerts(3)
    bar.update_usb_count(1)
"""
from __future__ import annotations

from datetime import datetime

import customtkinter as ctk

from ui.theme import (
    COLORS, BG_STATUSBAR, DIVIDER,
    FONT_SMALL,
    STATUSBAR_HEIGHT,
)


class StatusBar(ctk.CTkFrame):
    """
    Franja horizontal en la parte inferior de la ventana.

    Columnas:
        Izquierda  — última sincronización con el servidor
        Centro     — estado del broker MQTT
        Derecha    — alertas activas | placas USB conectadas
    """

    def __init__(self, master, **kwargs) -> None:
        kwargs.setdefault("height", STATUSBAR_HEIGHT)
        kwargs.setdefault("corner_radius", 0)
        kwargs.setdefault("fg_color", BG_STATUSBAR)
        super().__init__(master, **kwargs)

        self.pack_propagate(False)
        self._last_sync: datetime | None = None
        self._clock_running = False

        self._build()

    # ------------------------------------------------------------------
    # Construcción
    # ------------------------------------------------------------------

    def _build(self) -> None:
        # ── Izquierda: última sincronización ────────────────────────
        left = ctk.CTkFrame(self, fg_color="transparent")
        left.pack(side="left", padx=(12, 0))

        self._sync_label = ctk.CTkLabel(
            left,
            text="Sin datos del servidor",
            font=FONT_SMALL,
            text_color=("gray40", "gray55"),
        )
        self._sync_label.pack(side="left")

        _sep(self)

        # ── Centro: broker MQTT ──────────────────────────────────────
        center = ctk.CTkFrame(self, fg_color="transparent")
        center.pack(side="left")

        self._broker_dot = ctk.CTkLabel(
            center,
            text="●",
            font=FONT_SMALL,
            text_color=COLORS["disconnected"],
            width=10,
        )
        self._broker_dot.pack(side="left")

        self._broker_label = ctk.CTkLabel(
            center,
            text="Broker MQTT desconectado",
            font=FONT_SMALL,
            text_color=("gray40", "gray55"),
        )
        self._broker_label.pack(side="left", padx=(3, 0))

        # ── Derecha: alertas + USB ───────────────────────────────────
        right = ctk.CTkFrame(self, fg_color="transparent")
        right.pack(side="right", padx=(0, 12))

        self._usb_label = ctk.CTkLabel(
            right,
            text="0 USB",
            font=FONT_SMALL,
            text_color=("gray40", "gray55"),
        )
        self._usb_label.pack(side="right")

        _sep(right)

        self._alerts_dot = ctk.CTkLabel(
            right,
            text="●",
            font=FONT_SMALL,
            text_color=COLORS["unknown"],
            width=10,
        )
        self._alerts_dot.pack(side="right")

        self._alerts_label = ctk.CTkLabel(
            right,
            text="Sin alertas",
            font=FONT_SMALL,
            text_color=("gray40", "gray55"),
        )
        self._alerts_label.pack(side="right", padx=(0, 3))

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def mark_sync(self) -> None:
        """
        Registrar el momento de la última sincronización.
        Llamar desde DataReceiver al recibir cualquier mensaje MQTT.
        """
        self._last_sync = datetime.now()

    def start_clock(self, root) -> None:
        """
        Iniciar el refresco del label de sincronización cada segundo.
        Llamar una sola vez desde MainWindow tras construir la ventana.
        """
        if not self._clock_running:
            self._clock_running = True
            self._tick(root)

    def update_mqtt(self, connected: bool) -> None:
        """Actualizar indicador de estado del broker."""
        color = COLORS["connected"] if connected else COLORS["disconnected"]
        text = "Broker MQTT conectado" if connected else "Broker MQTT desconectado"
        self._broker_dot.configure(text_color=color)
        self._broker_label.configure(text=text)

    def update_alerts(self, count: int) -> None:
        """
        Actualizar contador de alertas activas.
        count == 0 → indicador gris "Sin alertas".
        count > 0  → indicador rojo con el número.
        """
        if count == 0:
            self._alerts_label.configure(text="Sin alertas",
                                         text_color=("gray40", "gray55"))
            self._alerts_dot.configure(text_color=COLORS["unknown"])
        else:
            plural = "s" if count != 1 else ""
            self._alerts_label.configure(
                text=f"{count} alerta{plural} activa{plural}",
                text_color=COLORS["fault"],
            )
            self._alerts_dot.configure(text_color=COLORS["fault"])

    def update_usb_count(self, count: int) -> None:
        """Actualizar contador de placas USB conectadas."""
        plural = "s" if count != 1 else ""
        color = COLORS["connected"] if count > 0 else ("gray40", "gray55")
        self._usb_label.configure(
            text=f"{count} USB",
            text_color=color,
        )

    # ------------------------------------------------------------------
    # Interno
    # ------------------------------------------------------------------

    def _tick(self, root) -> None:
        """Refrescar el label de sincronización cada segundo."""
        self._refresh_sync_label()
        root.after(1_000, lambda: self._tick(root))

    def _refresh_sync_label(self) -> None:
        if self._last_sync is None:
            self._sync_label.configure(text="Sin datos del servidor")
            return

        elapsed = int((datetime.now() - self._last_sync).total_seconds())
        if elapsed < 5:
            text = "Sync: ahora mismo"
        elif elapsed < 60:
            text = f"Sync: hace {elapsed} s"
        elif elapsed < 3600:
            text = f"Sync: hace {elapsed // 60} min"
        else:
            text = f"Sync: hace {elapsed // 3600} h"

        # Si llevan más de 2 min sin datos, resaltar en ámbar
        color = COLORS["warning"] if elapsed > 120 else ("gray40", "gray55")
        self._sync_label.configure(text=text, text_color=color)


# ---------------------------------------------------------------------------
# Helper local
# ---------------------------------------------------------------------------

def _sep(parent) -> None:
    """Separador vertical para la barra de estado."""
    ctk.CTkFrame(
        parent,
        width=1,
        height=14,
        fg_color=DIVIDER,
        corner_radius=0,
    ).pack(side="left" if parent.winfo_class() != "CTk" else "right",
           padx=10)
