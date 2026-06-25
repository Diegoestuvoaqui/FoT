"""
ui/dialogs/assign_arduino_dialog.py
Diálogo para vincular una placa Arduino a una parcela.
"""
import tkinter as tk

import customtkinter as ctk

from ui.theme import FONT_NORMAL, FONT_SMALL


class AssignArduinoDialog(ctk.CTkToplevel):
    def __init__(self, parent, board_id: str, parcelas: list[dict], on_confirm=None):
        super().__init__(parent)
        self.title(f"Asignar placa {board_id}")
        self.resizable(False, False)
        # SIN grab_set() aquí

        self._board_id = board_id
        self._parcelas = parcelas
        self._on_confirm = on_confirm

        self._build()
        self.update()
        self.after(10, self._set_grab)  # type: ignore[arg-type]

    def _set_grab(self):
        try:
            self.grab_set()
        except tk.TclError:
            pass

    def _build(self):
        # Selector de parcela
        ctk.CTkLabel(self, text="Seleccionar parcela:", font=FONT_NORMAL).grid(
            row=0, column=0, padx=14, pady=(14, 4), sticky="w")

        parcelas_ids = [f"{p['id']} - {p['name']}" for p in self._parcelas]
        self._combo = ctk.CTkComboBox(
            self, values=parcelas_ids,
            font=FONT_NORMAL,
            width=250
        )
        self._combo.grid(row=1, column=0, padx=14, pady=4)
        if parcelas_ids:
            self._combo.set(parcelas_ids[0])

        # Botón confirmar
        ctk.CTkButton(
            self, text="Asignar",
            font=FONT_SMALL,
            command=self._confirm
        ).grid(row=2, column=0, pady=12)

    def _confirm(self):
        seleccion = self._combo.get()
        if not seleccion:
            return
        parcela_id = seleccion.split(" - ")[0]

        # Verificar si la parcela ya tiene asignación (eso lo hará el callback,
        # aquí solo enviamos la solicitud)
        if self._on_confirm:
            self._on_confirm(self._board_id, parcela_id)
        self.destroy()
