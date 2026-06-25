"""
ui/widgets/event_log.py
Registro de eventos con filtros: Todos, Solo errores, Solo riegos, Solo cambios de modo.
Uso:
    log = EventLog(parent)
    log.add_line("14:32 — Fallo sensor suelo")
    log.clear_view()
"""
from __future__ import annotations

import customtkinter as ctk

from ui.theme import FONT_SMALL, FONT_MONO


class EventLog(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Filtros
        filter_frame = ctk.CTkFrame(self, fg_color="transparent")
        filter_frame.grid(row=0, column=0, sticky="ew", padx=6, pady=(6, 0))

        self._filter_var = ctk.StringVar(value="todos")
        filters = [
            ("Todos", "todos"),
            ("Solo errores", "errores"),
            ("Solo riegos", "riegos"),
            ("Solo cambios de modo", "modos"),
        ]
        for i, (text, value) in enumerate(filters):
            rb = ctk.CTkRadioButton(
                filter_frame,
                text=text,
                variable=self._filter_var,
                value=value,
                font=FONT_SMALL,
                command=self._apply_filter,
            )
            rb.grid(row=0, column=i, padx=(4, 8), pady=4)

        # Botón limpiar vista
        btn_clear = ctk.CTkButton(
            filter_frame,
            text="Limpiar vista",
            font=FONT_SMALL,
            width=100,
            command=self.clear_view,
        )
        btn_clear.grid(row=0, column=len(filters), padx=8, pady=4, sticky="e")
        filter_frame.grid_columnconfigure(len(filters), weight=1)  # empuja a la derecha

        # Cuadro de texto
        self._text = ctk.CTkTextbox(
            self,
            font=FONT_MONO,
            state="disabled",
            wrap="word",
        )
        self._text.grid(row=1, column=0, sticky="nsew", padx=6, pady=6)

        self._lines = []  # todas las líneas (crudas, como string)
        self._current_filter = "todos"

    def add_line(self, text: str, tipo: str = "") -> None:
        """Añadir una línea al registro. tipo puede ser 'error', 'riego', 'modo' para filtrar."""
        self._lines.append((text, tipo))
        self._apply_filter()

    def clear_view(self) -> None:
        """Limpia la vista pero no borra los datos subyacentes."""
        self._text.configure(state="normal")
        self._text.delete("1.0", "end")
        self._text.configure(state="disabled")
        # No borramos self._lines, solo la vista.

    def _apply_filter(self):
        filter_val = self._filter_var.get()
        self._current_filter = filter_val

        self._text.configure(state="normal")
        self._text.delete("1.0", "end")
        for line, tipo in self._lines:
            if filter_val == "todos":
                show = True
            elif filter_val == "errores" and tipo == "error":
                show = True
            elif filter_val == "riegos" and tipo == "riego":
                show = True
            elif filter_val == "modos" and tipo == "modo":
                show = True
            else:
                show = False
            if show:
                self._text.insert("end", line + "\n")
        self._text.see("end")
        self._text.configure(state="disabled")
