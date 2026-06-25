"""
ui/panels/help_panel.py
Panel de ayuda integrada con texto en español.
"""
import customtkinter as ctk

from help.help_text import HELP_TEXT
from ui.theme import FONT_TITLE


class HelpPanel(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Título
        ctk.CTkLabel(
            self,
            text="Ayuda de FoT",
            font=FONT_TITLE
        ).grid(row=0, column=0, padx=16, pady=(16, 8), sticky="w")

        # Cuadro de texto con la ayuda
        self._text = ctk.CTkTextbox(
            self,
            font=("Courier New", 12),  # monoespaciado para que quede limpio
            wrap="word",
            state="normal"
        )
        self._text.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))

        # Insertar contenido
        self._text.insert("1.0", HELP_TEXT)
        self._text.configure(state="disabled")  # solo lectura
