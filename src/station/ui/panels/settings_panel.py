# ui/panels/settings_panel.py
"""
Panel de ajustes generales de la aplicación.
Incluye: cuenta (cambiar contraseña, logout), pantalla completa, tema, notificaciones.

Uso:
    panel = SettingsPanel(parent, notification_manager=mgr, auth_controller=auth_ctrl, user=user)
"""
from __future__ import annotations

import logging
from typing import Optional

import customtkinter as ctk

from ui.dialogs.confirm_dialog import ConfirmDialog  # ← NUEVO: diálogo custom
from ui.theme import FONT_TITLE, FONT_NORMAL, FONT_SMALL, COLORS

logger = logging.getLogger(__name__)


class SettingsPanel(ctk.CTkFrame):
    def __init__(self,
                 master,
                 notification_manager=None,
                 auth_controller=None,
                 user=None,
                 on_logout=None,
                 on_theme_change=None,
                 **kwargs):
        super().__init__(master, **kwargs)

        self._notif_mgr = notification_manager
        self._auth_ctrl = auth_controller
        self._user = user
        self._on_logout = on_logout
        self._on_theme_change = on_theme_change
        self._is_fullscreen = False

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_header()
        self._build_content()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 8))

        ctk.CTkLabel(
            header,
            text="Ajustes",
            font=FONT_TITLE,
        ).pack(side="left")

    def _build_content(self):
        content = ctk.CTkScrollableFrame(self, label_text="")
        content.grid(row=1, column=0, sticky="nsew", padx=16, pady=8)
        content.grid_columnconfigure(0, weight=1)

        row = 0

        # ============================================================
        # === SECCIÓN: CUENTA DE USUARIO ===
        # ============================================================
        ctk.CTkLabel(content, text="Cuenta de usuario", font=("Roboto", 14, "bold"),
                     text_color=COLORS["accent"]).grid(
            row=row, column=0, sticky="w", pady=(16, 8))
        row += 1

        if self._user:
            user_info = f"Usuario: {self._user.username}  |  Rol: {self._user.role.upper()}"
            ctk.CTkLabel(content, text=user_info, font=FONT_NORMAL,
                         text_color=("gray40", "gray60")).grid(
                row=row, column=0, sticky="w", pady=(0, 12))
            row += 1

        # --- Cambiar contraseña ---
        pass_frame = ctk.CTkFrame(content, fg_color="transparent")
        pass_frame.grid(row=row, column=0, sticky="ew", pady=8)
        pass_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(pass_frame, text="Cambiar contraseña", font=("Roboto", 12, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))

        ctk.CTkLabel(pass_frame, text="Actual:", font=FONT_SMALL).grid(
            row=1, column=0, sticky="w", padx=(0, 8), pady=2)
        self._entry_old_pass = ctk.CTkEntry(
            pass_frame, font=FONT_NORMAL, show="●", placeholder_text="Contraseña actual")
        self._entry_old_pass.grid(row=1, column=1, sticky="ew", pady=2)

        ctk.CTkLabel(pass_frame, text="Nueva:", font=FONT_SMALL).grid(
            row=2, column=0, sticky="w", padx=(0, 8), pady=2)
        self._entry_new_pass = ctk.CTkEntry(
            pass_frame, font=FONT_NORMAL, show="●", placeholder_text="Mínimo 4 caracteres")
        self._entry_new_pass.grid(row=2, column=1, sticky="ew", pady=2)

        ctk.CTkLabel(pass_frame, text="Confirmar:", font=FONT_SMALL).grid(
            row=3, column=0, sticky="w", padx=(0, 8), pady=2)
        self._entry_confirm_pass = ctk.CTkEntry(
            pass_frame, font=FONT_NORMAL, show="●", placeholder_text="Repite la nueva")
        self._entry_confirm_pass.grid(row=3, column=1, sticky="ew", pady=2)

        self._show_pass = ctk.CTkCheckBox(
            pass_frame, text="Mostrar contraseñas", font=FONT_SMALL,
            command=self._toggle_password_visibility)
        self._show_pass.grid(row=4, column=1, sticky="w", pady=(4, 8))

        self._lbl_pass_error = ctk.CTkLabel(
            pass_frame, text="", font=FONT_SMALL, text_color=COLORS["fault"])
        self._lbl_pass_error.grid(row=5, column=0, columnspan=2, sticky="w", pady=(0, 4))

        ctk.CTkButton(
            pass_frame,
            text="Cambiar contraseña",
            font=FONT_NORMAL,
            height=36,
            command=self._on_change_password,
        ).grid(row=6, column=0, columnspan=2, sticky="w", pady=(0, 8))

        row += 1

        ctk.CTkFrame(content, height=1, fg_color=COLORS["border"]).grid(
            row=row, column=0, sticky="ew", pady=12)
        row += 1

        ctk.CTkButton(
            content,
            text="🚪  Cerrar sesión",
            font=FONT_NORMAL,
            height=44,
            fg_color="#EF4444",
            hover_color="#B91C1C",
            command=self._on_logout_clicked,
        ).grid(row=row, column=0, sticky="ew", pady=(8, 16))
        row += 1

        ctk.CTkFrame(content, height=1, fg_color=COLORS["border"]).grid(
            row=row, column=0, sticky="ew", pady=12)
        row += 1

        # ============================================================
        # === SECCIÓN: INTERFAZ ===
        # ============================================================
        ctk.CTkLabel(content, text="Interfaz", font=("Roboto", 14, "bold"),
                     text_color=COLORS["accent"]).grid(
            row=row, column=0, sticky="w", pady=(8, 8))
        row += 1

        self._btn_fullscreen = ctk.CTkButton(
            content,
            text="🖥️  Pantalla completa",
            font=FONT_NORMAL,
            height=40,
            command=self._toggle_fullscreen,
        )
        self._btn_fullscreen.grid(row=row, column=0, sticky="ew", pady=4)
        row += 1

        theme_frame = ctk.CTkFrame(content, fg_color="transparent")
        theme_frame.grid(row=row, column=0, sticky="ew", pady=8)
        theme_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(theme_frame, text="Tema:", font=FONT_NORMAL).grid(
            row=0, column=0, padx=(0, 12), sticky="w")

        self._theme_var = ctk.StringVar(value="dark")
        self._theme_combo = ctk.CTkComboBox(
            theme_frame,
            values=["Claro", "Oscuro", "Sistema"],
            font=FONT_NORMAL,
            state="readonly",
            command=self._on_theme_selected,
        )
        self._theme_combo.set("Oscuro")
        self._theme_combo.grid(row=0, column=1, sticky="ew")
        row += 1

        ctk.CTkFrame(content, height=1, fg_color=COLORS["border"]).grid(
            row=row, column=0, sticky="ew", pady=12)
        row += 1

        # ============================================================
        # === SECCIÓN: NOTIFICACIONES ===
        # ============================================================
        ctk.CTkLabel(content, text="Notificaciones", font=("Roboto", 14, "bold"),
                     text_color=COLORS["accent"]).grid(
            row=row, column=0, sticky="w", pady=(8, 8))
        row += 1

        if self._notif_mgr:
            self._sound_switch = ctk.CTkSwitch(
                content,
                text="Sonido de notificaciones",
                font=FONT_NORMAL,
                command=self._on_sound_toggle,
            )
            self._sound_switch.grid(row=row, column=0, sticky="w", pady=6)
            if self._notif_mgr.is_sound_enabled():
                self._sound_switch.select()
            row += 1

            vol_frame = ctk.CTkFrame(content, fg_color="transparent")
            vol_frame.grid(row=row, column=0, sticky="ew", pady=6)
            vol_frame.grid_columnconfigure(1, weight=1)

            ctk.CTkLabel(vol_frame, text="Volumen:", font=FONT_NORMAL).grid(
                row=0, column=0, padx=(0, 12), sticky="w")

            self._volume_slider = ctk.CTkSlider(
                vol_frame,
                from_=0,
                to=1,
                number_of_steps=10,
                command=self._on_volume_change,
            )
            self._volume_slider.set(self._notif_mgr.get_volume())
            self._volume_slider.grid(row=0, column=1, sticky="ew")

            self._lbl_volume = ctk.CTkLabel(
                vol_frame,
                text=f"{int(self._notif_mgr.get_volume() * 100)}%",
                font=FONT_SMALL,
                width=40,
            )
            self._lbl_volume.grid(row=0, column=2, padx=(8, 0))
            row += 1

            self._toast_switch = ctk.CTkSwitch(
                content,
                text="Mostrar notificaciones emergentes (toast)",
                font=FONT_NORMAL,
                command=self._on_toast_toggle,
            )
            self._toast_switch.grid(row=row, column=0, sticky="w", pady=6)
            if self._notif_mgr.is_toast_enabled():
                self._toast_switch.select()
            row += 1

            ctk.CTkButton(
                content,
                text="🔊  Probar sonido",
                font=FONT_SMALL,
                command=self._test_sound,
                fg_color="transparent",
                border_width=1,
                border_color=COLORS["border"],
            ).grid(row=row, column=0, sticky="w", pady=8)
            row += 1
        else:
            ctk.CTkLabel(content, text="Sistema de notificaciones no disponible",
                         font=FONT_SMALL, text_color="gray").grid(
                row=row, column=0, sticky="w", pady=8)
            row += 1

        ctk.CTkFrame(content, height=1, fg_color=COLORS["border"]).grid(
            row=row, column=0, sticky="ew", pady=12)
        row += 1

        # ============================================================
        # === SECCIÓN: DATOS ===
        # ============================================================
        ctk.CTkLabel(content, text="Datos", font=("Roboto", 14, "bold"),
                     text_color=COLORS["accent"]).grid(
            row=row, column=0, sticky="w", pady=(8, 8))
        row += 1

        ctk.CTkButton(
            content,
            text="🗑️  Limpiar historial de notificaciones",
            font=FONT_NORMAL,
            height=36,
            fg_color="#EF4444",
            hover_color="#B91C1C",
            command=self._clear_notifications,
        ).grid(row=row, column=0, sticky="ew", pady=4)
        row += 1

        ctk.CTkLabel(content, text="Farm of Things v1.0",
                     font=FONT_SMALL, text_color="gray").grid(
            row=row, column=0, pady=(24, 8))

    # ------------------------------------------------------------------
    # Validaciones
    # ------------------------------------------------------------------
    def _validate_password(self, password: str) -> tuple[bool, str]:
        if not password:
            return False, "La contraseña es obligatoria"
        if " " in password:
            return False, "La contraseña no puede contener espacios"
        if len(password) < 4:
            return False, "La contraseña debe tener al menos 4 caracteres"
        return True, ""

    # ------------------------------------------------------------------
    # Callbacks de Cuenta
    # ------------------------------------------------------------------

    def _toggle_password_visibility(self):
        show = "" if self._show_pass.get() else "●"
        self._entry_old_pass.configure(show=show)
        self._entry_new_pass.configure(show=show)
        self._entry_confirm_pass.configure(show=show)

    def _on_change_password(self):
        old = self._entry_old_pass.get()
        new = self._entry_new_pass.get()
        confirm = self._entry_confirm_pass.get()

        if not old or not new:
            self._lbl_pass_error.configure(text="Todos los campos son obligatorios")
            return

        ok, msg = self._validate_password(new)
        if not ok:
            self._lbl_pass_error.configure(text=msg)
            return

        if new != confirm:
            self._lbl_pass_error.configure(text="Las contraseñas nuevas no coinciden")
            return

        if not self._auth_ctrl or not self._user:
            self._lbl_pass_error.configure(text="Error: no hay sesión activa")
            return

        ok, msg = self._auth_ctrl.change_password(self._user, old, new)
        if ok:
            self._lbl_pass_error.configure(text="✅ Contraseña cambiada exitosamente", text_color=COLORS["accent"])
            self._entry_old_pass.delete(0, "end")
            self._entry_new_pass.delete(0, "end")
            self._entry_confirm_pass.delete(0, "end")
            self.after(3000, lambda: self._lbl_pass_error.configure(
                text="", text_color=COLORS["fault"]))
            logger.info("Contraseña cambiada para usuario: %s", self._user.username)
        else:
            self._lbl_pass_error.configure(text=msg, text_color=COLORS["fault"])

    def _on_logout_clicked(self):
        # ← CORREGIDO: usar ConfirmDialog custom en vez de messagebox nativo
        def _handle_result(confirmed: bool):
            if confirmed and self._on_logout:
                self._on_logout()

        ConfirmDialog(
            self.winfo_toplevel(),
            title="Cerrar sesión",
            message=f"¿Estás seguro de que querés cerrar la sesión de {self._user.username if self._user else 'usuario'}?",
            on_result=_handle_result,
        )

    # ------------------------------------------------------------------
    # Callbacks de Interfaz
    # ------------------------------------------------------------------

    def _toggle_fullscreen(self):
        root = self.winfo_toplevel()
        if not isinstance(root, ctk.CTk):
            return

        self._is_fullscreen = not self._is_fullscreen
        root.attributes("-fullscreen", self._is_fullscreen)

        if self._is_fullscreen:
            self._btn_fullscreen.configure(text="🖥️  Salir de pantalla completa")
        else:
            self._btn_fullscreen.configure(text="🖥️  Pantalla completa")

        logger.info("Pantalla completa: %s", self._is_fullscreen)

    def _on_theme_selected(self, value: str):
        theme_map = {
            "Claro": "light",
            "Oscuro": "dark",
            "Sistema": "system",
        }
        theme = theme_map.get(value, "dark")
        ctk.set_appearance_mode(theme)
        if self._on_theme_change:
            self._on_theme_change(theme)
        logger.info("Tema cambiado a: %s", theme)

    # ------------------------------------------------------------------
    # Callbacks de Notificaciones
    # ------------------------------------------------------------------

    def _on_sound_toggle(self):
        if self._notif_mgr:
            enabled = bool(self._sound_switch.get())
            self._notif_mgr.set_sound_enabled(enabled)
            logger.info("Sonido de notificaciones: %s", enabled)

    def _on_volume_change(self, value: float):
        if self._notif_mgr:
            self._notif_mgr.set_volume(value)
            self._lbl_volume.configure(text=f"{int(value * 100)}%")

    def _on_toast_toggle(self):
        if self._notif_mgr:
            enabled = bool(self._toast_switch.get())
            self._notif_mgr.set_toast_enabled(enabled)
            logger.info("Toast notifications: %s", enabled)

    def _test_sound(self):
        if self._notif_mgr:
            self._notif_mgr.notify(
                "Prueba de sonido",
                "Si escuchaste un sonido, las notificaciones están funcionando.",
                tipo="info"
            )

    def _clear_notifications(self):
        if self._notif_mgr:
            self._notif_mgr.clear_all()
            logger.info("Historial de notificaciones limpiado")