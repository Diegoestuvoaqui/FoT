# src/station/logic/sensor_manager.py
"""
Gestor central de conexiones a sensores (USB, Bluetooth y WiFi).
Mantiene un registro de bridges activos y enruta lecturas.
"""
from __future__ import annotations

import logging
from typing import Callable, Optional

from logic.bluetooth_bridge import BluetoothBridge
from logic.serial_bridge import SerialBridge
from logic.wifi_bridge import WiFiBridge

logger = logging.getLogger(__name__)


class SensorManager:
    """
    Administra múltiples conexiones a placas Arduino.
    Soporta USB, Bluetooth y WiFi simultáneamente.

    Notifica lecturas, identificaciones y desconexiones mediante el
    patrón Observer: múltiples suscriptores pueden registrarse sin
    pisarse entre sí (a diferencia del antiguo esquema de un solo
    callback por evento, que causaba que el último en registrarse
    "ganara" y silenciara a los anteriores).
    """

    def __init__(self, mqtt_bus=None):
        self._bridges: dict[str, SerialBridge | WiFiBridge] = {}
        self._mqtt_bus = mqtt_bus

        # Listas de observers (patrón Observer, consistente con BoardService/EventService)
        self._reading_observers: list[Callable[[str, dict], None]] = []
        self._identify_observers: list[Callable[[str, dict], None]] = []
        self._disconnect_observers: list[Callable[[str], None]] = []

    # ------------------------------------------------------------------
    # Observers
    # ------------------------------------------------------------------

    def add_reading_observer(self, callback: Callable[[str, dict], None]) -> None:
        if callback not in self._reading_observers:
            self._reading_observers.append(callback)

    def remove_reading_observer(self, callback: Callable[[str, dict], None]) -> None:
        if callback in self._reading_observers:
            self._reading_observers.remove(callback)

    def add_identify_observer(self, callback: Callable[[str, dict], None]) -> None:
        if callback not in self._identify_observers:
            self._identify_observers.append(callback)

    def remove_identify_observer(self, callback: Callable[[str, dict], None]) -> None:
        if callback in self._identify_observers:
            self._identify_observers.remove(callback)

    def add_disconnect_observer(self, callback: Callable[[str], None]) -> None:
        if callback not in self._disconnect_observers:
            self._disconnect_observers.append(callback)

    def remove_disconnect_observer(self, callback: Callable[[str], None]) -> None:
        if callback in self._disconnect_observers:
            self._disconnect_observers.remove(callback)

    def _notify_reading(self, board_id: str, data: dict) -> None:
        for obs in self._reading_observers:
            try:
                obs(board_id, data)
            except Exception as e:
                logger.error("Error en observer de lectura: %s", e)

    def _notify_identify(self, board_id: str, data: dict) -> None:
        for obs in self._identify_observers:
            try:
                obs(board_id, data)
            except Exception as e:
                logger.error("Error en observer de identificación: %s", e)

    def _notify_disconnect(self, board_id: str) -> None:
        for obs in self._disconnect_observers:
            try:
                obs(board_id)
            except Exception as e:
                logger.error("Error en observer de desconexión: %s", e)

    # ------------------------------------------------------------------
    # Conexiones
    # ------------------------------------------------------------------

    def connect_usb(self, port: str, board_id: str) -> bool:
        if board_id in self._bridges:
            logger.warning("%s ya conectada", board_id)
            return False

        def on_read(data: dict):
            self._notify_reading(board_id, data)

        def on_resp(data: dict):
            if "sketch" in data:
                self._notify_identify(board_id, data)

        def on_disconnect():
            self._bridges.pop(board_id, None)
            self._notify_disconnect(board_id)

        bridge = SerialBridge(port=port, on_reading=on_read, on_command_response=on_resp, on_disconnect=on_disconnect)
        if bridge.connect():
            self._bridges[board_id] = bridge
            bridge.request_identify()
            return True
        return False

    def connect_bluetooth(self, port: str, board_id: str) -> bool:
        if board_id in self._bridges:
            return False

        def on_read(data: dict):
            self._notify_reading(board_id, data)

        def on_disconnect():
            self._bridges.pop(board_id, None)
            self._notify_disconnect(board_id)

        bridge = BluetoothBridge(port=port, on_reading=on_read, on_disconnect=on_disconnect)
        if bridge.connect():
            self._bridges[board_id] = bridge
            bridge.request_identify()
            return True
        return False

    def connect_wifi(self, board_id: str, broker_ip: str = "localhost", broker_port: int = 1883) -> bool:
        """
        Conecta una placa por WiFi (UNO R4).
        Crea un WiFiBridge que SOLO publica comandos.
        Los datos entrantes son manejados por MQTTDataDispatcher global.
        """
        if board_id in self._bridges:
            logger.warning("%s ya conectada por WiFi", board_id)
            return False

        if self._mqtt_bus is None:
            logger.error("No hay MQTTEventBus configurado para WiFi")
            return False

        def on_disconnect():
            self._bridges.pop(board_id, None)
            self._notify_disconnect(board_id)

        # WiFiBridge ya no necesita callbacks de lectura — el dispatcher global los maneja
        bridge = WiFiBridge(
            board_id=board_id,
            mqtt_bus=self._mqtt_bus,
            on_disconnect=on_disconnect,
            # on_command_response opcional si queremos manejar respuestas a comandos
        )
        if bridge.connect():
            self._bridges[board_id] = bridge
            logger.info("Placa %s lista para comandos WiFi (broker: %s:%d)", board_id, broker_ip, broker_port)
            return True
        return False

    # ------------------------------------------------------------------
    # Desconexión
    # ------------------------------------------------------------------

    def disconnect(self, board_id: str) -> None:
        bridge = self._bridges.pop(board_id, None)
        if bridge:
            bridge.disconnect()
            logger.info("%s desconectada", board_id)

    def disconnect_all(self) -> None:
        for board_id in list(self._bridges.keys()):
            self.disconnect(board_id)

    # ------------------------------------------------------------------
    # Comandos
    # ------------------------------------------------------------------

    def send_command(self, board_id: str, cmd: dict) -> bool:
        bridge = self._bridges.get(board_id)
        if not bridge:
            return False
        bridge.send_command(cmd)
        return True

    def request_read(self, board_id: str) -> bool:
        return self.send_command(board_id, {"cmd": "read"})

    def request_identify(self, board_id: str) -> bool:
        return self.send_command(board_id, {"cmd": "identify"})

    def set_interval(self, board_id: str, ms: int) -> bool:
        return self.send_command(board_id, {"cmd": "interval", "ms": ms})

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------

    def get_connected(self) -> list[str]:
        """Retorna IDs de placas conectadas por USB/Bluetooth/WiFi."""
        return list(self._bridges.keys())

    def is_connected(self, board_id: str) -> bool:
        bridge = self._bridges.get(board_id)
        return bridge is not None and bridge.is_connected()

    def get_bridge(self, board_id: str) -> SerialBridge | WiFiBridge | None:
        """Obtiene el bridge de una placa para operaciones avanzadas."""
        return self._bridges.get(board_id)

    def check_wifi_timeouts(self) -> None:
        """Verifica timeouts de bridges WiFi. Llamar periódicamente."""
        for board_id, bridge in list(self._bridges.items()):
            if isinstance(bridge, WiFiBridge):
                bridge.check_timeout()