# ui/widgets/notification_panel.py
"""
Panel deslizable que muestra el historial de notificaciones.
Se abre al hacer clic en la campana del TopBar.

Uso:
    panel = NotificationPanel(parent, notification_manager=mgr)
    panel.show()  # o toggle()
"""
from __future__ import annotations

import logging
from typing import Optional

import customtkinter as ctk

from ui.theme import FONT_NORMAL, FONT_SMALL, COLORS
from ui.widgets.notification_manager import NotificationManager, NotifType, NOTIF_COLORS, NOTIF_ICONS

logger = logging.getLogger(__name__)


class NotificationPanel(ctk.CTkFrame):
    """
    Panel de historial de notificaciones estilo "centro de notificaciones".
    """

    def __init__(self,
                 master,
                 notification_manager: NotificationManager,
                 on_close=None,
                 **kwargs):
        super().__init__(master, **kwargs)

        self._notif_mgr = notification_manager
        self._on_close = on_close
        self._rows: list[ctk.CTkFrame] = []

        self._build()
        self._refresh()

        # Observer para auto-refrescar
        self._notif_mgr.add_observer(self._refresh)

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 8))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text="Notificaciones",
            font=("Roboto", 14, "bold"),
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            header,
            text="Marcar todo leído",
            font=FONT_SMALL,
            width=120,
            height=28,
            command=self._mark_all_read,
        ).grid(row=0, column=1, padx=(8, 0))

        ctk.CTkButton(
            header,
            text="Limpiar",
            font=FONT_SMALL,
            width=80,
            height=28,
            fg_color="transparent",
            border_width=1,
            border_color=COLORS["border"],
            command=self._clear_all,
        ).grid(row=0, column=2, padx=(4, 0))

        # Lista scrollable
        self._list_frame = ctk.CTkScrollableFrame(self, label_text="")
        self._list_frame.grid(row=1, column=0, sticky="nsew", padx=12, pady=8)
        self._list_frame.grid_columnconfigure(0, weight=1)

        # Footer con contador
        self._footer = ctk.CTkLabel(
            self,
            text="",
            font=FONT_SMALL,
            text_color="gray",
        )
        self._footer.grid(row=2, column=0, padx=12, pady=(0, 8), sticky="w")

    def _refresh(self):
        """Reconstruye la lista de notificaciones."""
        # Limpiar filas existentes
        for row in self._rows:
            row.destroy()
        self._rows.clear()

        notifications = self._notif_mgr.get_all()

        if not notifications:
            empty = ctk.CTkLabel(
                self._list_frame,
                text="No hay notificaciones",
                font=FONT_NORMAL,
                text_color="gray",
            )
            empty.grid(row=0, column=0, pady=30)
            self._rows.append(empty)
            self._footer.configure(text="Sin notificaciones")
            return

        for i, notif in enumerate(notifications):
            self._add_notif_row(i, notif)

        unread = self._notif_mgr.get_unread_count()
        self._footer.configure(
            text=f"{len(notifications)} total · {unread} sin leer"
        )

    def _add_notif_row(self, index: int, notif):
        border_color, bg_color = NOTIF_COLORS[notif.tipo]
        alpha = 1.0 if not notif.read else 0.6

        row = ctk.CTkFrame(
            self._list_frame,
            corner_radius=8,
            border_width=1,
            border_color=border_color,
            fg_color=bg_color,
        )
        row.grid(row=index, column=0, sticky="ew", pady=3, padx=2)
        row.grid_columnconfigure(0, weight=1)

        # Icono + título + timestamp
        header = ctk.CTkFrame(row, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=10, pady=(8, 2))
        header.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            header,
            text=NOTIF_ICONS[notif.tipo],
            font=("Roboto", 14),
        ).grid(row=0, column=0, padx=(0, 6))

        title_color = "white" if not notif.read else ("gray70", "gray50")
        ctk.CTkLabel(
            header,
            text=notif.title,
            font=("Roboto", 12, "bold" if not notif.read else "normal"),
            text_color=title_color,
        ).grid(row=0, column=1, sticky="w")

        ts_str = notif.timestamp.strftime("%H:%M")
        ctk.CTkLabel(
            header,
            text=ts_str,
            font=FONT_SMALL,
            text_color=("gray60", "gray40"),
        ).grid(row=0, column=2)

        # Mensaje
        msg_color = ("gray90", "gray80") if not notif.read else ("gray60", "gray40")
        ctk.CTkLabel(
            row,
            text=notif.message,
            font=FONT_SMALL,
            text_color=msg_color,
            wraplength=320,
            justify="left",
        ).grid(row=1, column=0, padx=10, pady=(0, 8), sticky="w")

        # Marcar como leído al hacer clic
        row.bind("<Button-1>", lambda e, nid=notif.id: self._mark_read(nid))

        self._rows.append(row)

    def _mark_read(self, notif_id: int):
        self._notif_mgr.mark_read(notif_id)
        self._refresh()

    def _mark_all_read(self):
        self._notif_mgr.mark_all_read()
        self._refresh()

    def _clear_all(self):
        self._notif_mgr.clear_all()
        self._refresh()

    def destroy(self):
        self._notif_mgr.remove_observer(self._refresh)
        super().destroy()
