# controller/board_controller.py
import logging

from service.board_service import BoardService

logger = logging.getLogger(__name__)


class BoardController:
    def __init__(self, board_service: BoardService):
        self._service = board_service
        self._on_board_updated = None

        self._service.add_board_observer(self._on_service_board_changed)

    def set_ui_callback(self, callback):
        """La UI registra callback para ser notificada de cambios en placas."""
        self._on_board_updated = callback

    # ------------------------------------------------------------------
    # Callback interno
    # ------------------------------------------------------------------
    def _on_service_board_changed(self, board):
        if self._on_board_updated:
            self._on_board_updated(board)

    # ------------------------------------------------------------------
    # Asignación / Desasignación
    # ------------------------------------------------------------------
    def assign_board(self, board_id: str, parcela_id: str) -> tuple[bool, str]:
        try:
            self._service.assign_board(board_id, parcela_id)
            return True, ""
        except ValueError as e:
            logger.error("Error al asignar placa: %s", e)
            return False, str(e)

    def unassign_board(self, board_id: str) -> tuple[bool, str]:
        try:
            self._service.unassign_board(board_id)
            return True, ""
        except ValueError as e:
            logger.error("Error al desasignar placa: %s", e)
            return False, str(e)

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------
    def get_boards(self):
        return self._service.get_boards()

    def get_board(self, board_id: str):
        return self._service.get_board(board_id)

    def get_assigned_parcela(self, board_id: str) -> str | None:
        return self._service.get_assigned_parcela(board_id)

    # ------------------------------------------------------------------
    # Firmware
    # ------------------------------------------------------------------
    def get_firmware_info(self, board_id: str) -> dict | None:
        board = self._service.get_board(board_id)
        if not board:
            return None

        return {
            "board_id": board_id,
            "port": board.port,
            "current_version": self._service.get_firmware_version(board_id),
        }

    # ------------------------------------------------------------------
    # Cierre limpio
    # ------------------------------------------------------------------
    def cleanup(self):
        if self._on_board_updated:
            self._service.remove_board_observer(self._on_service_board_changed)
