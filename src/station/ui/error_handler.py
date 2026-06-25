"""
ui/error_handler.py
Sistema centralizado de errores con mensajes en español.
Reemplaza los messagebox.showerror dispersos por llamadas a ErrorHandler.show().

Uso:
    from ui.error_handler import ErrorCode, ErrorHandler

    error_handler = ErrorHandler()
    error_handler.show(ErrorCode.ERR_MODE_CHANGE, parent, parcela_id=parcela_id)
"""
from __future__ import annotations

import tkinter as tk
from enum import Enum
from tkinter import messagebox  # solo como fallback si no hay parent CTk

import customtkinter as ctk

from ui.theme import FONT_NORMAL, FONT_SMALL


# ---------------------------------------------------------------------------
# Códigos de error
# ---------------------------------------------------------------------------
class ErrorCode(Enum):
    ERR_MODE_CHANGE = "ERR_MODE_CHANGE"
    ERR_IRRIGATE = "ERR_IRRIGATE"
    ERR_THRESHOLDS = "ERR_THRESHOLDS"
    ERR_ADD_PARCELA = "ERR_ADD_PARCELA"
    ERR_DUPLICATE_PARCELA = "ERR_DUPLICATE_PARCELA"
    ERR_MODIFY_PARCELA = "ERR_MODIFY_PARCELA"
    ERR_DELETE_PARCELA = "ERR_DELETE_PARCELA"
    ERR_SNAPSHOT = "ERR_SNAPSHOT"
    ERR_SENSOR_READ = "ERR_SENSOR_READ"
    ERR_MQTT_CONN = "ERR_MQTT_CONN"
    ERR_USB_CONN = "ERR_USB_CONN"
    ERR_FIRMWARE_INCOMPAT = "ERR_FIRMWARE_INCOMPAT"
    ERR_FIRMWARE_UPLOAD = "ERR_FIRMWARE_UPLOAD"
    ERR_VAR_READ = "ERR_VAR_READ"
    ERR_DB_WRITE = "ERR_DB_WRITE"
    ERR_ID_GENERATION = "ERR_ID_GENERATION"


# ---------------------------------------------------------------------------
# Mensajes en español (pueden contener placeholders para .format())
# ---------------------------------------------------------------------------
MESSAGES: dict[ErrorCode, str] = {
    ErrorCode.ERR_MODE_CHANGE: (
        "No se pudo cambiar el modo de operación. "
        "Verifica la conexión con la parcela."
    ),
    ErrorCode.ERR_IRRIGATE: (
        "No se pudo activar el riego. "
        "La parcela puede estar desconectada o en estado de fallo."
    ),
    ErrorCode.ERR_THRESHOLDS: (
        "No se pudieron guardar los umbrales. "
        "Verifica que los valores sean números válidos (0–100)."
    ),
    ErrorCode.ERR_ADD_PARCELA: (
        "No se pudo crear la parcela. "
        "El nombre no puede estar vacío."
    ),
    ErrorCode.ERR_DUPLICATE_PARCELA: (
        "Ya existe una parcela con ese ID o nombre. "
        "Usa un identificador diferente."
    ),
    ErrorCode.ERR_MODIFY_PARCELA: (
        "No se pudo modificar la parcela. "
        "Es posible que haya un problema con la base de datos."
    ),
    ErrorCode.ERR_DELETE_PARCELA: (
        "No se pudo eliminar la parcela. "
        "Desasigna la placa antes de eliminarla."
    ),
    ErrorCode.ERR_SNAPSHOT: (
        "No se pudo guardar la instantánea de configuración."
    ),
    ErrorCode.ERR_SENSOR_READ: (
        "Error al leer el sensor {sensor} en la placa {placa}. "
        "Verifica el cableado."
    ),
    ErrorCode.ERR_MQTT_CONN: (
        "Sin conexión con el broker MQTT en {ip}:{puerto}. "
        "Verifica que Mosquitto esté activo."
    ),
    ErrorCode.ERR_USB_CONN: (
        "No se pudo conectar con la placa en {puerto}. "
        "Verifica el cable y los permisos del puerto."
    ),
    ErrorCode.ERR_FIRMWARE_INCOMPAT: (
        "El firmware seleccionado no es compatible con esta placa o está corrupto."
    ),
    ErrorCode.ERR_FIRMWARE_UPLOAD: (
        "Error al cargar el firmware: {detalle}. "
        "Revisa que la placa esté en modo de carga."
    ),
    ErrorCode.ERR_VAR_READ: (
        "No se pudo obtener el valor de {variable} en {parcela}."
    ),
    ErrorCode.ERR_DB_WRITE: (
        "Los cambios no se guardaron correctamente en la base de datos."
    ),
    ErrorCode.ERR_ID_GENERATION: (
        "No se pudo generar un ID único para la parcela. "
        "Intenta de nuevo."
    ),
}


# ---------------------------------------------------------------------------
# Diálogo de error basado en CTkToplevel
# ---------------------------------------------------------------------------
class ErrorDialog(ctk.CTkToplevel):
    """
    Ventana emergente modal que muestra un mensaje de error.
    Similar a messagebox.showerror pero con el tema de CustomTkinter.
    """

    def __init__(self, parent, message: str) -> None:
        super().__init__(parent)
        self.title("Error")
        self.resizable(False, False)
        # SIN grab_set() aquí — se difiere hasta que la ventana sea visible
        # (evita _tkinter.TclError: grab failed: window not viewable)

        # Configuración mínima de grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Marco principal
        frame = ctk.CTkFrame(self, corner_radius=8)
        frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        frame.grid_columnconfigure(0, weight=1)

        # Icono (texto "⚠" como sustituto rápido)
        ctk.CTkLabel(frame, text="⚠", font=("Roboto", 32),
                     text_color="#F59E0B").grid(row=0, column=0, pady=(10, 5))

        # Mensaje
        ctk.CTkLabel(frame, text=message, font=FONT_NORMAL,
                     wraplength=400, justify="left").grid(
            row=1, column=0, padx=20, pady=(0, 10))

        # Botón Cerrar
        ctk.CTkButton(frame, text="Cerrar", font=FONT_SMALL,
                      command=self.destroy).grid(row=2, column=0, pady=(5, 10))

        # Ajustar tamaño automáticamente
        self.update_idletasks()
        self.minsize(300, 150)

        # Esperar a que la ventana sea visible antes de capturar el foco
        self.update()
        self.after(10, self._set_grab)  # type: ignore[arg-type]
        self.wait_window()

    def _set_grab(self) -> None:
        try:
            self.grab_set()
        except tk.TclError:
            # La ventana puede haberse cerrado antes de que el after() dispare
            pass


# ---------------------------------------------------------------------------
# Manejador de errores
# ---------------------------------------------------------------------------
class ErrorHandler:

    @staticmethod
    def show(code: ErrorCode, parent=None, **kwargs) -> None:
        raw_message = MESSAGES.get(code, "Error desconocido.")
        try:
            message = raw_message.format(**kwargs)
        except KeyError:
            message = raw_message

        if parent and isinstance(parent, ctk.CTk):
            ErrorDialog(parent, message)
        elif parent and hasattr(parent, "winfo_toplevel"):
            root = parent.winfo_toplevel()
            if isinstance(root, ctk.CTk):
                ErrorDialog(root, message)
            else:
                messagebox.showerror("Error", message)
        else:
            messagebox.showerror("Error", message)