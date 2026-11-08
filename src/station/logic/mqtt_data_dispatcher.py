# src/station/logic/mqtt_data_dispatcher.py
"""Único observer del bus MQTT para topics de nodos.

Novedades Fase 4:
- Valida board_id con regex.
- Separa _handle_sensores / _handle_estado.
- Publica a través de SensorManager (no callbacks sueltos).
- mark_seen() independiente de is_connected() → rompe el círculo vicioso
  que dejaba bridges WiFi en "nunca visto".
- Maneja ack de relé (preparado para Fase 5).
"""
from __future__ import annotations

import logging
import re
from typing import Callable, Optional

from logic.sensor_manager import SensorManager

logger = logging.getLogger(__name__)


class MQTTDataDispatcher:
    BOARD_ID_RE = re.compile(r"^[A-Za-z0-9_-]{3,40}$")

    def __init__(self,
                 sensor_manager: SensorManager,
                 on_new_board: Optional[Callable[[str, str], None]] = None):
        self._sm = sensor_manager
        self._on_new_board = on_new_board
        self._known_boards: set[str] = set()

    def on_event(self, topic: str, data: dict) -> None:
        parts = topic.split("/")
        if len(parts) < 3 or parts[0] != "fot":
            return
        board_id, msg_type = parts[1], parts[2]

        if not self.BOARD_ID_RE.match(board_id):
            logger.warning("board_id descartado (inválido): %r", board_id)
            return

        # Auto-descubrimiento
        if board_id not in self._known_boards:
            self._known_boards.add(board_id)
            if self._on_new_board:
                try:
                    self._on_new_board(board_id, "wifi")
                except Exception as e:
                    logger.error("on_new_board falló: %s", e)
            logger.info("Nueva placa WiFi detectada: %s", board_id)

        # Lifecycle del bridge (no-op si no existe)
        self._sm.mark_seen(board_id)

        if msg_type == "sensores":
            self._handle_sensores(board_id, data)
        elif msg_type == "estado":
            self._handle_estado(board_id, data)
        else:
            logger.debug("MQTT topic no manejado: %s", topic)

    # ------------------------------------------------------------------
    def _handle_sensores(self, board_id: str, data: dict) -> None:
        if "data" not in data:
            return
        self._sm.publish_reading(board_id, data)

    def _handle_estado(self, board_id: str, data: dict) -> None:
        if "sketch" in data:
            self._sm.publish_identify(board_id, data)

        if "status" in data:
            self._sm.publish_state(board_id, data)

        if data.get("ack") == "relay":
            self._sm.publish_relay_ack(board_id, data)