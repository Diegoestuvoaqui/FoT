# ui/dialogs/login_dialog.py
import logging

import customtkinter as ctk

from ui.theme import FONT_NORMAL, FONT_SMALL, COLORS

logger = logging.getLogger(__name__)


class LoginDialog(ctk.CTkToplevel):
    """
    Diálogo modal de login.
    Retorna User a través de on_login callback, o None si se cierra.
    """

    def __init__(self, parent, auth_controller, on_login=None, on_register=None):
        """
        auth_controller: AuthController
        on_login: callback(user: User) llamado al autenticar exitosamente
        on_register: callback() llamado al hacer clic en "Crear cuenta"
        """
        super().__init__(parent)
        self.title("FoT — Iniciar sesión")
        self.geometry("800x600")
        self.resizable(False, False)

        self._auth_ctrl = auth_controller
        self._on_login = on_login
        self._on_register = on_register
        self.result = None  # User o None

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

        # Logo / título
        title_frame = ctk.CTkFrame(self, fg_color="transparent")
        title_frame.grid(row=0, column=0, pady=(30, 10), padx=30, sticky="ew")

        ctk.CTkLabel(
            title_frame,
            text="FoT",
            font=("Roboto", 32, "bold"),
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
            form, font=FONT_NORMAL, height=40, show="●", placeholder_text="Contraseña")
        self._entry_pass.grid(row=3, column=0, sticky="ew", pady=(0, 4))

        # Mostrar/ocultar contraseña
        self._show_pass = ctk.CTkCheckBox(
            form, text="Mostrar contraseña", font=FONT_SMALL,
            command=self._toggle_password)
        self._show_pass.grid(row=4, column=0, sticky="w", pady=(4, 12))

        # Error
        self._lbl_error = ctk.CTkLabel(
            form, text="", font=FONT_SMALL, text_color=COLORS["fault"])
        self._lbl_error.grid(row=5, column=0, sticky="w", pady=(0, 8))

        # Botón login
        self._btn_login = ctk.CTkButton(
            form, text="Iniciar sesión", font=FONT_NORMAL, height=40,
            command=self._do_login)
        self._btn_login.grid(row=6, column=0, sticky="ew", pady=(0, 12))

        # Botón registro (solo si no hay usuarios o es admin)
        self._btn_register = ctk.CTkButton(
            form, text="Crear cuenta", font=FONT_SMALL, height=32,
            fg_color="transparent", hover_color=("gray80", "#2e2e2e"),
            command=self._go_register)
        self._btn_register.grid(row=7, column=0, sticky="ew")

        # Bind Enter
        self._entry_pass.bind("<Return>", lambda e: self._do_login())
        self._entry_user.bind("<Return>", lambda e: self._entry_pass.focus())

        # Botón registro (solo si se permite)
        if self._on_register is not None:
            self._btn_register = ctk.CTkButton(
                form, text="Crear cuenta", font=FONT_SMALL, height=32,
                fg_color="transparent", hover_color=("gray80", "#2e2e2e"),
                command=self._go_register)
            self._btn_register.grid(row=7, column=0, sticky="ew")

    # ------------------------------------------------------------------
    # Acciones
    # ------------------------------------------------------------------
    def _do_login(self):
        username = self._entry_user.get().strip()
        password = self._entry_pass.get()

        ok, result = self._auth_ctrl.login(username, password)
        if ok:
            self.result = result  # User
            if self._on_login:
                self._on_login(result)
            self.destroy()
        else:
            self._lbl_error.configure(text=result)  # mensaje de error
            self._entry_pass.delete(0, "end")

    def _go_register(self):
        if self._on_register:
            self._on_register()
        self.destroy()

    def _toggle_password(self):
        if self._show_pass.get():
            self._entry_pass.configure(show="")
        else:
            self._entry_pass.configure(show="●")

    def _on_close(self):
        self.result = None
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
