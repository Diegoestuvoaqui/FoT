# ui/panels/login_panel.py
import logging

import customtkinter as ctk

from ui.theme import FONT_NORMAL, FONT_SMALL, COLORS

logger = logging.getLogger(__name__)


class LoginPanel(ctk.CTkFrame):
    """
    Panel embebido de autenticación.
    Ofrece Login y Registro en pestañas sin bloquear la ventana principal.
    """

    def __init__(self, master, auth_controller, on_login=None, on_register=None, **kwargs):
        super().__init__(master, **kwargs)
        self._auth_ctrl = auth_controller
        self._on_login = on_login
        self._on_register = on_register

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------
    def _build(self):
        # Contenedor centrado con más espacio
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.grid(row=0, column=0)
        container.grid_columnconfigure(0, weight=1)

        # Logo más grande
        ctk.CTkLabel(
            container,
            text="FoT",
            font=("Roboto", 48, "bold"),
            text_color=COLORS["accent"],
        ).grid(row=0, column=0, pady=(40, 8))

        ctk.CTkLabel(
            container,
            text="Farm of Things",
            font=("Roboto", 18),
            text_color=("gray50", "gray70"),
        ).grid(row=1, column=0, pady=(0, 30))

        # Tabs más anchas y altas
        self._tab = ctk.CTkTabview(container, width=480, height=520)
        self._tab.grid(row=2, column=0)
        self._tab.add("Iniciar sesión")
        self._tab.add("Crear cuenta")

        self._build_login_tab()
        self._build_register_tab()

    def _build_login_tab(self):
        tab = self._tab.tab("Iniciar sesión")
        tab.grid_columnconfigure(0, weight=1)

        # Padding interno mayor
        inner = ctk.CTkFrame(tab, fg_color="transparent")
        inner.grid(row=0, column=0, sticky="nsew", padx=30, pady=20)
        inner.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(inner, text="Usuario", font=FONT_SMALL, anchor="w").grid(
            row=0, column=0, sticky="w", pady=(16, 4))
        self._entry_user = ctk.CTkEntry(
            inner, font=FONT_NORMAL, height=44,
            placeholder_text="Nombre de usuario")
        self._entry_user.grid(row=1, column=0, sticky="ew", pady=(0, 14))

        ctk.CTkLabel(inner, text="Contraseña", font=FONT_SMALL, anchor="w").grid(
            row=2, column=0, sticky="w", pady=(0, 4))
        self._entry_pass = ctk.CTkEntry(
            inner, font=FONT_NORMAL, height=44, show="●",
            placeholder_text="Contraseña")
        self._entry_pass.grid(row=3, column=0, sticky="ew", pady=(0, 6))

        self._show_pass = ctk.CTkCheckBox(
            inner, text="Mostrar contraseña", font=FONT_SMALL,
            command=self._toggle_password)
        self._show_pass.grid(row=4, column=0, sticky="w", pady=(8, 14))

        self._lbl_error = ctk.CTkLabel(
            inner, text="", font=FONT_SMALL, text_color=COLORS["fault"])
        self._lbl_error.grid(row=5, column=0, sticky="w", pady=(0, 12))

        ctk.CTkButton(
            inner, text="Iniciar sesión", font=FONT_NORMAL, height=44,
            command=self._do_login,
        ).grid(row=6, column=0, sticky="ew", pady=(0, 12))

        self._entry_pass.bind("<Return>", lambda e: self._do_login())
        self._entry_user.bind("<Return>", lambda e: self._entry_pass.focus())

    def _build_register_tab(self):
        tab = self._tab.tab("Crear cuenta")
        tab.grid_columnconfigure(0, weight=1)

        inner = ctk.CTkFrame(tab, fg_color="transparent")
        inner.grid(row=0, column=0, sticky="nsew", padx=30, pady=20)
        inner.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(inner, text="Usuario", font=FONT_SMALL, anchor="w").grid(
            row=0, column=0, sticky="w", pady=(16, 4))
        self._reg_user = ctk.CTkEntry(
            inner, font=FONT_NORMAL, height=44,
            placeholder_text="Nombre de usuario")
        self._reg_user.grid(row=1, column=0, sticky="ew", pady=(0, 14))

        ctk.CTkLabel(inner, text="Contraseña", font=FONT_SMALL, anchor="w").grid(
            row=2, column=0, sticky="w", pady=(0, 4))
        self._reg_pass = ctk.CTkEntry(
            inner, font=FONT_NORMAL, height=44, show="●",
            placeholder_text="Mínimo 4 caracteres")
        self._reg_pass.grid(row=3, column=0, sticky="ew", pady=(0, 10))

        ctk.CTkLabel(inner, text="Confirmar contraseña", font=FONT_SMALL, anchor="w").grid(
            row=4, column=0, sticky="w", pady=(0, 4))
        self._reg_pass2 = ctk.CTkEntry(
            inner, font=FONT_NORMAL, height=44, show="●",
            placeholder_text="Repite la contraseña")
        self._reg_pass2.grid(row=5, column=0, sticky="ew", pady=(0, 6))

        self._show_pass_reg = ctk.CTkCheckBox(
            inner, text="Mostrar contraseñas", font=FONT_SMALL,
            command=self._toggle_password_reg)
        self._show_pass_reg.grid(row=6, column=0, sticky="w", pady=(8, 14))

        # Info sobre primer usuario admin
        self._lbl_info_reg = ctk.CTkLabel(
            inner, text="", font=FONT_SMALL, text_color=COLORS["accent"])
        self._lbl_info_reg.grid(row=7, column=0, sticky="w", pady=(0, 8))

        self._lbl_error_reg = ctk.CTkLabel(
            inner, text="", font=FONT_SMALL, text_color=COLORS["fault"])
        self._lbl_error_reg.grid(row=8, column=0, sticky="w", pady=(0, 12))

        ctk.CTkButton(
            inner, text="Crear cuenta", font=FONT_NORMAL, height=44,
            command=self._do_register,
        ).grid(row=9, column=0, sticky="ew", pady=(0, 12))

        self._reg_pass2.bind("<Return>", lambda e: self._do_register())

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------
    def set_first_user_info(self, is_first: bool) -> None:
        """Muestra/oculta info sobre que el primer usuario será admin."""
        if is_first:
            self._lbl_info_reg.configure(
                text="👤 Serás el primer usuario — se creará como ADMINISTRADOR")
        else:
            self._lbl_info_reg.configure(text="")

    # ------------------------------------------------------------------
    # Acciones
    # ------------------------------------------------------------------
    def _do_login(self):
        username = self._entry_user.get().strip()
        password = self._entry_pass.get()

        ok, result = self._auth_ctrl.login(username, password)
        if ok:
            self._lbl_error.configure(text="")
            if self._on_login:
                self._on_login(result)
        else:
            self._lbl_error.configure(text=result)
            self._entry_pass.delete(0, "end")

    def _do_register(self):
        username = self._reg_user.get().strip()
        password = self._reg_pass.get()
        password2 = self._reg_pass2.get()

        if not username:
            self._lbl_error_reg.configure(text="El usuario es obligatorio")
            return
        if len(password) < 4:
            self._lbl_error_reg.configure(
                text="La contraseña debe tener al menos 4 caracteres")
            return
        if password != password2:
            self._lbl_error_reg.configure(text="Las contraseñas no coinciden")
            self._reg_pass2.delete(0, "end")
            return

        # Si no hay usuarios, el primero es admin
        role = "admin" if not self._auth_ctrl._service._db.user_exists() else "user"

        ok, error = self._auth_ctrl.register(username, password, role)
        if ok:
            self._lbl_error_reg.configure(text="")
            if self._on_register:
                self._on_register(username)
            self._tab.set("Iniciar sesión")
            msg = f"Usuario '{username}' creado como {role.upper()}. Inicia sesión."
            self._lbl_error.configure(text=msg, text_color=COLORS["accent"])
        else:
            self._lbl_error_reg.configure(text=error)

    def _toggle_password(self):
        show = "" if self._show_pass.get() else "●"
        self._entry_pass.configure(show=show)

    def _toggle_password_reg(self):
        show = "" if self._show_pass_reg.get() else "●"
        self._reg_pass.configure(show=show)
        self._reg_pass2.configure(show=show)

    def clear(self):
        """Limpia campos y errores."""
        self._entry_user.delete(0, "end")
        self._entry_pass.delete(0, "end")
        self._reg_user.delete(0, "end")
        self._reg_pass.delete(0, "end")
        self._reg_pass2.delete(0, "end")
        self._lbl_error.configure(text="")
        self._lbl_error_reg.configure(text="")
        self._lbl_info_reg.configure(text="")
        self._tab.set("Iniciar sesión")
