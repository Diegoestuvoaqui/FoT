# logic/wifi_bridge.py
"""
Bridge virtual para placas WiFi (UNO R4).
Ya NO es observer del MQTTEventBus — solo publica comandos.
El receptor de datos es MQTTDataDispatcher (único para todas las placas).
"""
from __future__ import annotations

import logging
import time
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class WiFiBridge:
    """
    Adaptador que publica comandos MQTT a una placa WiFi específica.
    Los datos entrantes son manejados por MQTTDataDispatcher global.
    """

    def __init__(self,
                 board_id: str,
                 mqtt_bus,
                 on_command_response: Optional[Callable[[dict], None]] = None,
                 on_disconnect: Optional[Callable[[], None]] = None,
                 timeout: float = 120.0):
        self._on_disconnect = on_disconnect
        self.board_id = board_id
        self._mqtt_bus = mqtt_bus
        self._on_cmd_response = on_command_response
        self._timeout = timeout
        self._last_seen: float = 0
        self._connected = False

    # ------------------------------------------------------------------
    # Ciclo de vida
    # ------------------------------------------------------------------

    def connect(self) -> bool:
        """Marca el bridge como activo. Los datos ya llegan vía dispatcher global."""
        self._connected = True
        self._last_seen = time.time()
        logger.info("WiFiBridge activo para %s", self.board_id)
        return True

    def disconnect(self) -> None:
        self._connected = False
        logger.info("WiFiBridge desactivado para %s", self.board_id)

    def is_connected(self) -> bool:
        """True si está activo y ha recibido mensajes recientemente (vía dispatcher)."""
        if not self._connected:
            return False
        if time.time() - self._last_seen > self._timeout:
            self._connected = False
            return False
        return True

    def mark_seen(self) -> None:
        """Llamado por el dispatcher cuando llega un mensaje de esta placa."""
        self._last_seen = time.time()
        self._connected = True

    def check_timeout(self) -> bool:
        """Devuelve True si sigue conectado. Si venció, notifica y devuelve False."""
        if not self._connected:
            return False
        if time.time() - self._last_seen > self._timeout:
            self._connected = False
            logger.info("WiFiBridge timeout para %s", self.board_id)
            if self._on_disconnect:
                try:
                    self._on_disconnect()
                except Exception as e:
                    logger.error("Error en on_disconnect WiFi: %s", e)
            return False
        return True

    # ------------------------------------------------------------------
    # Comunicación
    # ------------------------------------------------------------------

    def send_command(self, cmd_dict: dict) -> None:
        """Publica un comando en el topic de control de la placa."""
        if not self.is_connected():
            logger.warning("WiFiBridge: intento de envío sin conexión activa (%s)", self.board_id)
            return
        topic = f"fot/{self.board_id}/control"
        self._mqtt_bus.publish(topic, cmd_dict)
        logger.debug("WiFiBridge → %s: %s", topic, cmd_dict)

    # ------------------------------------------------------------------
    # Recepción ya no va aquí — la maneja MQTTDataDispatcher
    # ------------------------------------------------------------------
