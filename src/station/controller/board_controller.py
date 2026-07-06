# controller/board_controller.py
import logging

from domain.boards import Board
from service.board_service import BoardService

logger = logging.getLogger(__name__)


class BoardController:
    def __init__(self, board_service: BoardService):
        self._service = board_service
        self._on_board_updated = None

    def set_ui_callback(self, callback):
        self._on_board_updated = callback
        self._service.add_observer(self._on_service_board_changed)

    def _on_service_board_changed(self, board: Board):
        if self._on_board_updated:
            self._on_board_updated(board)

    def register_usb_board(self, board_id: str, port: str) -> Board:
        return self._service.register_board(board_id, port, "usb")

    def register_bluetooth_board(self, board_id: str, port: str) -> Board:
        return self._service.register_board(board_id, port, "bluetooth")

    def register_wifi_board(self, board_id: str, ip: str) -> Board:
        return self._service.register_wifi_board(board_id, ip)

    def connect(self, board_id: str) -> tuple[bool, str]:
        return self._service.connect_board(board_id)

    def disconnect(self, board_id: str) -> None:
        self._service.disconnect_board(board_id)

    def remove(self, board_id: str) -> None:
        self._service.remove_board(board_id)

    def get_boards(self) -> list[Board]:
        return self._service.get_boards()

    def get_boards_by_panel(self, panel_key: str) -> list[Board]:
        return self._service.get_boards_by_panel(panel_key)

    def board_belongs_to_panel(self, board_id: str, panel_key: str) -> bool:
        return self._service.board_belongs_to_panel(board_id, panel_key)

    def get_board(self, board_id: str) -> Board | None:
        return self._service.get_board(board_id)

    def get_boards_by_sketch(self, sketch_id: str) -> list[Board]:
        return self._service.get_boards_by_sketch(sketch_id)

    def is_connected(self, board_id: str) -> bool:
        return self._service.is_connected(board_id)

    def read_now(self, board_id: str) -> bool:
        return self._service.request_read(board_id)

    def identify_now(self, board_id: str) -> bool:
        return self._service.request_identify(board_id)

    def get_readings(self, board_id: str, sensor_type: str | None = None,
                     limit: int = 100, start=None, end=None) -> list[dict]:
        return self._service.get_readings(board_id, sensor_type, limit, start, end)

    def cleanup(self):
        if self._on_board_updated:
            self._service.remove_observer(self._on_service_board_changed)
            self._on_board_updated = None

    def on_sensor_identify(self, board_id: str, data: dict) -> None:
        self._service.on_sensor_identify(board_id, data)
