# src/station/service/board_service.py
"""
Servicio de gestión de placas Arduino.
Integra detección USB/Bluetooth, conexión vía SensorManager,
y mantenimiento del catálogo de placas conocidas.
"""
from __future__ import annotations

import logging
from typing import Callable, Optional

from data.database import Database
from domain.boards import Board
from logic.sensor_manager import SensorManager

logger = logging.getLogger(__name__)


class BoardService:
    """
    Gestiona el ciclo de vida de las placas:
    - Detección y registro
    - Conexión/desconexión (USB/Bluetooth)
    - Identificación de sketch activo
    - Notificación a observers de cambios
    """

    def __init__(self,
                 db: Database,
                 sensor_manager: SensorManager,
                 on_board_changed: Optional[Callable[[Board], None]] = None):
        self._db = db
        self._sensor_mgr = sensor_manager
        self._on_board_changed = on_board_changed
        self._boards: dict[str, Board] = {}  # board_id -> Board

    # ------------------------------------------------------------------
    # Registro de placas
    # ------------------------------------------------------------------

    def register_board(self,
                       board_id: str,
                       port: str,
                       conn_type: str = "usb",
                       parcela_id: Optional[str] = None) -> Board:
        """
        Registra una placa detectada. Si ya existe, actualiza datos.
        conn_type: "usb" | "bluetooth"
        """
        board = self._boards.get(board_id)
        if board:
            board.port = port
            board.conn = conn_type
            board.status = "Detectada"
        else:
            board = Board(
                board_id=board_id,
                conn=conn_type,
                status="Detectada",
                parcela=parcela_id,
                port=port,
            )
            self._boards[board_id] = board

        # Persistir en BD
        self._persist_board(board)
        self._notify_change(board)
        return board

    def connect_board(self, board_id: str, parcela_id: str) -> tuple[bool, str]:
        """
        Conecta una placa a una parcela (vincula físicamente).
        """
        board = self._boards.get(board_id)
        if not board:
            return False, "Placa no registrada"

        if not board.port:
            return False, "Placa sin puerto asignado"

        # Conectar según tipo
        if board.conn == "usb":
            ok = self._sensor_mgr.connect_usb(board.port, parcela_id)
        elif board.conn == "bluetooth":
            ok = self._sensor_mgr.connect_bluetooth(board.port, parcela_id)
        else:
            return False, f"Tipo de conexión desconocido: {board.conn}"

        if ok:
            board.parcela = parcela_id
            board.status = "Conectada"
            self._persist_board(board)
            self._notify_change(board)
            return True, ""
        else:
            board.status = "Error de conexión"
            self._notify_change(board)
            return False, f"No se pudo conectar a {board.port}"

    def disconnect_board(self, board_id: str) -> None:
        """Desconecta una placa de su parcela."""
        board = self._boards.get(board_id)
        if not board:
            return

        if board.parcela:
            self._sensor_mgr.disconnect(board.parcela)
            board.parcela = None

        board.status = "Desconectada"
        self._persist_board(board)
        self._notify_change(board)

    def remove_board(self, board_id: str) -> None:
        """Elimina una placa del registro."""
        board = self._boards.pop(board_id, None)
        if board and board.parcela:
            self._sensor_mgr.disconnect(board.parcela)

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------

    def get_board(self, board_id: str) -> Optional[Board]:
        return self._boards.get(board_id)

    def get_boards(self) -> list[Board]:
        return list(self._boards.values())

    def get_board_for_parcela(self, parcela_id: str) -> Optional[Board]:
        for board in self._boards.values():
            if board.parcela == parcela_id:
                return board
        return None

    def is_connected(self, board_id: str) -> bool:
        board = self._boards.get(board_id)
        if not board or not board.parcela:
            return False
        return self._sensor_mgr.is_connected(board.parcela)

    # ------------------------------------------------------------------
    # Comandos a placa
    # ------------------------------------------------------------------

    def request_read(self, board_id: str) -> bool:
        """Solicita lectura inmediata al sensor."""
        board = self._boards.get(board_id)
        if not board or not board.parcela:
            return False
        return self._sensor_mgr.request_read(board.parcela)

    def set_interval(self, board_id: str, ms: int) -> bool:
        """Cambia intervalo de lectura."""
        board = self._boards.get(board_id)
        if not board or not board.parcela:
            return False
        return self._sensor_mgr.set_interval(board.parcela, ms)

    # ------------------------------------------------------------------
    # Callbacks desde SensorManager
    # ------------------------------------------------------------------

    def on_sensor_identify(self, parcela_id: str, data: dict) -> None:
        """Recibe identificación del sketch cuando se conecta."""
        board = self.get_board_for_parcela(parcela_id)
        if not board:
            return

        board.firmware_version = data.get("version")
        # Guardar metadatos del sketch para mostrar en UI
        board.conn_module = data.get("name", "Unknown")
        self._persist_board(board)
        self._notify_change(board)

    # ------------------------------------------------------------------
    # Persistencia
    # ------------------------------------------------------------------

    def _persist_board(self, board: Board) -> None:
        try:
            self._db.save_board({
                "id": board.id,
                "conn": board.conn,
                "port": board.port,
                "status": board.status,
                "parcela_id": board.parcela,
                "firmware_version": board.firmware_version,
                "last_seen": board.last_seen,
            })
        except Exception as e:
            logger.error("Error persistiendo board %s: %s", board.id, e)

    def load_from_db(self) -> None:
        """Carga placas registradas previamente."""
        rows = self._db.get_all_boards()
        for row in rows:
            board = Board(
                board_id=row["id"],
                conn=row.get("conn", "usb"),
                status=row.get("status", "Desconocida"),
                parcela=row.get("parcela_id"),
                port=row.get("port", ""),
                firmware_version=row.get("firmware_version"),
                last_seen=row.get("last_seen"),
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

    # ------------------------------------------------------------------
    # Cierre
    # ------------------------------------------------------------------

    def stop(self) -> None:
        self._sensor_mgr.disconnect_all()
        self._boards.clear()
