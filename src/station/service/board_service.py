# service/board_service.py
import logging
from typing import Callable, Optional

from data.database import Database
from domain.boards import Board
from logic.sensor_manager import SensorManager

logger = logging.getLogger(__name__)


class BoardService:
    def __init__(self,
                 db: Database,
                 sensor_manager: SensorManager,
                 on_board_changed: Optional[Callable[[Board], None]] = None):
        self._db = db
        self._sensor_mgr = sensor_manager
        self._on_board_changed = on_board_changed
        self._boards: dict[str, Board] = {}

    # ------------------------------------------------------------------
    # Registro
    # ------------------------------------------------------------------

    def register_board(self,
                       board_id: str,
                       port: str,
                       conn_type: str = "usb",
                       usuario_id: Optional[int] = None,
                       factory_data: Optional[dict] = None) -> Board:
        """Registra o actualiza una placa en el sistema."""
        board = self._boards.get(board_id)
        if board:
            board.port = port
            board.conn = conn_type
            board.status = "Detectada"
            if factory_data:
                board.hwid = factory_data.get("hwid")
                board.vid = factory_data.get("vid")
                board.pid = factory_data.get("pid")
                board.serial_number = factory_data.get("serial_number")
                board.manufacturer = factory_data.get("manufacturer")
                board.product = factory_data.get("product")
                board.location = factory_data.get("location")
        else:
            board = Board(
                board_id=board_id,
                conn=conn_type,
                status="Detectada",
                usuario_id=usuario_id,
                port=port,
                hwid=factory_data.get("hwid") if factory_data else None,
                vid=factory_data.get("vid") if factory_data else None,
                pid=factory_data.get("pid") if factory_data else None,
                serial_number=factory_data.get("serial_number") if factory_data else None,
                manufacturer=factory_data.get("manufacturer") if factory_data else None,
                product=factory_data.get("product") if factory_data else None,
                location=factory_data.get("location") if factory_data else None,
            )
            self._boards[board_id] = board

        self._persist_board(board)
        self._notify_change(board)
        return board

    def register_bluetooth_board(self, board_id: str, port: str, usuario_id: Optional[int] = None) -> Board:
        return self.register_board(board_id, port, "bluetooth", usuario_id)

    def register_wifi_board(self, board_id: str, ip: str, usuario_id: Optional[int] = None) -> Board:
        return self.register_board(board_id, ip, "wifi", usuario_id)

    # ------------------------------------------------------------------
    # Conexión
    # ------------------------------------------------------------------

    def connect_board(self, board_id: str) -> tuple[bool, str]:
        board = self._boards.get(board_id)
        if not board:
            return False, "Placa no registrada"

        if board.conn == "usb":
            if not board.port:
                return False, "Placa sin puerto asignado"
            ok = self._sensor_mgr.connect_usb(board.port, board_id)
        elif board.conn == "bluetooth":
            if not board.port:
                return False, "Placa sin puerto asignado"
            ok = self._sensor_mgr.connect_bluetooth(board.port, board_id)
        elif board.conn == "wifi":
            ok = self._sensor_mgr.connect_wifi(board_id, board.port or "localhost")
        else:
            return False, f"Tipo de conexión desconocido: {board.conn}"

        if ok:
            board.status = "Conectada"
            self._persist_board(board)
            self._notify_change(board)
            return True, ""
        else:
            board.status = "Error de conexión"
            self._notify_change(board)
            return False, f"No se pudo conectar a {board.port or board_id}"

    def disconnect_board(self, board_id: str) -> None:
        board = self._boards.get(board_id)
        if not board:
            return
        self._sensor_mgr.disconnect(board_id)
        board.status = "Desconectada"
        self._persist_board(board)
        self._notify_change(board)

    def remove_board(self, board_id: str) -> None:
        self._boards.pop(board_id, None)
        self._sensor_mgr.disconnect(board_id)
        self._db.delete_board(board_id)

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------

    def get_board(self, board_id: str) -> Optional[Board]:
        return self._boards.get(board_id)

    def get_boards(self) -> list[Board]:
        return list(self._boards.values())

    def get_boards_by_sketch(self, sketch_id: str) -> list[Board]:
        return [b for b in self._boards.values() if b.sketch_id == sketch_id]

    def is_connected(self, board_id: str) -> bool:
        return self._sensor_mgr.is_connected(board_id)

    # ------------------------------------------------------------------
    # Comandos
    # ------------------------------------------------------------------

    def request_read(self, board_id: str) -> bool:
        return self._sensor_mgr.request_read(board_id)

    def set_interval(self, board_id: str, ms: int) -> bool:
        return self._sensor_mgr.set_interval(board_id, ms)

    # ------------------------------------------------------------------
    # Callbacks del sensor
    # ------------------------------------------------------------------

    def on_sensor_identify(self, board_id: str, data: dict) -> None:
        board = self._boards.get(board_id)
        if not board:
            return
        board.sketch_id = data.get("sketch")
        board.sketch_name = data.get("name")
        board.sketch_version = data.get("version")
        self._persist_board(board)
        self._notify_change(board)

    # ------------------------------------------------------------------
    # Persistencia
    # ------------------------------------------------------------------

    def _persist_board(self, board: Board) -> None:
        try:
            self._db.save_board({
                "id": board.id,
                "usuario_id": board.usuario_id,
                "conn": board.conn,
                "port": board.port,
                "sketch_id": board.sketch_id,
                "sketch_name": board.sketch_name,
                "sketch_version": board.sketch_version,
                "status": board.status,
                "last_seen": board.last_seen,
                "hwid": board.hwid,
                "vid": board.vid,
                "pid": board.pid,
                "serial_number": board.serial_number,
                "manufacturer": board.manufacturer,
                "product": board.product,
                "location": board.location,
            })
        except Exception as e:
            logger.error("Error persistiendo board %s: %s", board.id, e)

    def load_from_db(self) -> None:
        rows = self._db.get_all_boards()
        for row in rows:
            board = Board(
                board_id=row["id"],
                conn=row.get("conn", "usb"),
                status=row.get("status", "Desconocida"),
                usuario_id=row.get("usuario_id"),
                sketch_id=row.get("sketch_id"),
                sketch_name=row.get("sketch_name"),
                sketch_version=row.get("sketch_version"),
                port=row.get("port", ""),
                last_seen=row.get("last_seen"),
                hwid=row.get("hwid"),
                vid=row.get("vid"),
                pid=row.get("pid"),
                serial_number=row.get("serial_number"),
                manufacturer=row.get("manufacturer"),
                product=row.get("product"),
                location=row.get("location"),
            )
            self._boards[board.id] = board

    # ------------------------------------------------------------------
    # Observadores
    # ------------------------------------------------------------------

    def add_observer(self, callback: Callable[[Board], None]) -> None:
        self._on_board_changed = callback

    def remove_observer(self) -> None:
        self._on_board_changed = None

    def _notify_change(self, board: Board) -> None:
        if self._on_board_changed:
            try:
                self._on_board_changed(board)
            except Exception as e:
                logger.error("Error en observer: %s", e)

    def stop(self) -> None:
        self._sensor_mgr.disconnect_all()
        self._boards.clear()