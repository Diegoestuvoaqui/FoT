# ui/panels/audit_panel.py
"""Panel de auditoría (solo admin)."""
from __future__ import annotations

from datetime import datetime, timezone

import customtkinter as ctk

from service.audit_service import AuditService
from ui.theme import FONT_TITLE, FONT_NORMAL, FONT_SMALL, COLORS


class AuditPanel(ctk.CTkFrame):
    def __init__(self, master, audit_service: AuditService,
                 current_user, auth_controller=None, **kwargs):
        super().__init__(master, **kwargs)
        self._audit = audit_service
        self._user = current_user
        self._auth = auth_controller

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._rows: list[ctk.CTkFrame] = []
        self._build()
        self.refresh()

    def _build(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 8))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(header, text="Registro de auditoría",
                     font=FONT_TITLE).grid(row=0, column=0, sticky="w")

        filters = ctk.CTkFrame(self, fg_color="transparent")
        filters.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 8))
        filters.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(filters, text="Usuario:",
                     font=FONT_SMALL).grid(row=0, column=0, padx=(0, 8))
        self._combo_user = ctk.CTkComboBox(
            filters, values=["Todos"], font=FONT_NORMAL,
            command=lambda _v: self.refresh(),
        )
        self._combo_user.set("Todos")
        self._combo_user.grid(row=0, column=1, sticky="ew", padx=4)

        ctk.CTkLabel(filters, text="Límite:",
                     font=FONT_SMALL).grid(row=0, column=2, padx=(16, 8))
        self._combo_limit = ctk.CTkComboBox(
            filters, values=["50", "100", "250", "500"],
            font=FONT_NORMAL, width=90,
            command=lambda _v: self.refresh(),
        )
        self._combo_limit.set("100")
        self._combo_limit.grid(row=0, column=3, padx=4)

        ctk.CTkButton(filters, text="🔄 Refrescar", font=FONT_SMALL,
                      command=self.refresh).grid(row=0, column=4, padx=4)

        self._list = ctk.CTkScrollableFrame(self, label_text="")
        self._list.grid(row=2, column=0, sticky="nsew", padx=16, pady=(0, 16))
        self._list.grid_columnconfigure(0, weight=1)

    def refresh(self):
        for r in self._rows:
            r.destroy()
        self._rows.clear()

        limit = int(self._combo_limit.get() or "100")
        usuario_id = None
        # (puedes añadir filtro de usuario si quieres; por ahora solo self)

        rows = self._audit.list_events(self._user, limit=limit,
                                       usuario_id=usuario_id)
        if not rows:
            ctk.CTkLabel(self._list, text="Sin acciones registradas",
                         font=FONT_NORMAL,
                         text_color=("gray50", "gray70")).grid(
                row=0, column=0, pady=20)
            return

        for i, e in enumerate(rows):
            self._add_row(i, e)

    def _add_row(self, idx: int, e: dict):
        row = ctk.CTkFrame(self._list, corner_radius=6, border_width=1,
                           border_color=COLORS["border"])
        row.grid(row=idx, column=0, sticky="ew", pady=2, padx=2)
        row.grid_columnconfigure(3, weight=1)

        ts = e.get("ts_utc") or 0
        when = datetime.fromtimestamp(ts, tz=timezone.utc).strftime(
            "%Y-%m-%d %H:%M:%S") if ts else "—"
        ctk.CTkLabel(row, text=when, font=FONT_SMALL, width=150,
                     anchor="w").grid(row=0, column=0, padx=8, pady=6)

        user = e.get("username") or "—"
        ctk.CTkLabel(row, text=user, font=FONT_SMALL, width=110,
                     anchor="w").grid(row=0, column=1, padx=8)

        accion = e.get("accion") or "—"
        color = (COLORS["accent"] if e.get("resultado") == "ok"
                 else COLORS["fault"])
        ctk.CTkLabel(row, text=accion, font=FONT_SMALL, width=180,
                     text_color=color, anchor="w").grid(
            row=0, column=2, padx=8)

        objetivo = e.get("objetivo") or ""
        ctk.CTkLabel(row, text=objetivo, font=FONT_SMALL,
                     anchor="w").grid(row=0, column=3, padx=8, sticky="ew")

        self._rows.append(row)