"""
ui/widgets/board_list.py
Lista de boards con indicadores de estado de conexión y selección visual.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Optional

import customtkinter as ctk

from domain.boards import Board
from ui.theme import CONN_COLORS, FONT_NORMAL, FONT_SMALL, COLORS

CONN_STATES = {
    "mqtt": "MQTT",
    "usb": "USB",
    "bluetooth": "BT",
    "wifi": "WiFi",
    "none": "Sin conexión",
}


class BoardList(ctk.CTkScrollableFrame):
    def __init__(
            self,
            master,
            on_select: Optional[Callable[[str], None]] = None,
            on_context_menu: Optional[Callable[[str, str], None]] = None,
            on_claim: Optional[Callable[[str], None]] = None,
            **kwargs
    ):
        kwargs.setdefault("label_text", "")
        super().__init__(master, **kwargs)

        self.grid_columnconfigure(0, weight=1)

        self._on_select = on_select
        self._on_context_menu = on_context_menu
        self._on_claim = on_claim
        self._selected_id: str | None = None
        self._boards: list[Board] = []
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

    def update_board(self, board: Board) -> None:
        """Actualizar o agregar una board individual."""
        # Buscar si existe
        found = False
        for i, b in enumerate(self._boards):
            if b.id == board.id:
                self._boards[i] = board
                found = True
                break
        if not found:
            self._boards.append(board)

        # Reconstruir toda la lista (simple pero funcional)
        self.set_boards(self._boards)

        # Restaurar selección si existía
        if self._selected_id:
            self._select_board(self._selected_id)

    def get_selected(self) -> str | None:
        return self._selected_id

    # ------------------------------------------------------------------
    def _clear_rows(self) -> None:
        for widget in self.winfo_children():
            widget.destroy()
        self._row_frames.clear()
        self._row_labels.clear()
        self._row_dots.clear()

    def _add_row(self, board: Board, index: int) -> None:
        bid = board.id
        name = board.sketch_name or board.id
        conn = getattr(board, "conn", "none")
        status = getattr(board, "status", "Desconocida")
        unclaimed = board.usuario_id is None   # ← NUEVO

        is_connected = status == "Conectada"
        status_color = COLORS["accent"] if is_connected else "gray"

        frame = ctk.CTkFrame(
            self,
            corner_radius=8,
            border_width=2,
            border_color=COLORS["accent"] if bid == self._selected_id else "#3F3F3F",
        )
        frame.grid(row=index, column=0, sticky="ew", pady=3, padx=2)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_columnconfigure(1, minsize=40)
        if unclaimed:
            frame.grid_columnconfigure(2, minsize=90)   # ← NUEVO

        lbl_name = ctk.CTkLabel(
            frame,
            text=f"{self._conn_icon(conn)} {name}",
            font=FONT_NORMAL,
            anchor="w",
        )
        lbl_name.grid(row=0, column=0, padx=(10, 4), pady=(6, 0), sticky="w")

        factory_info = board.manufacturer or "Desconocido"
        if board.serial_number:
            factory_info += f" • S/N: {board.serial_number[:8]}..."

        # ← NUEVO: distinguir visualmente "sin asignar" de "detectada/conectada con dueño"
        display_status = "Sin asignar (detectada)" if unclaimed else status
        #info_text = f"{display_status}  •  {factory_info}"
        info_text = f"{display_status}"
        lbl_info = ctk.CTkLabel(
            frame,
            text=info_text,
            font=FONT_SMALL,
            text_color=COLORS["fault"] if unclaimed else status_color,
            anchor="w",
        )
        lbl_info.grid(row=1, column=0, padx=(10, 4), pady=(0, 6), sticky="w")

        dot_color = COLORS["accent"] if is_connected else COLORS["disconnected"]
        dot = ctk.CTkLabel(
            frame, text="●", width=16, font=("Roboto", 12), text_color=dot_color,
        )
        dot.grid(row=0, column=1, rowspan=2, padx=(0, 10), sticky="e")

        if unclaimed:   # ← NUEVO
            btn_claim = ctk.CTkButton(
                frame, text="Reclamar", font=FONT_SMALL, width=80, height=26,
                fg_color=COLORS["accent"], hover_color="#16A34A",
                command=lambda b=bid: self._handle_claim(b),
            )
            btn_claim.grid(row=0, column=2, rowspan=2, padx=(0, 10), sticky="e")

        for w in (frame, lbl_name, lbl_info, dot):
            w.bind("<Button-1>", lambda e, b=bid: self._handle_select(b))

        self._row_frames[bid] = frame
        self._row_labels[bid] = lbl_info
        self._row_dots[bid] = dot

    def _handle_claim(self, board_id: str) -> None:   # ← NUEVO
        if self._on_claim:
            self._on_claim(board_id)

    def _handle_select(self, board_id: str) -> None:
        self._select_board(board_id)
        if self._on_select:
            self._on_select(board_id)

    def _select_board(self, board_id: str) -> None:
        self._selected_id = board_id
        for bid, frame in self._row_frames.items():
            frame.configure(
                border_color=COLORS["accent"] if bid == board_id else "#3F3F3F"
            )

    @staticmethod
    def _conn_icon(conn: str) -> str:
        icons = {
            "usb": "🔌",
            "bluetooth": "📡",
            "wifi": "📶",
        }
        return icons.get(conn, "❓")