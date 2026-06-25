# ui/dialogs/export_dialog.py
from __future__ import annotations

from datetime import datetime
from tkinter import filedialog

import customtkinter as ctk

from ui.error_handler import ErrorCode
from ui.theme import FONT_NORMAL, FONT_SMALL


class ExportDialog(ctk.CTkToplevel):
    def __init__(self, parent, parcelas: list[dict],
                 export_ctrl,
                 error_handler=None):
        super().__init__(parent)
        self.title("Exportar datos")
        self.resizable(False, False)

        self._parcelas = parcelas
        self._export_ctrl = export_ctrl
        self._error_handler = error_handler

        self._build()

        # Esperar a que la ventana sea visible antes de capturar el foco
        self.update()
        self.after(10, self.grab_set)

    def _build(self):
        ctk.CTkLabel(self, text="Parcela:", font=FONT_NORMAL).grid(
            row=0, column=0, padx=14, pady=(14, 4), sticky="w")
        parcelas_ids = [f"{p['id']} - {p['name']}" for p in self._parcelas]
        self._combo_parcela = ctk.CTkComboBox(
            self, values=parcelas_ids, font=FONT_NORMAL, width=250)
        self._combo_parcela.grid(row=1, column=0, padx=14, pady=4, columnspan=2)
        if parcelas_ids:
            self._combo_parcela.set(parcelas_ids[0])

        ctk.CTkLabel(self, text="Tipo de datos:", font=FONT_NORMAL).grid(
            row=2, column=0, padx=14, pady=(12, 4), sticky="w")
        self._combo_tipo = ctk.CTkComboBox(
            self,
            values=["Lecturas de sensores", "Historial de eventos", "Configuración actual"],
            font=FONT_NORMAL, width=250)
        self._combo_tipo.grid(row=3, column=0, padx=14, pady=4, columnspan=2)
        self._combo_tipo.set("Lecturas de sensores")

        self._lbl_start = ctk.CTkLabel(self, text="Fecha inicio (YYYY-MM-DD):", font=FONT_SMALL)
        self._lbl_start.grid(row=4, column=0, padx=14, pady=(12, 0), sticky="w")
        self._entry_start = ctk.CTkEntry(self, width=120, font=FONT_NORMAL)
        self._entry_start.grid(row=5, column=0, padx=14, pady=4, sticky="w")

        self._lbl_end = ctk.CTkLabel(self, text="Fecha fin (YYYY-MM-DD):", font=FONT_SMALL)
        self._lbl_end.grid(row=4, column=1, padx=14, pady=(12, 0), sticky="w")
        self._entry_end = ctk.CTkEntry(self, width=120, font=FONT_NORMAL)
        self._entry_end.grid(row=5, column=1, padx=14, pady=4, sticky="w")

        self._combo_tipo.configure(command=self._toggle_dates)

        ctk.CTkLabel(self, text="Formato:", font=FONT_NORMAL).grid(
            row=6, column=0, padx=14, pady=(12, 4), sticky="w")
        self._combo_fmt = ctk.CTkComboBox(
            self, values=["CSV", "JSON"], font=FONT_NORMAL, width=100)
        self._combo_fmt.grid(row=7, column=0, padx=14, pady=4, sticky="w")
        self._combo_fmt.set("CSV")

        ctk.CTkButton(
            self, text="Exportar",
            font=FONT_SMALL,
            command=self._export,
        ).grid(row=8, column=0, columnspan=2, pady=14)

    def _toggle_dates(self, _value: str = "") -> None:
        if self._combo_tipo.get() == "Configuración actual":
            self._lbl_start.grid_remove()
            self._entry_start.grid_remove()
            self._lbl_end.grid_remove()
            self._entry_end.grid_remove()
        else:
            self._lbl_start.grid()
            self._entry_start.grid()
            self._lbl_end.grid()
            self._entry_end.grid()

    def _export(self):
        sel = self._combo_parcela.get()
        if not sel:
            return
        parcela_id = sel.split(" - ")[0]

        tipo_map = {
            "Lecturas de sensores": "lecturas",
            "Historial de eventos": "eventos",
            "Configuración actual": "config",
        }
        tipo = tipo_map.get(self._combo_tipo.get(), "lecturas")
        fmt = self._combo_fmt.get().lower()
        ext = ".json" if fmt == "json" else ".csv"

        path = filedialog.asksaveasfilename(
            defaultextension=ext,
            filetypes=[("JSON", "*.json")] if fmt == "json" else [("CSV", "*.csv")],
            title=f"Guardar {tipo} como",
        )
        if not path:
            return

        start = end = None
        if tipo != "config":
            try:
                s = self._entry_start.get().strip()
                e = self._entry_end.get().strip()
                if s:
                    start = datetime.strptime(s, "%Y-%m-%d")
                if e:
                    end = datetime.strptime(e, "%Y-%m-%d")
            except ValueError:
                if self._error_handler:
                    self._error_handler.show(ErrorCode.ERR_THRESHOLDS, self)
                return

        # Delegar en el controller
        ok, msg = self._export_ctrl.export(
            parcela_id=parcela_id,
            format=fmt,
            output_path=path,
            start_date=start,
            end_date=end,
            tipo=tipo
        )

        if ok:
            self.destroy()
        else:
            if self._error_handler:
                self._error_handler.show(ErrorCode.ERR_DB_WRITE, self)
