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

logger = logging.getLogger(__name__)


class SensorManager:
    """
    Administra múltiples conexiones a placas Arduino.
    Soporta USB, Bluetooth y WiFi simultáneamente.
    """

    def __init__(self,
                 on_reading: Optional[Callable[[str, dict], None]] = None,
                 on_identify: Optional[Callable[[str, dict], None]] = None):
        self._bridges: dict[str, SerialBridge] = {}
        self._on_reading = on_reading
        self._on_identify = on_identify

    # ------------------------------------------------------------------
    # Callbacks (pueden setearse después del constructor)
    # ------------------------------------------------------------------

    def set_callbacks(self,
                      on_reading: Optional[Callable[[str, dict], None]] = None,
                      on_identify: Optional[Callable[[str, dict], None]] = None) -> None:
        """Actualiza los callbacks en tiempo de ejecución."""
        if on_reading is not None:
            self._on_reading = on_reading
        if on_identify is not None:
            self._on_identify = on_identify

    # ------------------------------------------------------------------
    # Conexiones
    # ------------------------------------------------------------------

    def connect_usb(self, port: str, parcela_id: str) -> bool:
        """Conecta una placa por USB."""
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
        """Conecta una placa por Bluetooth (HC-05/06)."""
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
        La placa se conecta directamente al broker MQTT, no por serial.
        Este método solo registra la parcela como 'conectada por WiFi'.
        Las lecturas llegan por MQTTEventBus, no por SerialBridge.
        """
        # Las placas WiFi se autoconectan al broker MQTT
        # Solo registramos que esta parcela tiene una placa WiFi asociada
        logger.info("Parcela %s configurada para WiFi (broker: %s:%d)", parcela_id, broker_ip, broker_port)
        return True

    # ------------------------------------------------------------------
    # Desconexión
    # ------------------------------------------------------------------

    def disconnect(self, parcela_id: str) -> None:
        """Desconecta una placa."""
        bridge = self._bridges.pop(parcela_id, None)
        if bridge:
            bridge.disconnect()
            logger.info("%s desconectada", parcela_id)

    def disconnect_all(self) -> None:
        """Desconecta todas las placas."""
        for parcela_id in list(self._bridges.keys()):
            self.disconnect(parcela_id)

    # ------------------------------------------------------------------
    # Comandos
    # ------------------------------------------------------------------

    def send_command(self, parcela_id: str, cmd: dict) -> bool:
        """Envía un comando a una placa específica."""
        bridge = self._bridges.get(parcela_id)
        if not bridge:
            return False
        bridge.send_command(cmd)
        return True

    def request_read(self, parcela_id: str) -> bool:
        """Solicita lectura inmediata."""
        return self.send_command(parcela_id, {"cmd": "read"})

    def set_interval(self, parcela_id: str, ms: int) -> bool:
        """Cambia intervalo de lectura."""
        return self.send_command(parcela_id, {"cmd": "interval", "ms": ms})

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------

    def get_connected(self) -> list[str]:
        """Retorna IDs de parcelas conectadas por USB/Bluetooth."""
        return list(self._bridges.keys())

    def is_connected(self, parcela_id: str) -> bool:
        bridge = self._bridges.get(parcela_id)
        return bridge is not None and bridge.is_connected()
