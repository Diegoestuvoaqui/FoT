# service/board_service.py
import logging
from typing import Callable, Optional

from data.database import Database
from domain.boards import Board
from logic.sensor_manager import SensorManager
from data.database import Database

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
        self._observers: list[Callable[[Board], None]] = []
        self._sketch_panel_map: dict[str, str | None] = {}
        self._load_sketch_catalog()

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
            if usuario_id is not None:
                board.usuario_id = usuario_id
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
            board.last_seen = self._now()
            self._persist_board(board)
            self._notify_change(board)
            return True, ""
        else:
            board.status = "Error de conexión"
            self._persist_board(board)
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
        """Elimina una placa del sistema (DB + memoria)."""
        self._boards.pop(board_id, None)
        self._sensor_mgr.disconnect(board_id)
        try:
            self._db.delete_board(board_id)
            logger.info("Placa eliminada: %s", board_id)
        except Exception as e:
            logger.error("Error eliminando placa %s de DB: %s", board_id, e)

    # ------------------------------------------------------------------
    # Gestión de estado físico
    # ------------------------------------------------------------------

    def mark_board_disconnected(self, board_id: str, reason: str = "Puerto no disponible") -> None:
        """← NUEVO: Marca una placa como desconectada físicamente."""
        board = self._boards.get(board_id)
        if not board:
            return

        # Solo actualizar si estaba conectada o detectada
        if board.status in ("Conectada", "Detectada"):
            logger.info("Marcando placa %s como desconectada: %s", board_id, reason)
            board.status = "Desconectada"
            self._sensor_mgr.disconnect(board_id)
            self._persist_board(board)
            self._notify_change(board)

    def update_board_from_scanner(self, board_id: str, port_data: dict, is_connected: bool) -> None:
        """← NUEVO: Actualiza estado de placa basado en escáner USB."""
        board = self._boards.get(board_id)
        if board:
            if is_connected:
                # Actualizar datos de fábrica si están disponibles
                if port_data:
                    board.hwid = port_data.get("hwid")
                    board.vid = port_data.get("vid")
                    board.pid = port_data.get("pid")
                    board.serial_number = port_data.get("serial_number")
                    board.manufacturer = port_data.get("manufacturer")
                    board.product = port_data.get("product")
                    board.location = port_data.get("location")
                # Si estaba desconectada, marcar como detectada
                if board.status == "Desconectada":
                    board.status = "Detectada"
                    self._persist_board(board)
                    self._notify_change(board)
            else:
                # Puerto desapareció
                self.mark_board_disconnected(board_id, "Puerto físico desconectado")
        else:
            # Placa nueva detectada
            if is_connected and port_data:
                self.register_board(
                    board_id=board_id,
                    port=port_data["device"],
                    conn_type="usb",
                    factory_data=port_data
                )

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------

    def get_board(self, board_id: str) -> Optional[Board]:
        return self._boards.get(board_id)

    def get_boards(self) -> list[Board]:
        return list(self._boards.values())

    def get_boards_by_sketch(self, sketch_id: str) -> list[Board]:
        return [b for b in self._boards.values() if b.sketch_id == sketch_id]

    def get_boards_by_panel(self, panel_key: str) -> list[Board]:
        """Retorna placas cuyo sketch_id está asociado a panel_key en el catálogo."""
        return [
            b for b in self._boards.values()
            if b.sketch_id and self._sketch_panel_map.get(b.sketch_id) == panel_key
        ]

    def board_belongs_to_panel(self, board_id: str, panel_key: str) -> bool:
        board = self._boards.get(board_id)
        if not board or not board.sketch_id:
            return False
        return self._sketch_panel_map.get(board.sketch_id) == panel_key

    def is_connected(self, board_id: str) -> bool:
        return self._sensor_mgr.is_connected(board_id)

    # ------------------------------------------------------------------
    # Comandos
    # ------------------------------------------------------------------

    def request_read(self, board_id: str) -> bool:
        return self._sensor_mgr.request_read(board_id)

    def request_identify(self, board_id: str) -> bool:
        return self._sensor_mgr.request_identify(board_id)

    def get_readings(self, board_id: str, sensor_type: str | None = None,
                     limit: int = 100, start=None, end=None) -> list[dict]:
        return self._db.get_readings(board_id, sensor_type, limit, start, end)


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

        # Registrar el sketch en el catálogo si es nuevo
        if board.sketch_id and board.sketch_id not in self._sketch_panel_map:
            self._db.upsert_sketch(board.sketch_id, board.sketch_name or "")
            self._sketch_panel_map[board.sketch_id] = None
            logger.info("Sketch nuevo registrado en catálogo sin panel asignado: %s", board.sketch_id)


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

    def _load_sketch_catalog(self) -> None:
        """Carga el catálogo de sketches (sketch_id -> panel_key) desde la DB."""
        try:
            sketches = self._db.get_all_sketches()
            self._sketch_panel_map = {s["sketch_id"]: s.get("panel_key") for s in sketches}
        except Exception as e:
            logger.error("Error cargando catálogo de sketches: %s", e)
            self._sketch_panel_map = {}



    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _now() -> str:
        from datetime import datetime
        return datetime.now().isoformat()

    # ------------------------------------------------------------------
    # Observadores (lista, como EventService)
    # ------------------------------------------------------------------

    def add_observer(self, callback: Callable[[Board], None]) -> None:
        if callback not in self._observers:
            self._observers.append(callback)

    def remove_observer(self, callback: Callable[[Board], None]) -> None:
        if callback in self._observers:
            self._observers.remove(callback)

    def _notify_change(self, board: Board) -> None:
        for observer in self._observers:
            try:
                observer(board)
            except Exception as e:
                logger.error("Error en observer: %s", e)

    def stop(self) -> None:
        self._sensor_mgr.disconnect_all()
        self._boards.clear()
        self._observers.clear()