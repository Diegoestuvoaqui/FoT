# logic/mqtt_data_dispatcher.py
"""
Receptor único de datos MQTT para todas las placas WiFi.
Se registra una sola vez en el bus y enruta a DataReceiver, BoardService, etc.
"""
from __future__ import annotations

import logging
from typing import Callable, Optional

from logic.sensor_manager import SensorManager

logger = logging.getLogger(__name__)


class MQTTDataDispatcher:
    """
    Único observer del MQTTEventBus para topics de sensores.
    Enruta datos a:
    - DataReceiver (guardar en DB)
    - BoardService (identificación de sketch, auto-registro)

    NOTA: Solo marca el WiFiBridge como 'visto' en mensajes de estado/conexión,
    NO en lecturas de sensores periódicas.
    """

    def __init__(self,
                 sensor_manager: SensorManager,
                 on_reading: Optional[Callable[[str, dict], None]] = None,
                 on_identify: Optional[Callable[[str, dict], None]] = None,
                 on_new_board: Optional[Callable[[str, str], None]] = None):
        self._sensor_manager = sensor_manager
        self._on_reading = on_reading
        self._on_identify = on_identify
        self._on_new_board = on_new_board  # callback(board_id, conn_type)
        self._known_boards: set[str] = set()

    def on_event(self, topic: str, data: dict) -> None:
        # Topic esperado: fot/<board_id>/sensores  o  fot/<board_id>/estado
        parts = topic.split("/")
        if len(parts) < 3 or parts[0] != "fot":
            return

        board_id = parts[1]
        msg_type = parts[2] if len(parts) > 2 else "unknown"

        # Auto-descubrimiento: si es una placa nueva, notificar
        if board_id not in self._known_boards:
            self._known_boards.add(board_id)
            if self._on_new_board:
                self._on_new_board(board_id, "wifi")
            logger.info("Nueva placa WiFi detectada vía MQTT: %s", board_id)

        # Enrutar según tipo de mensaje
        if msg_type == "sensores" and "data" in data:
            # Lectura de sensor: guardar en DB, NO marcar como 'visto' el bridge
            if self._on_reading:
                self._on_reading(board_id, data)

        elif msg_type == "estado":
            # Mensaje de estado/conexión: marcar bridge como vivo y procesar identificación
            self._mark_bridge_seen(board_id)

            if "sketch" in data and self._on_identify:
                self._on_identify(board_id, data)
            # También puede ser heartbeat, error, etc.
        else:
            logger.debug("Mensaje MQTT no manejado: %s → keys=%s", topic, list(data.keys()))

    def _mark_bridge_seen(self, board_id: str) -> None:
        """
        Marca el WiFiBridge como 'visto' solo en mensajes de estado/conexión.
        No se llama en lecturas de sensores periódicas.
        """
        if not self._sensor_manager.is_connected(board_id):
            return

        bridge = self._sensor_manager.get_bridge(board_id)
        if bridge is not None and hasattr(bridge, 'mark_seen'):
            bridge.mark_seen()
            logger.debug("WiFiBridge %s marcado como visto (estado/identify)", board_id)
