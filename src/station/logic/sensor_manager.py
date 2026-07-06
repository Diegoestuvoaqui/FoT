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
    """

    def __init__(self,
                 on_reading: Optional[Callable[[str, dict], None]] = None,
                 on_identify: Optional[Callable[[str, dict], None]] = None,
                 mqtt_bus=None):
        self._bridges: dict[str, SerialBridge | WiFiBridge] = {}
        self._on_reading = on_reading
        self._on_identify = on_identify
        self._mqtt_bus = mqtt_bus

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def set_callbacks(self,
                      on_reading: Optional[Callable[[str, dict], None]] = None,
                      on_identify: Optional[Callable[[str, dict], None]] = None) -> None:
        if on_reading is not None:
            self._on_reading = on_reading
        if on_identify is not None:
            self._on_identify = on_identify

    # ------------------------------------------------------------------
    # Conexiones
    # ------------------------------------------------------------------

    def connect_usb(self, port: str, board_id: str) -> bool:
        if board_id in self._bridges:
            logger.warning("%s ya conectada", board_id)
            return False

        def on_read(data: dict):
            if self._on_reading:
                self._on_reading(board_id, data)

        def on_resp(data: dict):
            if "sketch" in data and self._on_identify:
                self._on_identify(board_id, data)

        bridge = SerialBridge(port=port, on_reading=on_read, on_command_response=on_resp)
        if bridge.connect():
            self._bridges[board_id] = bridge
            bridge.request_identify()
            return True
        return False

    def connect_bluetooth(self, port: str, board_id: str) -> bool:
        if board_id in self._bridges:
            return False

        def on_read(data: dict):
            if self._on_reading:
                self._on_reading(board_id, data)

        bridge = BluetoothBridge(port=port, on_reading=on_read)
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

        # WiFiBridge ya no necesita callbacks de lectura — el dispatcher global los maneja
        bridge = WiFiBridge(
            board_id=board_id,
            mqtt_bus=self._mqtt_bus,
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