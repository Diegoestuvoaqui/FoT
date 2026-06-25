# ui/dialogs/register_dialog.py
import logging

import customtkinter as ctk

from ui.theme import FONT_TITLE, FONT_NORMAL, FONT_SMALL, COLORS

logger = logging.getLogger(__name__)


class RegisterDialog(ctk.CTkToplevel):
    """
    Diálogo modal para registro de nuevos usuarios.
    Retorna éxito/fallo a través de callback.
    """

    def __init__(self, parent, auth_controller, on_success=None,
                 allow_admin_creation: bool = False):
        """
        auth_controller: AuthController
        on_success: callback(username: str) llamado al registrar exitosamente
        allow_admin_creation: True si se permite crear usuarios admin (solo admin logueado)
        """
        super().__init__(parent)
        self.title("FoT — Crear cuenta")
        self.geometry("400x520")
        self.resizable(False, False)

        self._auth_ctrl = auth_controller
        self._on_success = on_success
        self._allow_admin = allow_admin_creation

        self._build()
        self._center_window()

        # Modal
        self.transient(parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._entry_user.focus()
        self.wait_window()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------
    def _build(self):
        self.grid_columnconfigure(0, weight=1)

        # Título
        title_frame = ctk.CTkFrame(self, fg_color="transparent")
        title_frame.grid(row=0, column=0, pady=(30, 10), padx=30, sticky="ew")

        ctk.CTkLabel(
            title_frame,
            text="Crear cuenta",
            font=FONT_TITLE,
            text_color=COLORS["accent"],
        ).pack()

        ctk.CTkLabel(
            title_frame,
            text="Farm of Things",
            font=FONT_NORMAL,
            text_color=("gray50", "gray70"),
        ).pack()

        # Formulario
        form = ctk.CTkFrame(self, fg_color="transparent")
        form.grid(row=1, column=0, pady=20, padx=30, sticky="ew")
        form.grid_columnconfigure(0, weight=1)

        # Usuario
        ctk.CTkLabel(form, text="Usuario", font=FONT_SMALL, anchor="w").grid(
            row=0, column=0, sticky="w", pady=(0, 4))
        self._entry_user = ctk.CTkEntry(
            form, font=FONT_NORMAL, height=40, placeholder_text="Nombre de usuario")
        self._entry_user.grid(row=1, column=0, sticky="ew", pady=(0, 12))

        # Contraseña
        ctk.CTkLabel(form, text="Contraseña", font=FONT_SMALL, anchor="w").grid(
            row=2, column=0, sticky="w", pady=(0, 4))
        self._entry_pass = ctk.CTkEntry(
            form, font=FONT_NORMAL, height=40, show="●", placeholder_text="Mínimo 4 caracteres")
        self._entry_pass.grid(row=3, column=0, sticky="ew", pady=(0, 4))

        # Confirmar contraseña
        ctk.CTkLabel(form, text="Confirmar contraseña", font=FONT_SMALL, anchor="w").grid(
            row=4, column=0, sticky="w", pady=(0, 4))
        self._entry_pass2 = ctk.CTkEntry(
            form, font=FONT_NORMAL, height=40, show="●", placeholder_text="Repite la contraseña")
        self._entry_pass2.grid(row=5, column=0, sticky="ew", pady=(0, 4))

        # Mostrar contraseñas
        self._show_pass = ctk.CTkCheckBox(
            form, text="Mostrar contraseñas", font=FONT_SMALL,
            command=self._toggle_password)
        self._show_pass.grid(row=6, column=0, sticky="w", pady=(4, 12))

        # Selector de rol (solo si se permite admin)
        if self._allow_admin:
            ctk.CTkLabel(form, text="Rol", font=FONT_SMALL, anchor="w").grid(
                row=7, column=0, sticky="w", pady=(0, 4))
            self._combo_role = ctk.CTkComboBox(
                form, values=["user", "admin"], font=FONT_NORMAL, state="readonly")
            self._combo_role.set("user")
            self._combo_role.grid(row=8, column=0, sticky="ew", pady=(0, 12))
            self._role_row_offset = 2
        else:
            self._combo_role = None
            self._role_row_offset = 0

        # Error
        self._lbl_error = ctk.CTkLabel(
            form, text="", font=FONT_SMALL, text_color=COLORS["fault"])
        self._lbl_error.grid(row=7 + self._role_row_offset, column=0, sticky="w", pady=(0, 8))

        # Botón registrar
        self._btn_register = ctk.CTkButton(
            form, text="Crear cuenta", font=FONT_NORMAL, height=40,
            command=self._do_register)
        self._btn_register.grid(row=8 + self._role_row_offset, column=0, sticky="ew", pady=(0, 12))

        # Botón cancelar
        self._btn_cancel = ctk.CTkButton(
            form, text="Cancelar", font=FONT_SMALL, height=32,
            fg_color="transparent", hover_color=("gray80", "#2e2e2e"),
            command=self._on_close)
        self._btn_cancel.grid(row=9 + self._role_row_offset, column=0, sticky="ew")

        # Bind Enter
        self._entry_pass2.bind("<Return>", lambda e: self._do_register())
        self._entry_pass.bind("<Return>", lambda e: self._entry_pass2.focus())

    # ------------------------------------------------------------------
    # Acciones
    # ------------------------------------------------------------------
    def _do_register(self):
        username = self._entry_user.get().strip()
        password = self._entry_pass.get()
        password2 = self._entry_pass2.get()

        # Validaciones básicas de UI
        if not username:
            self._lbl_error.configure(text="El usuario es obligatorio")
            return

        if len(password) < 4:
            self._lbl_error.configure(text="La contraseña debe tener al menos 4 caracteres")
            return

        if password != password2:
            self._lbl_error.configure(text="Las contraseñas no coinciden")
            self._entry_pass2.delete(0, "end")
            return

        role = "user"
        if self._combo_role:
            role = self._combo_role.get()

        ok, error = self._auth_ctrl.register(username, password, role)
        if ok:
            if self._on_success:
                self._on_success(username)
            self.destroy()
        else:
            self._lbl_error.configure(text=error)

    def _toggle_password(self):
        show = "" if self._show_pass.get() else "●"
        self._entry_pass.configure(show=show)
        self._entry_pass2.configure(show=show)

    def _on_close(self):
        self.destroy()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _center_window(self):
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
