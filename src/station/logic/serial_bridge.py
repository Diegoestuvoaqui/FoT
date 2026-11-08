# src/station/logic/serial_bridge.py
from __future__ import annotations

import json
import logging
import threading
import time
from collections.abc import Callable
from typing import Optional

import serial

from logic.ibridge import IBridge

logger = logging.getLogger(__name__)


class SerialBridge(IBridge):
    """Bridge serial (USB o RFCOMM/Bluetooth) con protocolo JSON."""

    def __init__(self,
                 port: str,
                 baud: int = 115200,
                 on_reading: Optional[Callable[[dict], None]] = None,
                 on_command_response: Optional[Callable[[dict], None]] = None,
                 on_disconnect: Optional[Callable[[], None]] = None,
                 timeout: float = 60.0):
        self.port = port
        self.baud = baud
        self._on_reading = on_reading
        self._on_cmd_response = on_command_response
        self._on_disconnect = on_disconnect
        self._serial: Optional[serial.Serial] = None
        self._reader_thread: Optional[threading.Thread] = None
        self._running = False
        self.timeout = timeout

    # ------------------------------------------------------------------
    # Ciclo de vida (IBridge)
    # ------------------------------------------------------------------
    def connect(self) -> bool:
        try:
            self._serial = serial.Serial(self.port, self.baud, timeout=self.timeout)
            self._running = True
            self._reader_thread = threading.Thread(
                target=self._read_loop, daemon=True)
            self._reader_thread.start()
            logger.info("Conectado a %s @ %d baud", self.port, self.baud)
            time.sleep(3.0)  # margen para que el Arduino reinicie
            return True
        except serial.SerialException as e:
            logger.error("No se pudo conectar a %s: %s", self.port, e)
            return False

    def disconnect(self) -> None:
        self._running = False
        if self._reader_thread:
            self._reader_thread.join(timeout=2)
        if self._serial and self._serial.is_open:
            self._serial.close()
            logger.info("Desconectado de %s", self.port)

    def is_connected(self) -> bool:
        return bool(self._serial and self._serial.is_open and self._running)

    def check_timeout(self) -> bool:
        # El socket manda: si está abierto, está vivo.
        return self.is_connected()

    def set_timeout(self, seconds: float) -> None:
        # El timeout real lo gestiona el SO con `serial.Serial(timeout=...)`.
        pass

    # mark_seen() hereda el no-op de IBridge: no aplica a serial.

    # ------------------------------------------------------------------
    # Comandos
    # ------------------------------------------------------------------
    def send_command(self, cmd_dict: dict) -> bool:
        if not self.is_connected():
            logger.warning("Intento de envío sin conexión en %s", self.port)
            return False
        try:
            line = json.dumps(cmd_dict) + "\n"
            self._serial.write(line.encode("utf-8"))
            self._serial.flush()
            logger.debug("Enviado a %s: %s", self.port, line.strip())
            return True
        except serial.SerialException as e:
            logger.error("Error al enviar a %s: %s", self.port, e)
            return False

    def request_read(self) -> bool:
        return self.send_command({"cmd": "read"})

    def request_identify(self) -> bool:
        return self.send_command({"cmd": "identify"})

    def set_interval(self, ms: int) -> bool:
        return self.send_command({"cmd": "interval", "ms": ms})

    # ------------------------------------------------------------------
    # Lectura
    # ------------------------------------------------------------------
    def _read_loop(self) -> None:
        buffer = ""
        while self._running and self._serial and self._serial.is_open:
            try:
                if self._serial.in_waiting > 0:
                    chunk = self._serial.read(
                        self._serial.in_waiting).decode("utf-8", errors="replace")
                    buffer += chunk
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        line = line.strip()
                        if line:
                            self._process_line(line)
                else:
                    time.sleep(0.01)
            except serial.SerialException:
                logger.error("Error de lectura serial en %s, cerrando", self.port)
                self._running = False
                if self._on_disconnect is not None:
                    try:
                        self._on_disconnect()
                    except Exception as e:
                        logger.error("Error en on_disconnect: %s", e)
                break
            except Exception as e:
                logger.error("Error inesperado leyendo %s: %s", self.port, e)

    def _process_line(self, line: str) -> None:
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            logger.warning("Línea no JSON (%s): %s", self.port, line[:80])
            return

        msg_type = self._classify_message(data)
        if msg_type == "reading" and self._on_reading:
            self._on_reading(data)
        elif msg_type == "response" and self._on_cmd_response:
            self._on_cmd_response(data)
        elif msg_type == "status":
            logger.info("Estado del dispositivo %s: %s", self.port, data)
        else:
            logger.debug("Mensaje no clasificado (%s): %s", self.port, data)

    @staticmethod
    def _classify_message(data: dict) -> str:
        if "data" in data and "ts" in data:
            return "reading"
        if "sketch" in data:
            return "response"
        if "status" in data:
            return "status"
        return "response"