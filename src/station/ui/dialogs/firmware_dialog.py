"""
ui/dialogs/firmware_dialog.py
"""
import threading
import tkinter as tk
from pathlib import Path  # ← reemplaza os.path
from tkinter import filedialog
from typing import Optional

import customtkinter as ctk

from logic.firmware_uploader import FirmwareUploader
from ui.theme import FONT_NORMAL, FONT_SMALL, FONT_MONO


class FirmwareDialog(ctk.CTkToplevel):
    def __init__(self, parent, board_id: str, port: str,
                 current_version: str = "Desconocida"):
        super().__init__(parent)
        self.title(f"Actualizar firmware - {board_id}")
        self.resizable(False, False)

        self._board_id = board_id
        self._port = port
        self._current_version = current_version
        self._hex_path: Optional[str] = None
        self._uploader = FirmwareUploader()

        self._build()
        self.update()
        self.after(10, lambda: self._set_grab())  # type: ignore[arg-type]

    def _set_grab(self) -> None:
        try:
            self.grab_set()
        except tk.TclError:
            pass

    def _build(self) -> None:
        ctk.CTkLabel(self, text=f"Placa: {self._board_id}", font=FONT_NORMAL).grid(
            row=0, column=0, padx=14, pady=(14, 4), sticky="w")
        ctk.CTkLabel(self, text=f"Versión actual: {self._current_version}", font=FONT_NORMAL).grid(
            row=1, column=0, padx=14, pady=4, sticky="w")

        file_frame = ctk.CTkFrame(self, fg_color="transparent")
        file_frame.grid(row=2, column=0, padx=14, pady=8, sticky="ew")
        self._lbl_file = ctk.CTkLabel(file_frame, text="Ningún archivo seleccionado", font=FONT_SMALL)
        self._lbl_file.pack(side="left", padx=4)
        ctk.CTkButton(
            file_frame, text="Seleccionar .hex",
            font=FONT_SMALL, command=self._select_file
        ).pack(side="right", padx=4)

        self._progress = ctk.CTkProgressBar(self, width=300)
        self._progress.grid(row=3, column=0, padx=14, pady=4, sticky="ew")
        self._progress.set(0)

        self._log = ctk.CTkTextbox(self, height=150, font=FONT_MONO, state="disabled")
        self._log.grid(row=4, column=0, padx=14, pady=8, sticky="ew")

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=5, column=0, pady=8)
        self._btn_start = ctk.CTkButton(
            btn_frame, text="Iniciar carga",
            font=FONT_SMALL, command=self._start_flash, state="disabled"
        )
        self._btn_start.pack(side="left", padx=4)
        ctk.CTkButton(
            btn_frame, text="Cerrar",
            font=FONT_SMALL, fg_color="gray", command=self.destroy
        ).pack(side="left", padx=4)

        self._lbl_status = ctk.CTkLabel(self, text="Listo", font=FONT_SMALL,
                                        text_color="green")
        self._lbl_status.grid(row=6, column=0, padx=14, pady=(0, 8), sticky="w")

    def _select_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Seleccionar firmware .hex",
            filetypes=[("Intel HEX", "*.hex")]
        )
        if path:
            self._hex_path = path
            self._lbl_file.configure(text=Path(path).name)  # ← Path.name reemplaza os.path.basename
            self._btn_start.configure(state="normal")

    def _start_flash(self) -> None:
        if not self._hex_path:
            return
        self._btn_start.configure(state="disabled")
        self._lbl_status.configure(text="Cargando...", text_color="orange")
        self._log_clear()
        self._log_add("Iniciando avrdude...\n")
        threading.Thread(target=self._run_upload, daemon=True).start()

    def _run_upload(self) -> None:
        success, message = self._uploader.upload(
            port=self._port,
            hex_path=self._hex_path or "",
            progress_callback=self._on_progress_line
        )
        self.after(0, self._set_status, "Éxito" if success else "Error",
                   "green" if success else "red")  # ← after() con args posicionales
        self.after(0, self._log_add, message + "\n")

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
        self._btn_start.configure(state="normal")
