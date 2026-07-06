"""
ui/dialogs/arduino_register_dialog.py
Diálogo para registrar manualmente una placa Arduino.
Permite especificar ID, tipo de conexión, puerto/IP y datos opcionales.
"""
from __future__ import annotations

import logging
from typing import Callable, Optional

import customtkinter as ctk

from ui.theme import FONT_TITLE, FONT_NORMAL, FONT_SMALL, COLORS

logger = logging.getLogger(__name__)


class ArduinoRegisterDialog(ctk.CTkToplevel):
    """
    Diálogo modal para registrar una placa Arduino manualmente.
    Soporta USB (por puerto serial), Bluetooth (rfcomm) y WiFi (IP).
    """

    def __init__(
        self,
        parent,
        on_register: Optional[Callable[[str, str, str, dict], None]] = None,
        available_ports: Optional[list[str]] = None,
    ):
        """
        Args:
            parent: Widget padre
            on_register: callback(board_id, port, conn_type, extra_data)
            available_ports: Lista de puertos seriales disponibles (opcional)
        """
        super().__init__(parent)
        self.title("FoT — Registrar Arduino")
        self.geometry("800x1000")
        self.resizable(False, False)

        self._on_register = on_register
        self._available_ports = available_ports or []

        self._build()
        self._center_window()

        self.transient(parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._entry_id.focus()
        self.wait_window()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------
    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        container = ctk.CTkFrame(self, fg_color="transparent")
        container.grid(row=0, column=0, sticky="nsew", padx=24, pady=24)
        container.grid_columnconfigure(0, weight=1)

        row = 0

        # Título
        ctk.CTkLabel(
            container,
            text="🔧 Registrar nueva placa",
            font=FONT_TITLE,
            text_color=COLORS["accent"],
        ).grid(row=row, column=0, sticky="w", pady=(0, 4))
        row += 1

        ctk.CTkLabel(
            container,
            text="Registra manualmente una placa Arduino para monitorearla.",
            font=FONT_SMALL,
            text_color="gray",
        ).grid(row=row, column=0, sticky="w", pady=(0, 16))
        row += 1

        # === TIPO DE CONEXIÓN ===
        ctk.CTkLabel(
            container, text="Tipo de conexión", font=FONT_NORMAL, anchor="w"
        ).grid(row=row, column=0, sticky="w", pady=(0, 4))
        row += 1

        self._conn_var = ctk.StringVar(value="usb")
        conn_frame = ctk.CTkFrame(container, fg_color="transparent")
        conn_frame.grid(row=row, column=0, sticky="ew", pady=(0, 12))

        for i, (value, label, icon) in enumerate([
            ("usb", "USB", "🔌"),
            ("bluetooth", "Bluetooth", "📡"),
            ("wifi", "WiFi", "📶"),
        ]):
            rb = ctk.CTkRadioButton(
                conn_frame,
                text=f"{icon} {label}",
                variable=self._conn_var,
                value=value,
                font=FONT_SMALL,
                command=self._on_conn_type_changed,
            )
            rb.grid(row=0, column=i, padx=(0, 16))
        row += 1

        # Separador
        ctk.CTkFrame(container, height=1, fg_color=COLORS["border"]).grid(
            row=row, column=0, sticky="ew", pady=8)
        row += 1

        # === ID DE LA PLACA ===
        ctk.CTkLabel(
            container, text="ID de la placa *", font=FONT_NORMAL, anchor="w"
        ).grid(row=row, column=0, sticky="w", pady=(0, 4))
        row += 1

        self._entry_id = ctk.CTkEntry(
            container, font=FONT_NORMAL, height=40,
            placeholder_text="Ej: board-01, arduino-salon, etc."
        )
        self._entry_id.grid(row=row, column=0, sticky="ew", pady=(0, 12))
        row += 1

        # === PUERTO / DIRECCIÓN ===
        self._lbl_port = ctk.CTkLabel(
            container, text="Puerto serial *", font=FONT_NORMAL, anchor="w"
        )
        self._lbl_port.grid(row=row, column=0, sticky="w", pady=(0, 4))
        row += 1

        # Combo para puertos disponibles + entrada manual
        port_frame = ctk.CTkFrame(container, fg_color="transparent")
        port_frame.grid(row=row, column=0, sticky="ew", pady=(0, 12))
        port_frame.grid_columnconfigure(1, weight=1)

        self._combo_ports = ctk.CTkComboBox(
            port_frame,
            values=self._available_ports or ["/dev/ttyUSB0", "/dev/ttyACM0", "COM3", "COM4"],
            font=FONT_NORMAL,
            width=180,
        )
        self._combo_ports.grid(row=0, column=0, padx=(0, 8))

        self._entry_port = ctk.CTkEntry(
            port_frame, font=FONT_NORMAL, height=40,
            placeholder_text="O escribe manualmente..."
        )
        self._entry_port.grid(row=0, column=1, sticky="ew")
        row += 1

        # === IP (solo WiFi) ===
        self._lbl_ip = ctk.CTkLabel(
            container, text="Dirección IP *", font=FONT_NORMAL, anchor="w"
        )
        self._entry_ip = ctk.CTkEntry(
            container, font=FONT_NORMAL, height=40,
            placeholder_text="Ej: 192.168.1.100"
        )
        # Se muestra/oculta según tipo de conexión
        row = self._build_wifi_fields(container, row)

        # Separador
        ctk.CTkFrame(container, height=1, fg_color=COLORS["border"]).grid(
            row=row, column=0, sticky="ew", pady=8)
        row += 1

        # === DATOS OPCIONALES ===
        ctk.CTkLabel(
            container, text="Datos opcionales", font=FONT_NORMAL, anchor="w"
        ).grid(row=row, column=0, sticky="w", pady=(0, 4))
        row += 1

        # Nombre del sketch
        ctk.CTkLabel(
            container, text="Sketch (opcional):", font=FONT_SMALL, anchor="w"
        ).grid(row=row, column=0, sticky="w", pady=(0, 2))
        row += 1

        self._entry_sketch = ctk.CTkEntry(
            container, font=FONT_NORMAL, height=36,
            placeholder_text="Ej: dht11, suelo, custom..."
        )
        self._entry_sketch.grid(row=row, column=0, sticky="ew", pady=(0, 8))
        row += 1

        # === ERROR ===
        self._lbl_error = ctk.CTkLabel(
            container, text="", font=FONT_SMALL, text_color=COLORS["fault"]
        )
        self._lbl_error.grid(row=row, column=0, sticky="w", pady=(0, 8))
        row += 1

        # === BOTONES ===
        btn_frame = ctk.CTkFrame(container, fg_color="transparent")
        btn_frame.grid(row=row, column=0, sticky="ew")
        btn_frame.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkButton(
            btn_frame,
            text="Cancelar",
            font=FONT_NORMAL,
            height=40,
            fg_color="transparent",
            hover_color=("gray80", "#2e2e2e"),
            command=self._on_close,
        ).grid(row=0, column=0, padx=(0, 8), sticky="ew")

        ctk.CTkButton(
            btn_frame,
            text="Registrar placa",
            font=FONT_NORMAL,
            height=40,
            fg_color=COLORS["accent"],
            hover_color="#16A34A",
            command=self._do_register,
        ).grid(row=0, column=1, padx=(8, 0), sticky="ew")

        # Bind Enter
        self._entry_id.bind("<Return>", lambda e: self._entry_port.focus())
        self._entry_port.bind("<Return>", lambda e: self._do_register())
        self._entry_ip.bind("<Return>", lambda e: self._do_register())

    def _build_wifi_fields(self, container, start_row: int) -> int:
        """Construye campos específicos para WiFi, inicialmente ocultos."""
        self._wifi_frame = ctk.CTkFrame(container, fg_color="transparent")
        self._wifi_frame.grid(row=start_row, column=0, sticky="ew", pady=(0, 12))
        self._wifi_frame.grid_columnconfigure(0, weight=1)
        self._wifi_frame.grid_remove()  # Oculto por defecto

        ctk.CTkLabel(
            self._wifi_frame, text="Dirección IP *", font=FONT_NORMAL, anchor="w"
        ).grid(row=0, column=0, sticky="w", pady=(0, 4))

        self._entry_ip = ctk.CTkEntry(
            self._wifi_frame, font=FONT_NORMAL, height=40,
            placeholder_text="Ej: 192.168.1.100"
        )
        self._entry_ip.grid(row=1, column=0, sticky="ew")

        return start_row + 1

    # ------------------------------------------------------------------
    # Eventos
    # ------------------------------------------------------------------
    def _on_conn_type_changed(self):
        conn = self._conn_var.get()

        if conn == "wifi":
            # Mostrar campo IP, ocultar puerto
            self._lbl_port.grid_remove()
            self._combo_ports.grid_remove()
            self._entry_port.grid_remove()
            self._wifi_frame.grid()
        else:
            # Mostrar puerto, ocultar IP
            self._lbl_port.grid()
            self._combo_ports.grid()
            self._entry_port.grid()
            self._wifi_frame.grid_remove()

        # Actualizar label del puerto según tipo
        labels = {
            "usb": "Puerto serial *",
            "bluetooth": "Puerto RFCOMM *",
            "wifi": "Dirección IP *",
        }
        self._lbl_port.configure(text=labels.get(conn, "Puerto *"))

    def _do_register(self):
        board_id = self._entry_id.get().strip()
        conn = self._conn_var.get()

        # Validar ID
        if not board_id:
            self._lbl_error.configure(text="El ID de la placa es obligatorio")
            return

        if " " in board_id:
            self._lbl_error.configure(text="El ID no puede contener espacios")
            return

        # Obtener puerto/IP según tipo
        if conn == "wifi":
            port = self._entry_ip.get().strip()
            if not port:
                self._lbl_error.configure(text="La dirección IP es obligatoria")
                return
            # Validar formato básico de IP
            parts = port.split(".")
            if len(parts) != 4 or not all(p.isdigit() and 0 <= int(p) <= 255 for p in parts):
                self._lbl_error.configure(text="La dirección IP no es válida")
                return
        else:
            port = self._entry_port.get().strip()
            if not port:
                port = self._combo_ports.get()
            if not port or port == "O escribe manualmente...":
                self._lbl_error.configure(text="El puerto es obligatorio")
                return

        # Datos extra
        extra = {}
        sketch = self._entry_sketch.get().strip()
        if sketch:
            extra["sketch_name"] = sketch
        notes = self._entry_notes.get().strip()
        if notes:
            extra["notes"] = notes

        logger.info("Registrando placa manual: %s (%s) en %s", board_id, conn, port)

        if self._on_register:
            self._on_register(board_id, port, conn, extra)

        self.destroy()

    def _on_close(self):
        self.destroy()

    def _center_window(self):
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")