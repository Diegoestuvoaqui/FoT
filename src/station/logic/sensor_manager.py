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

    def connect_usb(self, port: str, parcela_id: str) -> bool:
        if parcela_id in self._bridges:
            logger.warning("%s ya conectada", parcela_id)
            return False

        def on_read(data: dict):
            if self._on_reading:
                self._on_reading(parcela_id, data)

        def on_resp(data: dict):
            if "sketch" in data and self._on_identify:
                self._on_identify(parcela_id, data)

        bridge = SerialBridge(port=port, on_reading=on_read, on_command_response=on_resp)
        if bridge.connect():
            self._bridges[parcela_id] = bridge
            bridge.request_identify()
            return True
        return False

    def connect_bluetooth(self, port: str, parcela_id: str) -> bool:
        if parcela_id in self._bridges:
            return False

        def on_read(data: dict):
            if self._on_reading:
                self._on_reading(parcela_id, data)

        bridge = BluetoothBridge(port=port, on_reading=on_read)
        if bridge.connect():
            self._bridges[parcela_id] = bridge
            bridge.request_identify()
            return True
        return False

    def connect_wifi(self, parcela_id: str, broker_ip: str = "localhost", broker_port: int = 1883) -> bool:
        """
        Conecta una placa por WiFi (UNO R4).
        Crea un WiFiBridge que se registra en el MQTTEventBus para recibir
        datos y publicar comandos.
        """
        if parcela_id in self._bridges:
            logger.warning("%s ya conectada por WiFi", parcela_id)
            return False

        if self._mqtt_bus is None:
            logger.error("No hay MQTTEventBus configurado para WiFi")
            return False

        def on_read(data: dict):
            if self._on_reading:
                self._on_reading(parcela_id, data)

        def on_resp(data: dict):
            if "sketch" in data and self._on_identify:
                self._on_identify(parcela_id, data)

        bridge = WiFiBridge(
            board_id=parcela_id,
            mqtt_bus=self._mqtt_bus,
            on_reading=on_read,
            on_command_response=on_resp,
        )
        if bridge.connect():
            self._bridges[parcela_id] = bridge
            logger.info("Parcela %s conectada por WiFi (broker: %s:%d)", parcela_id, broker_ip, broker_port)
            return True
        return False

    # ------------------------------------------------------------------
    # Desconexión
    # ------------------------------------------------------------------

    def disconnect(self, parcela_id: str) -> None:
        bridge = self._bridges.pop(parcela_id, None)
        if bridge:
            bridge.disconnect()
            logger.info("%s desconectada", parcela_id)

    def disconnect_all(self) -> None:
        for parcela_id in list(self._bridges.keys()):
            self.disconnect(parcela_id)

    # ------------------------------------------------------------------
    # Comandos
    # ------------------------------------------------------------------

    def send_command(self, parcela_id: str, cmd: dict) -> bool:
        bridge = self._bridges.get(parcela_id)
        if not bridge:
            return False
        bridge.send_command(cmd)
        return True

    def request_read(self, parcela_id: str) -> bool:
        return self.send_command(parcela_id, {"cmd": "read"})

    def set_interval(self, parcela_id: str, ms: int) -> bool:
        return self.send_command(parcela_id, {"cmd": "interval", "ms": ms})

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------

    def get_connected(self) -> list[str]:
        """Retorna IDs de parcelas conectadas por USB/Bluetooth/WiFi."""
        return list(self._bridges.keys())

    def is_connected(self, parcela_id: str) -> bool:
        bridge = self._bridges.get(parcela_id)
        return bridge is not None and bridge.is_connected()