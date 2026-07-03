# ui/dialogs/wifi_scan_dialog.py
import tkinter as tk

import customtkinter as ctk

from controller.wifi_controller import WiFiController
from ui.theme import FONT_NORMAL, FONT_SMALL, COLORS


class WiFiScanDialog(ctk.CTkToplevel):
    def __init__(self, parent, on_register=None):
        super().__init__(parent)
        self.title("Buscar dispositivos WiFi")
        self.geometry("500x400")
        self.resizable(False, False)

        self._on_register = on_register
        self._devices: list[dict] = []
        self._controller = WiFiController(
            on_device_found=self._on_device_found,
            on_scan_complete=self._on_scan_complete,
        )

        self._build()
        self.update()
        self.after(10, self._set_grab)

        self._start_scan()

        # ← NUEVO: cancelar escaneo si se cierra el diálogo
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _set_grab(self):
        try:
            self.grab_set()
        except tk.TclError:
            pass

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=14, pady=(14, 4))

        self._lbl_status = ctk.CTkLabel(
            header, text="Buscando...", font=FONT_NORMAL,
            text_color=COLORS["accent"]
        )
        self._lbl_status.pack(side="left")

        self._progress = ctk.CTkProgressBar(header, width=100)
        self._progress.pack(side="right")
        self._progress.set(0)
        self._progress.start()

        self._list_frame = ctk.CTkScrollableFrame(self, label_text="")
        self._list_frame.grid(row=1, column=0, sticky="nsew", padx=14, pady=8)
        self._list_frame.grid_columnconfigure(0, weight=1)

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 14))

        ctk.CTkButton(
            btn_frame, text="Volver a buscar",
            font=FONT_SMALL,
            command=self._start_scan,
        ).pack(side="left", padx=4)

        # ← NUEVO: botón cancelar durante escaneo
        self._btn_cancel = ctk.CTkButton(
            btn_frame, text="Cancelar",
            font=FONT_SMALL, fg_color="#EF4444", hover_color="#B91C1C",
            command=self._on_close,
        )
        self._btn_cancel.pack(side="left", padx=4)

        ctk.CTkButton(
            btn_frame, text="Cerrar",
            font=FONT_SMALL, fg_color="gray",
            command=self._on_close,
        ).pack(side="right", padx=4)

    def _start_scan(self):
        self._clear_list()
        self._lbl_status.configure(text="Buscando...", text_color=COLORS["accent"])
        self._progress.start()
        self._controller.scan_async()

    def _clear_list(self):
        for w in self._list_frame.winfo_children():
            w.destroy()

    def _on_device_found(self, board_id: str, ip: str):
        # Marshaling al hilo principal de Tkinter
        self.after(0, self._update_status_found, board_id)

    def _update_status_found(self, board_id: str):
        if not self.winfo_exists():
            return
        self._lbl_status.configure(text=f"Encontrado: {board_id}")

    def _on_scan_complete(self, devices: list[dict]):
        # Marshaling al hilo principal de Tkinter
        self.after(0, self._render_results, devices)

    def _render_results(self, devices: list[dict]):
        if not self.winfo_exists():
            return

        self._devices = devices
        self._progress.stop()
        self._progress.set(1)

        if not devices:
            self._lbl_status.configure(text="No se encontraron dispositivos", text_color="gray")
            ctk.CTkLabel(
                self._list_frame, text="No hay dispositivos WiFi en la red",
                font=FONT_SMALL, text_color="gray"
            ).grid(row=0, column=0, pady=20)
            return

        self._lbl_status.configure(
            text=f"{len(devices)} dispositivo(s) encontrado(s)",
            text_color=COLORS["accent"]
        )

        for i, dev in enumerate(devices):
            self._add_device_row(i, dev)

    def _add_device_row(self, index: int, device: dict):
        row = ctk.CTkFrame(self._list_frame, corner_radius=6,
                           border_width=1, border_color=COLORS["border"])
        row.grid(row=index, column=0, sticky="ew", pady=2, padx=2)
        row.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(row, text=f"📶 {device['name']}", font=FONT_NORMAL, anchor="w").grid(
            row=0, column=0, padx=10, pady=(6, 0), sticky="w")

        info = f"{device['ip']}:{device['port']} • {device['type']}"
        if device.get('response_ms'):
            info += f" • {device['response_ms']}ms"

        ctk.CTkLabel(row, text=info, font=FONT_SMALL,
                     text_color="gray", anchor="w").grid(
            row=1, column=0, padx=10, pady=(0, 6), sticky="w")

        ctk.CTkButton(
            row, text="Registrar", font=FONT_SMALL, width=80,
            command=lambda d=device: self._register_device(d)
        ).grid(row=0, column=1, rowspan=2, padx=10, pady=8)

    def _register_device(self, device: dict):
        if self._on_register:
            self._on_register(device["id"], device["ip"], "wifi")
        self._on_close()

    def _on_close(self):
        """Cierra el diálogo cancelando el escaneo si está activo."""
        if self._controller.is_scanning():
            self._controller.cancel()
        self.destroy()