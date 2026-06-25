# service/board_service.py
import logging

from domain.boards import Board
from logic.device_scanner import USBScanner
from logic.serial_bridge import SerialBridge

logger = logging.getLogger(__name__)


class BoardService:
    """
    Gestiona el ciclo de vida de las placas Arduino:
    - Descubrimiento USB (conexión/desconexión)
    - Serial bridges (abrir, cerrar, leer)
    - Asignación de placas a parcelas
    - Resolución de bridge activo para una parcela
    """

    def __init__(self, mqtt_bus, data_receiver):
        self._mqtt_bus = mqtt_bus
        self._data_receiver = data_receiver

        self._boards: list[Board] = []
        self._serial_bridges: dict[str, SerialBridge] = {}
        self._parcela_to_board: dict[str, str] = {}

        self._board_observers: list = []
        self._data_observers: list = []

        self._usb_scanner = USBScanner(
            on_new_board=self._on_usb_new_board,
            on_remove_board=self._on_usb_remove_board,
            interval=3,
        )
        self._usb_scanner.start()

    # ------------------------------------------------------------------
    # Observadores
    # ------------------------------------------------------------------
    def add_board_observer(self, callback):
        self._board_observers.append(callback)

    def remove_board_observer(self, callback):
        self._board_observers.remove(callback)

    def add_data_observer(self, callback):
        self._data_observers.append(callback)

    def remove_data_observer(self, callback):
        self._data_observers.remove(callback)

    def _notify_board(self, board: Board):
        for obs in self._board_observers:
            obs(board)

    def _notify_data(self, topic: str, data: dict):
        for obs in self._data_observers:
            obs(topic, data)

    # ------------------------------------------------------------------
    # USB
    # ------------------------------------------------------------------
    def _on_usb_new_board(self, port):
        board_id = port.serial_number or port.device
        if any(b.id == board_id for b in self._boards):
            return

        board = Board(
            board_id=board_id,
            conn="usb",
            status="Conectada",
            port=port.device,
        )
        self._boards.append(board)
        self._notify_board(board)
        self._start_serial_bridge(port.device)

    def _on_usb_remove_board(self, device):
        board = next((b for b in self._boards if b.id == device), None)
        if board:
            board.status = "Desconectada"
            self._notify_board(board)
        self._stop_serial_bridge(device)

    # ------------------------------------------------------------------
    # Serial bridges
    # ------------------------------------------------------------------
    def _start_serial_bridge(self, port: str, baud: int = 9600):
        def on_serial_message(data: dict):
            board = next((b for b in self._boards if b.port == port), None)
            parcela_id = board.parcela if board else None

            if parcela_id:
                topic = f"fot/{parcela_id}/sensores"
                self._notify_data(topic, data)
                self._data_receiver.on_event(topic, data)
            else:
                logger.info(
                    "Dato serial sin parcela asignada (puerto %s): %s",
                    port, data
                )

        bridge = SerialBridge(port, baud, on_message=on_serial_message)
        if bridge.connect():
            self._serial_bridges[port] = bridge
            return bridge
        return None

    def _stop_serial_bridge(self, port: str):
        bridge = self._serial_bridges.pop(port, None)
        if bridge:
            bridge.disconnect()

    # ------------------------------------------------------------------
    # Asignación / Desasignación
    # ------------------------------------------------------------------
    def assign_board(self, board_id: str, parcela_id: str) -> None:
        board = next((b for b in self._boards if b.id == board_id), None)
        if not board:
            raise ValueError(f"Placa {board_id} no encontrada")

        old_board_id = self._parcela_to_board.get(parcela_id)
        if old_board_id and old_board_id != board_id:
            old_board = next((b for b in self._boards if b.id == old_board_id), None)
            if old_board:
                old_board.parcela = None
                self._notify_board(old_board)

        board.parcela = parcela_id
        self._parcela_to_board[parcela_id] = board_id
        self._notify_board(board)

    def unassign_board(self, board_id: str) -> None:
        board = next((b for b in self._boards if b.id == board_id), None)
        if not board:
            raise ValueError(f"Placa {board_id} no encontrada")

        if board.parcela and board.parcela in self._parcela_to_board:
            del self._parcela_to_board[board.parcela]

        board.parcela = None
        self._notify_board(board)

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------
    def get_boards(self) -> list[Board]:
        return list(self._boards)

    def get_board(self, board_id: str) -> Board | None:
        return next((b for b in self._boards if b.id == board_id), None)

    def get_bridge_for_parcela(self, parcela_id: str) -> SerialBridge | None:
        board_id = self._parcela_to_board.get(parcela_id)
        if not board_id:
            return None
        board = next((b for b in self._boards if b.id == board_id), None)
        if not board or not board.port:
            return None
        return self._serial_bridges.get(board.port)

    def get_assigned_parcela(self, board_id: str) -> str | None:
        board = self.get_board(board_id)
        return board.parcela if board else None

    def is_parcela_connected(self, parcela_id: str) -> bool:
        return self.get_bridge_for_parcela(parcela_id) is not None

    # ------------------------------------------------------------------
    # Firmware
    # ------------------------------------------------------------------
    def get_firmware_version(self, board_id: str) -> str:
        board = self.get_board(board_id)
        return board.firmware_version if board and board.firmware_version else "Desconocida"

    # ------------------------------------------------------------------
    # Cierre limpio
    # ------------------------------------------------------------------
    def stop(self):
        self._usb_scanner.stop()
        for port in list(self._serial_bridges.keys()):
            self._stop_serial_bridge(port)
