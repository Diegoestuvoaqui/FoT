# service/board_service.py
import logging
import threading
import time
from typing import Callable, Optional

from data.database import Database
from domain.boards import Board
from logic.sensor_manager import SensorManager

logger = logging.getLogger(__name__)


class BoardService:
    RELAY_ACK_TIMEOUT_S = 5.0
    RELAY_RATE_LIMIT_S = 1.0

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

        # Fase 5: estado de relé
        self._relay_seq: dict[str, int] = {}
        self._pending_acks: dict[str, dict] = {}
        self._last_relay_cmd: dict[str, float] = {}

        self._load_sketch_catalog()

    # ==================================================================
    # Registro
    # ==================================================================
    def register_board(self,
                       board_id: str,
                       port: str,
                       conn_type: str = "usb",
                       factory_data: Optional[dict] = None) -> Board:
        board = self._boards.get(board_id)
        if board:
            board.port = port
            board.conn = conn_type
            board.last_seen = self._now()
            if factory_data:
                for f in ("hwid", "vid", "pid", "serial_number",
                          "manufacturer", "product", "location"):
                    setattr(board, f, factory_data.get(f))
            board.on_physical_detected()
        else:
            existing = self._db.get_board_by_id(board_id)
            board = Board(
                board_id=board_id,
                conn=conn_type,
                status="Sin asignar",
                usuario_id=existing["usuario_id"] if existing else None,
                port=port,
                last_seen=self._now(),
                hwid=factory_data.get("hwid") if factory_data else None,
                vid=factory_data.get("vid") if factory_data else None,
                pid=factory_data.get("pid") if factory_data else None,
                serial_number=factory_data.get("serial_number") if factory_data else None,
                manufacturer=factory_data.get("manufacturer") if factory_data else None,
                product=factory_data.get("product") if factory_data else None,
                location=factory_data.get("location") if factory_data else None,
                hw_model=existing.get("hw_model") if existing else None,
                mac=existing.get("mac") if existing else None,
                ip=existing.get("ip") if existing else None,
                fw_version=existing.get("fw_version") if existing else None,
                rssi=existing.get("rssi") if existing else None,
                uptime_s=existing.get("uptime_s") if existing else None,
                power_mode=existing.get("power_mode") if existing else None,
                interval_ms=existing.get("interval_ms") if existing else None,
            )
            board.on_physical_detected()
            self._boards[board_id] = board
            self._reload_relays(board)

        self._persist_board(board)
        self._notify_change(board)
        return board

    def register_bluetooth_board(self, board_id: str, port: str,
                                 usuario_id: Optional[int] = None) -> Board:
        return self.register_board(board_id, port, "bluetooth", usuario_id)

    def register_wifi_board(self, board_id: str, ip: str = "",
                            usuario_id: Optional[int] = None) -> Board:
        board = self.register_board(board_id, port="", conn_type="wifi",
                                    factory_data=None)
        if ip and board.ip != ip:
            board.ip = ip
            self._persist_board(board)
        return board

    def get_boards_by_user(self, usuario_id: int) -> list[Board]:
        return [b for b in self._boards.values() if b.usuario_id == usuario_id]

    # ==================================================================
    # Conexión
    # ==================================================================
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
            ok = self._sensor_mgr.ensure_wifi_bridge(board_id)
        else:
            return False, f"Tipo de conexión desconocido: {board.conn}"

        if ok:
            board.status = "Detectada" if board.conn == "wifi" else "Conectada"
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

    # ==================================================================
    # Callbacks de ingesta
    # ==================================================================
    def on_board_reading(self, board_id: str) -> None:
        board = self._boards.get(board_id)
        if board is None:
            return
        board.last_seen = self._now()
        if board.mark_alive():
            self._persist_board(board)
            self._notify_change(board)

    def on_board_state(self, board_id: str, data: dict) -> None:
        board = self._boards.get(board_id)
        if board is None:
            return
        changed = False
        for attr in ("hw_model", "mac", "ip", "fw_version", "power_mode"):
            val = data.get(attr)
            if val is not None and getattr(board, attr) != val:
                setattr(board, attr, val)
                changed = True
        for attr in ("rssi", "uptime_s", "interval_ms"):
            val = data.get(attr)
            if val is not None and getattr(board, attr) != val:
                setattr(board, attr, val)
                changed = True
        status = data.get("status")
        if status == "offline":
            if board.on_physical_lost():
                changed = True
        elif status == "online" or data.get("boot"):
            if board.mark_alive():
                changed = True
        board.last_seen = self._now()
        self._persist_board(board)
        if changed:
            self._notify_change(board)

    def on_sensor_identify(self, board_id: str, data: dict) -> None:
        board = self._boards.get(board_id)
        if not board:
            return
        board.sketch_id = data.get("sketch") or board.sketch_id
        board.sketch_name = data.get("name") or board.sketch_name
        board.sketch_version = data.get("version") or board.sketch_version
        if data.get("hw"):
            board.hw_model = data["hw"]
        if data.get("mac"):
            board.mac = data["mac"]
        if data.get("ip"):
            board.ip = data["ip"]
        board.mark_alive()
        self._persist_board(board)

        # Crear actuador si el nodo reporta >0
        if int(data.get("actuators", 0)) > 0:
            try:
                self._db.upsert_actuator(
                    board_id, "relay1", kind="relay",
                    label="Relé 1",
                    pin=str(data.get("relay_pin", "GPIO26")),
                )
            except Exception as e:
                logger.error("Error creando actuador en %s: %s", board_id, e)
        self._reload_relays(board)

        if board.sketch_id and board.sketch_id not in self._sketch_panel_map:
            self._db.upsert_sketch(board.sketch_id, board.sketch_name or "")
            self._sketch_panel_map[board.sketch_id] = None

        self._notify_change(board)

    # ==================================================================
    # Relé
    # ==================================================================
    def set_relay(self, actor, board_id: str, state: bool,
                  actuator_id: str = "relay1") -> tuple[bool, str]:
        """Solo dueño o admin, placa online, 1 cambio/s, con ack timeout."""
        board = self._boards.get(board_id)
        if board is None:
            return False, "Placa no registrada"

        is_owner = board.usuario_id is not None and board.usuario_id == actor.id
        if not (is_owner or actor.is_admin()):
            return False, "Sin permiso para controlar esta placa"

        if not self._sensor_mgr.is_connected(board_id):
            return False, "La placa no está en línea"

        now = time.time()
        last = self._last_relay_cmd.get(board_id, 0.0)
        if now - last < self.RELAY_RATE_LIMIT_S:
            return False, "Espera un segundo entre comandos"
        self._last_relay_cmd[board_id] = now

        seq = self._relay_seq.get(board_id, 0) + 1
        self._relay_seq[board_id] = seq

        try:
            event_id = self._db.save_relay_event(
                board_id=board_id,
                actuator_id=actuator_id,
                state=state,
                source="ui",
                usuario_id=actor.id,
                seq=seq,
            )
        except Exception as e:
            logger.error("Error guardando relay_event: %s", e)
            return False, "Error guardando evento de relé"

        self._db.set_actuator_desired(board_id, actuator_id, state)

        ok = self._sensor_mgr.set_relay(board_id, actuator_id, state, seq)
        if not ok:
            logger.warning("Fallo enviando comando de relé a %s", board_id)
            # rollback desired
            old = self._db.get_actuators(board_id)
            old_state = next(
                (a.get("reported_state", 0) for a in old
                 if a["actuator_id"] == actuator_id), 0)
            self._db.set_actuator_desired(
                board_id, actuator_id, bool(old_state))
            self._reload_relays(board)
            self._notify_change(board)
            return False, "No se pudo enviar el comando al nodo"

        self._schedule_ack_timeout(board_id, event_id)

        self._reload_relays(board)
        self._notify_change(board)
        return True, ""

    def on_relay_ack(self, board_id: str, data: dict) -> None:
        if data.get("ack") != "relay":
            return
        if data.get("id") != "relay1":
            return
        state = bool(data.get("state", 0))
        seq = data.get("seq", 0)

        info = self._pending_acks.pop(board_id, None)
        if info and info.get("timer"):
            info["timer"].cancel()
            try:
                self._db.ack_relay_event(info["event_id"])
            except Exception as e:
                logger.error("Error marcando ack: %s", e)

        try:
            self._db.set_actuator_reported(
                board_id, "relay1", state, ts=int(time.time()))
        except Exception as e:
            logger.error("Error guardando reported_state: %s", e)

        logger.info("Relay ack %s: state=%s seq=%s", board_id, state, seq)

        board = self._boards.get(board_id)
        if board is not None:
            board.mark_alive()
            self._reload_relays(board)
            self._notify_change(board)

    def _schedule_ack_timeout(self, board_id: str, event_id: int) -> None:
        old = self._pending_acks.pop(board_id, None)
        if old and old.get("timer"):
            old["timer"].cancel()

        def on_timeout():
            info = self._pending_acks.pop(board_id, None)
            if info is None:
                return
            logger.warning(
                "Relay ack timeout %s (event %s)", board_id, event_id)
            board = self._boards.get(board_id)
            if board is not None:
                self._reload_relays(board)
                self._notify_change(board)

        timer = threading.Timer(self.RELAY_ACK_TIMEOUT_S, on_timeout)
        timer.daemon = True
        timer.start()
        self._pending_acks[board_id] = {
            "event_id": event_id, "timer": timer}

    def _reload_relays(self, board: Board) -> None:
        try:
            board.relays = self._db.get_actuators(board.id)
        except Exception as e:
            logger.error("Error cargando relays de %s: %s", board.id, e)

    # ==================================================================
    # Eliminación / asignación
    # ==================================================================
    def remove_board(self, board_id: str) -> None:
        self._boards.pop(board_id, None)
        self._sensor_mgr.disconnect(board_id)
        try:
            self._db.delete_board(board_id)
        except Exception as e:
            logger.error("Error eliminando %s: %s", board_id, e)

    def unassign_board(self, board_id: str, usuario_id: int) -> None:
        board = self._boards.get(board_id)
        if not board:
            return
        if board.usuario_id != usuario_id:
            raise PermissionError("No es tu placa")
        board.usuario_id = None
        board.status = "Sin asignar"
        self._persist_board(board)
        self._notify_change(board)

    def claim_board(self, board_id: str, usuario_id: int) -> Board:
        board = self._boards.get(board_id)
        if not board:
            raise ValueError("Placa no encontrada")
        board.claim(usuario_id)
        self._persist_board(board)
        self._notify_change(board)
        return board

    def admin_reassign_board(self, board_id: str,
                             new_usuario_id: Optional[int]) -> Board:
        board = self._boards.get(board_id)
        if not board:
            raise ValueError("Placa no encontrada")
        if new_usuario_id is None:
            board.release()
        else:
            board.usuario_id = new_usuario_id
            if board.status == "Sin asignar":
                board.status = "Detectada"
        self._persist_board(board)
        self._notify_change(board)
        return board

    def delete_board_permanently(self, board_id: str) -> None:
        self._boards.pop(board_id, None)
        self._sensor_mgr.disconnect(board_id)
        try:
            self._db.delete_board(board_id)
        except Exception as e:
            logger.error("Error eliminando %s: %s", board_id, e)

    # ==================================================================
    # Estado físico
    # ==================================================================
    def mark_board_disconnected(self, board_id: str,
                                reason: str = "Puerto no disponible") -> None:
        board = self._boards.get(board_id)
        if not board:
            return
        logger.info("Marcando %s desconectada: %s", board_id, reason)
        self._sensor_mgr.disconnect(board_id)
        if board.on_physical_lost():
            self._persist_board(board)
            self._notify_change(board)

    def update_board_from_scanner(self, board_id: str, port_data: dict,
                                  is_connected: bool) -> None:
        board = self._boards.get(board_id)
        if board:
            if is_connected:
                if port_data:
                    for f in ("hwid", "vid", "pid", "serial_number",
                              "manufacturer", "product", "location"):
                        setattr(board, f, port_data.get(f))
                board.last_seen = self._now()
                changed = board.on_physical_detected()
                self._persist_board(board)
                if changed:
                    self._notify_change(board)
            else:
                self.mark_board_disconnected(
                    board_id, "Puerto físico desconectado")
        else:
            if is_connected and port_data:
                self.register_board(
                    board_id=board_id,
                    port=port_data["device"],
                    conn_type="usb",
                    factory_data=port_data,
                )

    # ==================================================================
    # Consultas
    # ==================================================================
    def get_board(self, board_id: str) -> Optional[Board]:
        return self._boards.get(board_id)

    def get_boards(self) -> list[Board]:
        return list(self._boards.values())

    def get_boards_by_sketch(self, sketch_id: str) -> list[Board]:
        return [b for b in self._boards.values() if b.sketch_id == sketch_id]

    def get_boards_by_panel(self, panel_key: str) -> list[Board]:
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

    def request_read(self, board_id: str) -> bool:
        return self._sensor_mgr.request_read(board_id)

    def request_identify(self, board_id: str) -> bool:
        return self._sensor_mgr.request_identify(board_id)

    def get_readings(self, board_id: str, sensor_type: str | None = None,
                     limit: int = 100, start=None, end=None) -> list[dict]:
        return self._db.get_readings(board_id, sensor_type, limit, start, end)

    def get_boards_visible_to_user(self, usuario_id: int) -> list[Board]:
        return [
            b for b in self._boards.values()
            if b.usuario_id == usuario_id or b.usuario_id is None
        ]

    def set_interval(self, board_id: str, ms: int) -> bool:
        return self._sensor_mgr.set_interval(board_id, ms)

    def get_relays(self, board_id: str) -> list[dict]:
        board = self._boards.get(board_id)
        return list(board.relays) if board else []

    # ==================================================================
    # Persistencia
    # ==================================================================
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
                "hw_model": board.hw_model,
                "mac": board.mac,
                "ip": board.ip,
                "fw_version": board.fw_version,
                "rssi": board.rssi,
                "uptime_s": board.uptime_s,
                "power_mode": board.power_mode,
                "interval_ms": board.interval_ms,
                "approved": 0,
            })
        except Exception as e:
            logger.error("Error persistiendo board %s: %s", board.id, e)

    def load_from_db(self) -> None:
        rows = self._db.get_all_boards()
        for row in rows:
            board = Board(
                board_id=row["id"],
                conn=row.get("conn", "usb"),
                status="Desconectada",
                usuario_id=row.get("usuario_id"),
                sketch_id=row.get("sketch_id"),
                sketch_name=row.get("sketch_name"),
                sketch_version=row.get("sketch_version"),
                port=row.get("port") or "",
                last_seen=row.get("last_seen"),
                hwid=row.get("hwid"),
                vid=row.get("vid"),
                pid=row.get("pid"),
                serial_number=row.get("serial_number"),
                manufacturer=row.get("manufacturer"),
                product=row.get("product"),
                location=row.get("location"),
                hw_model=row.get("hw_model"),
                mac=row.get("mac"),
                ip=row.get("ip"),
                fw_version=row.get("fw_version"),
                rssi=row.get("rssi"),
                uptime_s=row.get("uptime_s"),
                power_mode=row.get("power_mode"),
                interval_ms=row.get("interval_ms"),
            )
            self._boards[board.id] = board
            self._reload_relays(board)

    def _load_sketch_catalog(self) -> None:
        try:
            sketches = self._db.get_all_sketches()
            self._sketch_panel_map = {
                s["sketch_id"]: s.get("panel_key") for s in sketches
            }
        except Exception as e:
            logger.error("Error cargando catálogo: %s", e)
            self._sketch_panel_map = {}

    @staticmethod
    def _now() -> str:
        from datetime import datetime
        return datetime.now().isoformat()

    # ==================================================================
    # Observers
    # ==================================================================
    def add_observer(self, callback: Callable[[Board], None]) -> None:
        if callback not in self._observers:
            self._observers.append(callback)
        for board in self._boards.values():
            try:
                callback(board)
            except Exception as e:
                logger.error("Error en replay observer: %s", e)

    def remove_observer(self, callback: Callable[[Board], None]) -> None:
        if callback in self._observers:
            self._observers.remove(callback)

    def _notify_change(self, board: Board) -> None:
        for observer in self._observers:
            try:
                observer(board)
            except Exception as e:
                logger.error("Error en observer: %s", e)

    def set_disconnect_callback(self, callback: Callable[[str], None]) -> None:
        self._sensor_mgr.add_disconnect_observer(callback)

    def check_wifi_timeouts(self) -> None:
        self._sensor_mgr.check_wifi_timeouts()

    def stop(self) -> None:
        """Detiene timers pendientes. No cierra el sensor_manager (lo hace main)."""
        for info in self._pending_acks.values():
            if info.get("timer"):
                info["timer"].cancel()
        self._pending_acks.clear()