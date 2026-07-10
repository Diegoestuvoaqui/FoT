from __future__ import annotations

import customtkinter as ctk

from ui.theme import FONT_NORMAL, FONT_SMALL, COLORS


class ConfirmDialog(ctk.CTkToplevel):
    """
    Diálogo modal de confirmación estilo CustomTkinter.
    Retorna True (Sí) o False (No) vía el callback on_result.
    """

    def __init__(
        self,
        parent,
        title: str = "Confirmar",
        message: str = "¿Estás seguro?",
        yes_text: str = "Sí",
        no_text: str = "No",
        yes_color: str = "#EF4444",
        yes_hover: str = "#B91C1C",
        on_result=None,
    ):
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        self._on_result = on_result
        self._result = False

        self._build(message, yes_text, no_text, yes_color, yes_hover)
        self._center_window()

        # Modal
        self.transient(parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._on_no)

        self.wait_window()

    def _build(self, message: str, yes_text: str, no_text: str,
               yes_color: str, yes_hover: str):
        self.grid_columnconfigure(0, weight=1)

        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.grid(row=0, column=0, padx=24, pady=24, sticky="nsew")
        frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            frame, text="⚠️", font=("Roboto", 28),
        ).grid(row=0, column=0, pady=(0, 8))

        ctk.CTkLabel(
            frame, text=message, font=FONT_NORMAL,
            wraplength=320, justify="center",
        ).grid(row=1, column=0, pady=(0, 20))

        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.grid(row=2, column=0)
        btn_frame.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkButton(
            btn_frame, text=no_text, font=FONT_SMALL,
            width=80, height=32,
            fg_color="transparent",
            hover_color=("gray80", "#2e2e2e"),
            command=self._on_no,
        ).grid(row=0, column=0, padx=6)

        ctk.CTkButton(
            btn_frame, text=yes_text, font=FONT_SMALL,
            width=120, height=32,
            fg_color=yes_color, hover_color=yes_hover,
            command=self._on_yes,
        ).grid(row=0, column=1, padx=6)

    def _on_yes(self):
        self._result = True
        if self._on_result:
            self._on_result(True)
        self.destroy()

    def _on_no(self):
        self._result = False
        if self._on_result:
            self._on_result(False)
        self.destroy()

    def _center_window(self):
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")

    def get_result(self) -> bool:
        return self._result
