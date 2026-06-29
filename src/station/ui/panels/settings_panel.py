# ui/panels/settings_panel.py
"""
Panel de ajustes generales de la aplicación.
Incluye: pantalla completa, tema, configuración de notificaciones (sonido, toast).

Uso:
    panel = SettingsPanel(parent, notification_manager=mgr)
"""
from __future__ import annotations

import logging
from typing import Optional

import customtkinter as ctk

from ui.theme import FONT_TITLE, FONT_NORMAL, FONT_SMALL, COLORS

logger = logging.getLogger(__name__)


class SettingsPanel(ctk.CTkFrame):
    def __init__(self,
                 master,
                 notification_manager=None,
                 on_theme_change=None,
                 **kwargs):
        super().__init__(master, **kwargs)

        self._notif_mgr = notification_manager
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

        # === SECCIÓN: INTERFAZ ===
        ctk.CTkLabel(content, text="Interfaz", font=("Roboto", 14, "bold"),
                     text_color=COLORS["accent"]).grid(
            row=row, column=0, sticky="w", pady=(16, 8))
        row += 1

        # Pantalla completa
        self._btn_fullscreen = ctk.CTkButton(
            content,
            text="🖥️  Pantalla completa",
            font=FONT_NORMAL,
            height=40,
            command=self._toggle_fullscreen,
        )
        self._btn_fullscreen.grid(row=row, column=0, sticky="ew", pady=4)
        row += 1

        # Tema
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

        # Separador
        ctk.CTkFrame(content, height=1, fg_color=COLORS["border"]).grid(
            row=row, column=0, sticky="ew", pady=12)
        row += 1

        # === SECCIÓN: NOTIFICACIONES ===
        ctk.CTkLabel(content, text="Notificaciones", font=("Roboto", 14, "bold"),
                     text_color=COLORS["accent"]).grid(
            row=row, column=0, sticky="w", pady=(8, 8))
        row += 1

        if self._notif_mgr:
            # Sonido habilitado
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

            # Volumen
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

            # Toast habilitado
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

            # Botón probar sonido
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

        # Separador
        ctk.CTkFrame(content, height=1, fg_color=COLORS["border"]).grid(
            row=row, column=0, sticky="ew", pady=12)
        row += 1

        # === SECCIÓN: DATOS ===
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

        # Info de versión
        ctk.CTkLabel(content, text="Farm of Things v1.0",
                     font=FONT_SMALL, text_color="gray").grid(
            row=row, column=0, pady=(24, 8))

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def _toggle_fullscreen(self):
        """Alterna modo pantalla completa en la ventana principal."""
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
