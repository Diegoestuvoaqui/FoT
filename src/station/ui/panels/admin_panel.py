# ui/panels/admin_panel.py
import logging
from tkinter.messagebox import askyesno

import customtkinter as ctk

from ui.dialogs.confirm_dialog import ConfirmDialog
from ui.theme import FONT_TITLE, FONT_NORMAL, FONT_SMALL, COLORS

logger = logging.getLogger(__name__)


class AdminPanel(ctk.CTkFrame):
    def __init__(self,
                 master,
                 auth_controller,
                 on_register_user=None,
                 **kwargs):
        super().__init__(master, **kwargs)

        self._auth_ctrl = auth_controller
        self._on_register_user = on_register_user

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_header()
        self._build_user_list()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------
    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 8))
        header.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            header,
            text="Gestión de usuarios",
            font=FONT_TITLE,
        ).grid(row=0, column=0, sticky="w")

        self._btn_add = ctk.CTkButton(
            header,
            text="+ Nuevo usuario",
            font=FONT_SMALL,
            command=self._on_add_user,
        )
        self._btn_add.grid(row=0, column=1, sticky="e")

    def _build_user_list(self):
        self._list_frame = ctk.CTkScrollableFrame(self, label_text="")
        self._list_frame.grid(row=1, column=0, sticky="nsew", padx=16, pady=8)
        self._list_frame.grid_columnconfigure(0, weight=1)

        self._user_rows: list[ctk.CTkFrame] = []

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------
    def refresh_users(self, users: list[dict], current_user_id: int):
        for row in self._user_rows:
            row.destroy()
        self._user_rows.clear()

        if not users:
            ctk.CTkLabel(
                self._list_frame,
                text="No hay usuarios registrados",
                font=FONT_NORMAL,
                text_color=("gray50", "gray70"),
            ).grid(row=0, column=0, pady=20)
            return

        for i, user in enumerate(users):
            self._add_user_row(i, user, current_user_id)

    # ------------------------------------------------------------------
    # Filas de usuario
    # ------------------------------------------------------------------
    def _add_user_row(self, index: int, user: dict, current_user_id: int):
        is_active = bool(user.get("is_active", 1))
        is_self = user["id"] == current_user_id
        can_manage = not is_self

        row = ctk.CTkFrame(self._list_frame, corner_radius=8, border_width=1,
                           border_color=COLORS["border"],
                           fg_color=("gray85", "#1e1e1e") if is_active else ("gray75", "#2a1a1a"))
        row.grid(row=index, column=0, sticky="ew", pady=3, padx=2)
        row.grid_columnconfigure(1, weight=1)

        # Indicador de rol + estado
        role_color = COLORS["accent"] if user["role"] == "admin" else ("gray50", "gray70")
        if not is_active:
            role_color = ("gray60", "gray50")

        lbl_role = ctk.CTkLabel(
            row,
            text="●",
            font=("Roboto", 12),
            text_color=role_color,
            width=20,
        )
        lbl_role.grid(row=0, column=0, padx=(10, 0), pady=8)

        # Username
        username_text = user["username"]
        if not is_active:
            username_text += " (inactivo)"
        lbl_name = ctk.CTkLabel(
            row,
            text=username_text,
            font=FONT_NORMAL if is_active else ("Roboto", 13, "overstrike"),
            anchor="w",
        )
        lbl_name.grid(row=0, column=1, sticky="w", padx=8)

        # Rol
        lbl_role_text = ctk.CTkLabel(
            row,
            text=user["role"],
            font=FONT_SMALL,
            text_color=("gray50", "gray70"),
        )
        lbl_role_text.grid(row=0, column=2, padx=8)

        # Fecha
        lbl_date = ctk.CTkLabel(
            row,
            text=user.get("created_at", "")[:10],
            font=FONT_SMALL,
            text_color=("gray50", "gray70"),
        )
        lbl_date.grid(row=0, column=3, padx=8)

        # Toggle activo/inactivo
        switch_active = ctk.CTkSwitch(
            row,
            text="",
            width=36,
            onvalue=1,
            offvalue=0,
            state="normal" if can_manage else "disabled",
        )
        switch_active.grid(row=0, column=4, padx=4)
        if is_active:
            switch_active.select()

        # FIX: El command no recibe parámetros, leemos del widget
        switch_active.configure(
            command=lambda sw=switch_active, uid=user["id"]:
            self._on_toggle_active(uid, bool(sw.get()))
        )

        # Botón reset password
        btn_reset = ctk.CTkButton(
            row,
            text="🔑 Reset",
            font=FONT_SMALL,
            width=70,
            height=28,
            state="normal" if can_manage else "disabled",
            command=lambda uid=user["id"], uname=user["username"]:
            self._on_reset_password(uid, uname),
        )
        btn_reset.grid(row=0, column=5, padx=4)

        # Botón eliminar
        btn_delete = ctk.CTkButton(
            row,
            text="🗑️",
            font=FONT_SMALL,
            width=40,
            height=28,
            fg_color="#EF4444" if can_manage else ("gray60", "gray40"),
            hover_color="#B91C1C" if can_manage else ("gray60", "gray40"),
            state="normal" if can_manage else "disabled",
            command=lambda uid=user["id"], uname=user["username"]:
            self._on_delete_user(uid, uname),
        )
        btn_delete.grid(row=0, column=6, padx=(4, 10), pady=8)

        self._user_rows.append(row)

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------
    def _on_add_user(self):
        if self._on_register_user:
            self._on_register_user()

    def _on_toggle_active(self, user_id: int, active: bool):
        if hasattr(self, "_on_toggle_active_callback"):
            self._on_toggle_active_callback(user_id, active)

    def _on_reset_password(self, user_id: int, username: str):
        if hasattr(self, "_on_reset_password_callback"):
            self._on_reset_password_callback(user_id, username)

    def _on_delete_user(self, user_id: int, username: str):
        def _handle_result(confirmed: bool):
            if confirmed and hasattr(self, "_on_delete_user_callback"):
                self._on_delete_user_callback(user_id)

        ConfirmDialog(
            self.winfo_toplevel(),
            title="Confirmar eliminación",
            message=f"¿Eliminar permanentemente al usuario '{username}'?\n\n"
                    "Esta acción no se puede deshacer.",
            on_result=_handle_result,
        )
    # ------------------------------------------------------------------
    # Registro de callbacks desde MainWindow
    # ------------------------------------------------------------------
    def set_delete_callback(self, callback):
        self._on_delete_user_callback = callback

    def set_toggle_active_callback(self, callback):
        self._on_toggle_active_callback = callback

    def set_reset_password_callback(self, callback):
        self._on_reset_password_callback = callback