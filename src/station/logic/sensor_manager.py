# src/station/logic/sensor_manager.py
"""Facade de conexiones (USB / BT / WiFi) + bus de observers."""
from __future__ import annotations

import logging
from typing import Callable, Optional

from logic.bluetooth_bridge import BluetoothBridge
from logic.ibridge import IBridge
from logic.serial_bridge import SerialBridge
from logic.wifi_bridge import WiFiBridge

logger = logging.getLogger(__name__)


class SensorManager:
    def __init__(self, mqtt_bus=None):
        self._bridges: dict[str, IBridge] = {}
        self._mqtt_bus = mqtt_bus

        self._reading_observers: list[Callable[[str, dict], None]] = []
        self._identify_observers: list[Callable[[str, dict], None]] = []
        self._disconnect_observers: list[Callable[[str], None]] = []
        self._state_observers: list[Callable[[str, dict], None]] = []
        self._relay_ack_observers: list[Callable[[str, dict], None]] = []

    # ------------------------------------------------------------------
    # Observers
    # ------------------------------------------------------------------
    def _add(self, lst, cb):
        if cb not in lst:
            lst.append(cb)

    def _remove(self, lst, cb):
        if cb in lst:
            lst.remove(cb)

    def add_reading_observer(self, cb): self._add(self._reading_observers, cb)
    def remove_reading_observer(self, cb): self._remove(self._reading_observers, cb)
    def add_identify_observer(self, cb): self._add(self._identify_observers, cb)
    def remove_identify_observer(self, cb): self._remove(self._identify_observers, cb)
    def add_disconnect_observer(self, cb): self._add(self._disconnect_observers, cb)
    def remove_disconnect_observer(self, cb): self._remove(self._disconnect_observers, cb)
    def add_state_observer(self, cb): self._add(self._state_observers, cb)
    def remove_state_observer(self, cb): self._remove(self._state_observers, cb)
    def add_relay_ack_observer(self, cb): self._add(self._relay_ack_observers, cb)
    def remove_relay_ack_observer(self, cb): self._remove(self._relay_ack_observers, cb)

    # ------------------------------------------------------------------
    # Notificadores públicos (usados por MQTTDataDispatcher, Fase 4)
    # ------------------------------------------------------------------
    def _notify(self, lst, *args):
        for obs in list(lst):
            try:
                obs(*args)
            except Exception as e:
                logger.error("Error en observer %s: %s", obs, e)

    def publish_reading(self, board_id: str, data: dict) -> None:
        self._notify(self._reading_observers, board_id, data)

    def publish_identify(self, board_id: str, data: dict) -> None:
        self._notify(self._identify_observers, board_id, data)

    def publish_disconnect(self, board_id: str) -> None:
        self._notify(self._disconnect_observers, board_id)

    def publish_state(self, board_id: str, data: dict) -> None:
        self._notify(self._state_observers, board_id, data)

    def publish_relay_ack(self, board_id: str, data: dict) -> None:
        self._notify(self._relay_ack_observers, board_id, data)

    # ------------------------------------------------------------------
    # WiFi (nuevo flujo)
    # ------------------------------------------------------------------
    def ensure_wifi_bridge(self, board_id: str) -> bool:
        """Crea el bridge WiFi si no existe (idempotente). No es 'conectar':
        el bridge queda 'listo' pero is_connected() seguirá siendo False
        hasta que llegue el primer mensaje MQTT de esta placa."""
        if board_id in self._bridges:
            return True
        if self._mqtt_bus is None:
            logger.error("Sin MQTTEventBus: no puedo crear WiFiBridge de %s", board_id)
            return False

        def on_disc():
            self._bridges.pop(board_id, None)
            self.publish_disconnect(board_id)

        bridge = WiFiBridge(board_id=board_id, mqtt_bus=self._mqtt_bus,
                            on_disconnect=on_disc)
        self._bridges[board_id] = bridge
        bridge.connect()
        return True

    def mark_seen(self, board_id: str) -> None:
        """Señal de vida. Si no existe bridge para esta placa, lo crea
        aquí mismo (auto-registro al primer mensaje MQTT). Así
        set_relay/send_command funcionan sin exigir que el usuario
        pulse 'Conectar' antes."""
        bridge = self._bridges.get(board_id)
        if bridge is None:
            if self._mqtt_bus is None:
                logger.error(
                    "mark_seen(%s) sin MQTTEventBus: no puedo crear bridge",
                    board_id)
                return
            self.ensure_wifi_bridge(board_id)
            bridge = self._bridges.get(board_id)
            if bridge is None:
                logger.error(
                    "mark_seen(%s): ensure_wifi_bridge no creó el bridge",
                    board_id)
                return
        bridge.mark_seen()

    # ------------------------------------------------------------------
    # USB / BT (sin cambios funcionales, sí tipado IBridge)
    # ------------------------------------------------------------------
    def connect_usb(self, port: str, board_id: str) -> bool:
        if board_id in self._bridges:
            return False
        def on_read(data): self.publish_reading(board_id, data)
        def on_resp(data):
            if "sketch" in data:
                self.publish_identify(board_id, data)
        def on_disc():
            self._bridges.pop(board_id, None)
            self.publish_disconnect(board_id)
        b = SerialBridge(port=port, on_reading=on_read,
                         on_command_response=on_resp, on_disconnect=on_disc)
        if b.connect():
            self._bridges[board_id] = b
            b.request_identify()
            return True
        return False

    def connect_bluetooth(self, port: str, board_id: str) -> bool:
        if board_id in self._bridges:
            return False
        def on_read(data): self.publish_reading(board_id, data)
        def on_disc():
            self._bridges.pop(board_id, None)
            self.publish_disconnect(board_id)
        b = BluetoothBridge(port=port, on_reading=on_read, on_disconnect=on_disc)
        if b.connect():
            self._bridges[board_id] = b
            b.request_identify()
            return True
        return False

    # Compatibilidad con BoardService (usa ensure_wifi_bridge por dentro)
    def connect_wifi(self, board_id: str, broker_ip: str = "", broker_port: int = 1883) -> bool:
        return self.ensure_wifi_bridge(board_id)

    # ------------------------------------------------------------------
    def disconnect(self, board_id: str) -> None:
        b = self._bridges.pop(board_id, None)
        if b:
            b.disconnect()
            logger.info("%s desconectada", board_id)

    def disconnect_all(self) -> None:
        for board_id in list(self._bridges):
            self.disconnect(board_id)

    def send_command(self, board_id: str, cmd: dict) -> bool:
        b = self._bridges.get(board_id)
        return b.send_command(cmd) if b else False

    def request_read(self, board_id: str) -> bool:
        return self.send_command(board_id, {"cmd": "read"})

    def request_identify(self, board_id: str) -> bool:
        return self.send_command(board_id, {"cmd": "identify"})

    def set_interval(self, board_id: str, ms: int) -> bool:
        return self.send_command(board_id, {"cmd": "interval", "ms": ms})

    def set_relay(self, board_id: str, actuator_id: str,
        state: bool, seq: int) -> bool:
        return self.send_command(board_id, {
            "cmd": "relay",
            "id": actuator_id,
            "state": 1 if state else 0,
            "seq": seq,
        })

    def get_connected(self) -> list[str]:
        return [bid for bid, b in self._bridges.items() if b.is_connected()]

    def is_connected(self, board_id: str) -> bool:
        b = self._bridges.get(board_id)
        return b is not None and b.is_connected()

    def get_bridge(self, board_id: str) -> IBridge | None:
        return self._bridges.get(board_id)

    def check_wifi_timeouts(self) -> None:
        for bid, bridge in list(self._bridges.items()):
            bridge.check_timeout()