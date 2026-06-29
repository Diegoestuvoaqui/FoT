"""
Lista de boards con indicadores de estado de conexión y menú contextual.
Uso:
    lista = BoardList(parent, on_select=callback, on_context_menu=callback)
    lista.set_boards(boards)   # lista de objetos Board
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Optional

import customtkinter as ctk

from ui.theme import CONN_COLORS, FONT_NORMAL, FONT_SMALL

CONN_STATES = {
    "mqtt": "MQTT",
    "usb": "USB",
    "bluetooth": "BT",
    "none": "Sin conexión",
}


class BoardList(ctk.CTkScrollableFrame):
    def __init__(
            self,
            master,
            on_select: Optional[Callable[[str], None]] = None,
            on_context_menu: Optional[Callable[[str, str], None]] = None,
            **kwargs
    ):
        kwargs.setdefault("label_text", "")
        super().__init__(master, **kwargs)

        self.grid_columnconfigure(0, weight=1)

        self._on_select = on_select
        self._on_context_menu = on_context_menu
        self._selected_id: str | None = None
        self._boards = []
        self._row_frames: dict[str, ctk.CTkFrame] = {}
        self._row_labels: dict[str, ctk.CTkLabel] = {}
        self._row_dots: dict[str, ctk.CTkLabel] = {}

    # ------------------------------------------------------------------
    def set_boards(self, boards: list) -> None:
        """Actualizar la lista completa de boards."""
        self._clear_rows()
        self._boards = boards
        for i, board in enumerate(boards):
            self._add_row(board, i)

    def update_board(self, board_id: str, **data) -> None:
        """Actualizar visualmente una fila en concreto."""
        if board_id in self._row_frames:
            self._refresh_row(board_id, **data)

    # ------------------------------------------------------------------
    def _clear_rows(self) -> None:
        for widget in self.winfo_children():
            widget.destroy()
        self._row_frames.clear()
        self._row_labels.clear()
        self._row_dots.clear()

    def _add_row(self, board, index: int) -> None:
        bid = board.id
        name = board.sketch_name or board.id
        conn = getattr(board, "conn", "none")
        status = getattr(board, "status", "Desconocida")

        frame = ctk.CTkFrame(
            self,
            corner_radius=8,
            border_width=2,
            border_color="#3F3F3F",
        )
        frame.grid(row=index, column=0, sticky="ew", pady=3, padx=2)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_columnconfigure(1, minsize=40)

        lbl_name = ctk.CTkLabel(
            frame,
            text=name,
            font=FONT_NORMAL,
            anchor="w",
        )
        lbl_name.grid(row=0, column=0, padx=(10, 4), pady=(6, 0), sticky="w")

        info_text = f"{status}  •  {CONN_STATES.get(conn, 'Sin conexión')}"
        lbl_info = ctk.CTkLabel(
            frame,
            text=info_text,
            font=FONT_SMALL,
            text_color=CONN_COLORS.get("connected") if conn != "none" else "#6B7280",
            anchor="w",
        )
        lbl_info.grid(row=1, column=0, padx=(10, 4), pady=(0, 6), sticky="w")

        dot_color = CONN_COLORS.get("connected") if conn != "none" else CONN_COLORS.get("disconnected")
        dot = ctk.CTkLabel(
            frame,
            text="●",
            width=16,
            font=("Roboto", 12),
            text_color=dot_color,
        )
        dot.grid(row=0, column=1, rowspan=2, padx=(0, 10), sticky="e")

        btn_menu = ctk.CTkButton(
            frame,
            text="⋮",
            width=30,
            height=30,
            corner_radius=6,
            fg_color="transparent",
            hover_color=("gray80", "#2e2e2e"),
            font=("Roboto", 16),
            command=lambda b=bid: self._handle_context_menu(b),
        )
        btn_menu.grid(row=0, column=2, rowspan=2, padx=(0, 6), sticky="e")

        for w in (frame, lbl_name, lbl_info, dot):
            w.bind("<Button-1>", lambda e, b=bid: self._handle_select(b))

        self._row_frames[bid] = frame
        self._row_labels[bid] = lbl_info
        self._row_dots[bid] = dot

    def _refresh_row(self, board_id: str, **data) -> None:
        conn = data.get("connection", "none")
        status = data.get("status", "Desconocida")

        if board_id in self._row_labels:
            info_text = f"{status}  •  {CONN_STATES.get(conn, 'Sin conexión')}"
            self._row_labels[board_id].configure(
                text=info_text,
                text_color=CONN_COLORS.get("connected") if conn != "none" else "#6B7280",
            )
        if board_id in self._row_dots:
            dot_color = (CONN_COLORS.get("connected")
                         if conn != "none"
                         else CONN_COLORS.get("disconnected"))
            self._row_dots[board_id].configure(text_color=dot_color)

    # ------------------------------------------------------------------
    def _handle_select(self, board_id: str) -> None:
        self._selected_id = board_id
        for bid, frame in self._row_frames.items():
            frame.configure(border_color="#22C55E" if bid == board_id else "#3F3F3F")
        if self._on_select:
            self._on_select(board_id)

    def _handle_context_menu(self, board_id: str) -> None:
        popup = ctk.CTkToplevel(self)
        popup.wm_overrideredirect(True)
        popup.attributes("-topmost", True)

        x = self.winfo_pointerx()
        y = self.winfo_pointery()
        popup.wm_geometry(f"+{x}+{y}")

        frame = ctk.CTkFrame(popup, corner_radius=8, border_width=1,
                             border_color="#3F3F3F", fg_color="#2B2B2B")
        frame.pack(padx=1, pady=1)

        def _close() -> None:
            popup.destroy()

        def _ver_detalle() -> None:
            _close()
            if self._on_context_menu:
                self._on_context_menu(board_id, "detail")

        def _eliminar() -> None:
            _close()
            if self._on_context_menu:
                self._on_context_menu(board_id, "delete")

        ctk.CTkButton(
            frame,
            text="🔍  Ver detalle",
            font=("Roboto", 12),
            anchor="w",
            width=180,
            height=34,
            fg_color="transparent",
            hover_color="#3F3F3F",
            text_color=("gray10", "gray90"),
            corner_radius=6,
            command=_ver_detalle,
        ).pack(padx=4, pady=(4, 0), fill="x")

        ctk.CTkFrame(frame, height=1, fg_color="#3F3F3F",
                     corner_radius=0).pack(fill="x", padx=6, pady=4)

        ctk.CTkButton(
            frame,
            text="🗑️  Eliminar board",
            font=("Roboto", 12),
            anchor="w",
            width=180,
            height=34,
            fg_color="transparent",
            hover_color="#3F3F3F",
            text_color="#EF4444",
            corner_radius=6,
            command=_eliminar,
        ).pack(padx=4, pady=(0, 4), fill="x")

        popup.bind("<FocusOut>", lambda e: _close())
        popup.focus_set()

    @property
    def selected_id(self) -> str | None:
        return self._selected_id
