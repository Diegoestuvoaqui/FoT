"""
ui/dialogs/firmware_dialog.py
Diálogo para cargar firmware .hex en placas Arduino vía avrdude.
Soporta selección de MCU, programmer, progreso en tiempo real y cancelación.
"""
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog
from typing import Optional

import customtkinter as ctk

from logic.firmware_uploader import FirmwareUploader
from ui.theme import FONT_NORMAL, FONT_SMALL, FONT_MONO, COLORS


class FirmwareDialog(ctk.CTkToplevel):
    def __init__(self, parent, board_id: str, port: str,
                 current_version: str = "Desconocida"):
        super().__init__(parent)
        self.title(f"Actualizar firmware — {board_id}")
        self.geometry("660x660")
        self.resizable(False, False)

        self._board_id = board_id
        self._port = port
        self._current_version = current_version
        self._hex_path: Optional[str] = None
        self._uploader = FirmwareUploader()
        self._upload_thread: Optional[threading.Thread] = None
        self._is_uploading = False

        self._build()
        self.update()
        self.after(10, lambda: self._set_grab())

    def _set_grab(self) -> None:
        try:
            self.grab_set()
        except tk.TclError:
            pass

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)

        # === HEADER ===
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, padx=14, pady=(14, 4), sticky="ew")

        ctk.CTkLabel(header, text=f"Placa: {self._board_id}", font=FONT_NORMAL).pack(
            side="left", padx=4)
        ctk.CTkLabel(
            header, text=f"Versión actual: {self._current_version}",
            font=FONT_SMALL, text_color="gray"
        ).pack(side="right", padx=4)

        # === OPCIONES AVRDUDE ===
        opts_frame = ctk.CTkFrame(self)
        opts_frame.grid(row=1, column=0, padx=14, pady=8, sticky="ew")
        opts_frame.grid_columnconfigure((0, 1), weight=1)

        # MCU
        ctk.CTkLabel(opts_frame, text="MCU:", font=FONT_SMALL).grid(
            row=0, column=0, padx=8, pady=(8, 2), sticky="w")
        self._mcu_var = ctk.StringVar(value="atmega328p")
        self._combo_mcu = ctk.CTkComboBox(
            opts_frame,
            values=["atmega328p", "atmega2560", "atmega32u4", "attiny85"],
            variable=self._mcu_var,
            font=FONT_SMALL,
            width=180,
        )
        self._combo_mcu.grid(row=1, column=0, padx=8, pady=(0, 8), sticky="w")

        # Programmer
        ctk.CTkLabel(opts_frame, text="Programmer:", font=FONT_SMALL).grid(
            row=0, column=1, padx=8, pady=(8, 2), sticky="w")
        self._prog_var = ctk.StringVar(value="arduino")
        self._combo_prog = ctk.CTkComboBox(
            opts_frame,
            values=["arduino", "stk500v1", "stk500v2", "avrisp", "usbasp"],
            variable=self._prog_var,
            font=FONT_SMALL,
            width=180,
        )
        self._combo_prog.grid(row=1, column=1, padx=8, pady=(0, 8), sticky="w")

        # === SELECCIÓN DE ARCHIVO ===
        file_frame = ctk.CTkFrame(self, fg_color="transparent")
        file_frame.grid(row=2, column=0, padx=14, pady=8, sticky="ew")

        self._lbl_file = ctk.CTkLabel(
            file_frame, text="Ningún archivo seleccionado", font=FONT_SMALL)
        self._lbl_file.pack(side="left", padx=4, fill="x", expand=True)

        ctk.CTkButton(
            file_frame, text="Seleccionar .hex",
            font=FONT_SMALL, command=self._select_file
        ).pack(side="right", padx=4)

        # === INFO DEL ARCHIVO ===
        self._lbl_file_info = ctk.CTkLabel(
            self, text="", font=FONT_SMALL, text_color="gray")
        self._lbl_file_info.grid(row=3, column=0, padx=14, pady=(0, 4), sticky="w")

        # === PROGRESO ===
        self._progress = ctk.CTkProgressBar(self, width=300)
        self._progress.grid(row=4, column=0, padx=14, pady=4, sticky="ew")
        self._progress.set(0)

        # === LOG ===
        self._log = ctk.CTkTextbox(self, height=180, font=FONT_MONO, state="disabled")
        self._log.grid(row=5, column=0, padx=14, pady=8, sticky="ew")

        # === ESTADO ===
        self._lbl_status = ctk.CTkLabel(
            self, text="Listo — selecciona un archivo .hex", font=FONT_SMALL,
            text_color="gray")
        self._lbl_status.grid(row=6, column=0, padx=14, pady=(0, 4), sticky="w")

        # === BOTONES ===
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=7, column=0, pady=8)

        self._btn_start = ctk.CTkButton(
            btn_frame, text="▶  Iniciar carga",
            font=FONT_SMALL, command=self._start_flash, state="disabled"
        )
        self._btn_start.pack(side="left", padx=4)

        self._btn_cancel = ctk.CTkButton(
            btn_frame, text="⏹  Cancelar",
            font=FONT_SMALL, fg_color="#EF4444", hover_color="#B91C1C",
            command=self._cancel_flash, state="disabled"
        )
        self._btn_cancel.pack(side="left", padx=4)

        ctk.CTkButton(
            btn_frame, text="Cerrar",
            font=FONT_SMALL, fg_color="gray", command=self.destroy
        ).pack(side="left", padx=4)

    def _select_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Seleccionar firmware .hex",
            filetypes=[("Intel HEX", "*.hex"), ("Todos los archivos", "*.*")]
        )
        if not path:
            return

        self._hex_path = path
        self._lbl_file.configure(text=Path(path).name)

        try:
            size = Path(path).stat().st_size
            if size == 0:
                self._lbl_file_info.configure(
                    text="⚠️  Archivo vacío", text_color=COLORS["fault"])
                self._btn_start.configure(state="disabled")
                return
            size_kb = size / 1024
            self._lbl_file_info.configure(
                text=f"📄  {size_kb:.1f} KB", text_color="green")
            self._btn_start.configure(state="normal")
        except OSError:
            self._lbl_file_info.configure(
                text="⚠️  No se puede leer el archivo", text_color=COLORS["fault"])
            self._btn_start.configure(state="disabled")

    def _start_flash(self) -> None:
        if not self._hex_path:
            return

        self._is_uploading = True
        self._btn_start.configure(state="disabled")
        self._btn_cancel.configure(state="normal")
        self._combo_mcu.configure(state="disabled")
        self._combo_prog.configure(state="disabled")
        self._lbl_status.configure(text="Cargando firmware...", text_color="orange")
        self._log_clear()
        self._log_add(f"MCU: {self._mcu_var.get()}\n")
        self._log_add(f"Programmer: {self._prog_var.get()}\n")
        self._log_add(f"Puerto: {self._port}\n")
        self._log_add(f"Archivo: {Path(self._hex_path).name}\n")
        self._log_add("─" * 40 + "\n")
        self._log_add("Iniciando avrdude...\n\n")

        self._upload_thread = threading.Thread(target=self._run_upload, daemon=True)
        self._upload_thread.start()

    def _cancel_flash(self) -> None:
        if not self._is_uploading:
            return
        self._log_add("\n⚠️  Cancelando operación...\n")
        self._uploader.cancel()
        self._is_uploading = False
        self._btn_cancel.configure(state="disabled")
        self._lbl_status.configure(text="Cancelado por el usuario", text_color=COLORS["fault"])

    def _run_upload(self) -> None:
        success, message = self._uploader.upload(
            port=self._port,
            hex_path=self._hex_path or "",
            mcu=self._mcu_var.get(),
            programmer=self._prog_var.get(),
            progress_callback=self._on_progress_line
        )
        self._is_uploading = False
        self.after(0, self._set_status, "Éxito" if success else "Error",
                   "green" if success else "red")
        self.after(0, self._log_add, "\n" + message + "\n")
        self.after(0, self._reset_ui_after_upload)

    def _reset_ui_after_upload(self) -> None:
        self._btn_start.configure(state="normal" if self._hex_path else "disabled")
        self._btn_cancel.configure(state="disabled")
        self._combo_mcu.configure(state="normal")
        self._combo_prog.configure(state="normal")

    def _on_progress_line(self, line: str) -> None:
        self.after(0, self._log_add, line + "\n")
        low = line.lower()
        if "writing flash" in low:
            self.after(0, self._update_progress, 0.5)
        elif "reading on-chip flash" in low:
            self.after(0, self._update_progress, 0.8)
        elif "avrdude done" in low:
            self.after(0, self._update_progress, 1.0)

    def _log_add(self, text: str) -> None:
        self._log.configure(state="normal")
        self._log.insert("end", text)
        self._log.see("end")
        self._log.configure(state="disabled")

    def _log_clear(self) -> None:
        self._log.configure(state="normal")
        self._log.delete("1.0", "end")
        self._log.configure(state="disabled")

    def _update_progress(self, value: float) -> None:
        self._progress.set(value)

    def _set_status(self, text: str, color: str) -> None:
        self._lbl_status.configure(text=text, text_color=color)
