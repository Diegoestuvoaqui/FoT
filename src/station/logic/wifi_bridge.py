# src/station/logic/wifi_bridge.py
"""Bridge para placas WiFi (ESP32 y UNO R4 WiFi).

Novedad Fase 4:
- `connect()` deja el bridge en estado "listo" pero NO conectado.
- `is_connected()` solo es True tras el primer `mark_seen()` (heartbeat).
  Esto elimina los "fantasmas" del tipo `test`: una placa registrada en la
  BD pero sin tráfico real NO aparece como conectada.
- `send_command()` devuelve bool.
"""
from __future__ import annotations

import logging
import time
from typing import Callable, Optional

from logic.ibridge import IBridge

logger = logging.getLogger(__name__)


class WiFiBridge(IBridge):
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
        self._last_seen: float = 0.0
        self._ready: bool = False          # bridge activo, esperando heartbeat
        self._had_heartbeat: bool = False  # alguna vez llegó algo

    # ------------------------------------------------------------------
    def connect(self) -> bool:
        """Marca el bridge como listo. NO implica 'conectado'."""
        self._ready = True
        self._last_seen = 0.0
        self._had_heartbeat = False
        logger.info("WiFiBridge listo para %s (esperando heartbeat)", self.board_id)
        return True

    def disconnect(self) -> None:
        self._ready = False
        self._last_seen = 0.0
        self._had_heartbeat = False
        logger.info("WiFiBridge desactivado para %s", self.board_id)

    def is_connected(self) -> bool:
        if not self._ready or self._last_seen <= 0:
            return False
        return (time.time() - self._last_seen) <= self._timeout

    def mark_seen(self) -> None:
        self._last_seen = time.time()
        if not self._had_heartbeat:
            self._had_heartbeat = True
            logger.info("WiFiBridge %s: primer heartbeat recibido", self.board_id)

    def check_timeout(self) -> bool:
        if not self._ready:
            return False
        if not self._had_heartbeat:
            return False  # nunca llegó a estar vivo, no aplica timeout
        if (time.time() - self._last_seen) <= self._timeout:
            return True
        self._had_heartbeat = False
        logger.info("WiFiBridge timeout para %s", self.board_id)
        if self._on_disconnect:
            try:
                self._on_disconnect()
            except Exception as e:
                logger.error("Error en on_disconnect WiFi: %s", e)
        return False

    def send_command(self, cmd_dict: dict) -> bool:
        if not self.is_connected():
            logger.debug("WiFiBridge %s: comando descartado (sin heartbeat)", self.board_id)
            return False
        try:
            self._mqtt_bus.publish(f"fot/{self.board_id}/control", cmd_dict)
            return True
        except Exception as e:
            logger.error("WiFiBridge %s: error publicando comando: %s", self.board_id, e)
            return False

    def set_timeout(self, seconds: float) -> None:
        self._timeout = float(seconds)