# logic/wifi_bridge.py
"""
Bridge virtual para placas WiFi (UNO R4) conectadas vía MQTT.
No usa serial; se registra como observer del MQTTEventBus para recibir
datos y publica comandos en el topic correspondiente.
"""
from __future__ import annotations

import logging
import time
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class WiFiBridge:
    """
    Adaptador que unifica la interfaz de conexión para placas WiFi
    bajo el mismo patrón que SerialBridge y BluetoothBridge.
    """

    def __init__(self,
                 board_id: str,
                 mqtt_bus,
                 on_reading: Optional[Callable[[dict], None]] = None,
                 on_command_response: Optional[Callable[[dict], None]] = None,
                 timeout: float = 30.0):
        self.board_id = board_id
        self._mqtt_bus = mqtt_bus
        self._on_reading = on_reading
        self._on_cmd_response = on_command_response
        self._timeout = timeout
        self._last_seen: float = 0
        self._connected = False

    # ------------------------------------------------------------------
    # Ciclo de vida
    # ------------------------------------------------------------------

    def connect(self) -> bool:
        """Se registra como observer del broker MQTT."""
        self._mqtt_bus.register(self)
        self._connected = True
        self._last_seen = time.time()
        logger.info("WiFiBridge conectado para %s", self.board_id)
        return True

    def disconnect(self) -> None:
        """Se desregistra del broker."""
        self._mqtt_bus.unregister(self)
        self._connected = False
        logger.info("WiFiBridge desconectado para %s", self.board_id)

    def is_connected(self) -> bool:
        """True si está registrado y ha recibido mensajes recientemente."""
        if not self._connected:
            return False
        if time.time() - self._last_seen > self._timeout:
            self._connected = False
            return False
        return True

    # ------------------------------------------------------------------
    # Comunicación
    # ------------------------------------------------------------------

    def send_command(self, cmd_dict: dict) -> None:
        """Publica un comando en el topic de la placa."""
        if not self.is_connected():
            logger.warning("WiFiBridge: intento de envío sin conexión activa")
            return
        topic = f"fot/{self.board_id}/control"  # ← CORREGIDO: "control" en vez de "comandos"
        self._mqtt_bus.publish(topic, cmd_dict)
        logger.debug("WiFiBridge → %s: %s", topic, cmd_dict)

    # ------------------------------------------------------------------
    # Recepción MQTT (observer)
    # ------------------------------------------------------------------

    def on_event(self, topic: str, data: dict) -> None:
        """
        Callback del MQTTEventBus. Filtra solo los mensajes destinados
        a esta placa.
        """
        # Topic esperado: fot/<board_id>/sensores  o  fot/<board_id>/estado
        parts = topic.split("/")
        if len(parts) < 3 or parts[1] != self.board_id:
            return

        self._last_seen = time.time()
        self._connected = True

        msg_type = self._classify_message(data)
        if msg_type == "reading" and self._on_reading:
            self._on_reading(data)
        elif msg_type in ("status", "response") and self._on_cmd_response:
            self._on_cmd_response(data)

    def _classify_message(self, data: dict) -> str:
        if "data" in data and "ts" in data:
            return "reading"
        if "sketch" in data or "status" in data or "state" in data:  # ← CORREGIDO: añadido "state"
            return "status"
        return "response"