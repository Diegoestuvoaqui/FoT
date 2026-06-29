# controller/board_controller.py
import logging

from domain.boards import Board
from service.board_service import BoardService

logger = logging.getLogger(__name__)


class BoardController:
    def __init__(self, board_service: BoardService):
        self._service = board_service
        self._on_board_updated = None
        # ← CORREGIDO: NO registrar observer aquí, se hace en set_ui_callback

    def set_ui_callback(self, callback):
        self._on_board_updated = callback
        self._service.add_observer(self._on_service_board_changed)  # ← MOVIDO aquí

    def _on_service_board_changed(self, board: Board):
        if self._on_board_updated:
            self._on_board_updated(board)

    def register_usb_board(self, board_id: str, port: str) -> Board:
        return self._service.register_board(board_id, port, "usb")

    def register_bluetooth_board(self, board_id: str, port: str) -> Board:
        return self._service.register_board(board_id, port, "bluetooth")

    def connect(self, board_id: str) -> tuple[bool, str]:
        return self._service.connect_board(board_id)

    def disconnect(self, board_id: str) -> None:
        self._service.disconnect_board(board_id)

    def remove(self, board_id: str) -> None:
        self._service.remove_board(board_id)

    def get_boards(self) -> list[Board]:
        return self._service.get_boards()

    def get_board(self, board_id: str) -> Board | None:
        return self._service.get_board(board_id)

    def get_boards_by_sketch(self, sketch_id: str) -> list[Board]:
        return self._service.get_boards_by_sketch(sketch_id)

    def is_connected(self, board_id: str) -> bool:
        return self._service.is_connected(board_id)

    def read_now(self, board_id: str) -> bool:
        return self._service.request_read(board_id)

    def cleanup(self):
        if self._on_board_updated:
            self._service.remove_observer()