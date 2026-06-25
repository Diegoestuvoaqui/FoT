# ui/panels/admin_panel.py
import logging
from tkinter.messagebox import askyesno

import customtkinter as ctk

from ui.theme import FONT_TITLE, FONT_NORMAL, FONT_SMALL, COLORS

logger = logging.getLogger(__name__)


class AdminPanel(ctk.CTkFrame):
    """
    Panel de administración de usuarios.
    Solo visible para usuarios con rol 'admin'.
    """

    def __init__(self,
                 master,
                 auth_controller,
                 on_register_user=None,  # callback para abrir RegisterDialog
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
        # Contenedor scrollable
        self._list_frame = ctk.CTkScrollableFrame(self, label_text="")
        self._list_frame.grid(row=1, column=0, sticky="nsew", padx=16, pady=8)
        self._list_frame.grid_columnconfigure(0, weight=1)

        self._user_rows: list[ctk.CTkFrame] = []

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------
    def refresh_users(self, users: list[dict], current_user_id: int):
        """
        Poblar la lista de usuarios.
        users: lista de dicts con id, username, role, created_at
        current_user_id: ID del usuario logueado (no puede eliminarse)
        """
        # Limpiar lista anterior
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
        row = ctk.CTkFrame(self._list_frame, corner_radius=8, border_width=1,
                           border_color=COLORS["border"])
        row.grid(row=index, column=0, sticky="ew", pady=3, padx=2)
        row.grid_columnconfigure(1, weight=1)

        # Indicador de rol
        role_color = COLORS["accent"] if user["role"] == "admin" else ("gray50", "gray70")
        lbl_role = ctk.CTkLabel(
            row,
            text="●",
            font=("Roboto", 12),
            text_color=role_color,
            width=20,
        )
        lbl_role.grid(row=0, column=0, padx=(10, 0), pady=8)

        # Username
        lbl_name = ctk.CTkLabel(
            row,
            text=user["username"],
            font=FONT_NORMAL,
            anchor="w",
        )
        lbl_name.grid(row=0, column=1, sticky="w", padx=8)

        # Rol como texto
        lbl_role_text = ctk.CTkLabel(
            row,
            text=user["role"],
            font=FONT_SMALL,
            text_color=("gray50", "gray70"),
        )
        lbl_role_text.grid(row=0, column=2, padx=8)

        # Fecha de creación
        lbl_date = ctk.CTkLabel(
            row,
            text=user.get("created_at", "")[:10],  # solo YYYY-MM-DD
            font=FONT_SMALL,
            text_color=("gray50", "gray70"),
        )
        lbl_date.grid(row=0, column=3, padx=8)

        # Botón eliminar (deshabilitado si es el usuario actual)
        can_delete = user["id"] != current_user_id
        btn_delete = ctk.CTkButton(
            row,
            text="Eliminar",
            font=FONT_SMALL,
            width=80,
            height=28,
            fg_color="#EF4444" if can_delete else ("gray60", "gray40"),
            hover_color="#B91C1C" if can_delete else ("gray60", "gray40"),
            state="normal" if can_delete else "disabled",
            command=lambda uid=user["id"], uname=user["username"]: self._on_delete_user(uid, uname),
        )
        btn_delete.grid(row=0, column=4, padx=(8, 10), pady=8)

        self._user_rows.append(row)

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------
    def _on_add_user(self):
        if self._on_register_user:
            self._on_register_user()

    def _on_delete_user(self, user_id: int, username: str):
        confirm = askyesno(
            "Confirmar eliminación",
            f"¿Eliminar al usuario '{username}'?\n\n"
            "Esta acción no se puede deshacer. "
            "Las parcelas y datos asociados también se eliminarán."
        )
        if not confirm:
            return

        # Notificar a MainWindow para que ejecute a través del controller
        if hasattr(self, "_on_delete_user_callback"):
            self._on_delete_user_callback(user_id)

    def set_delete_callback(self, callback):
        """MainWindow registra aquí el callback para eliminar usuarios."""
        self._on_delete_user_callback = callback
