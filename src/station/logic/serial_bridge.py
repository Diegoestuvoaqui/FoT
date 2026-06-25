"""
logic/serial_bridge.py
"""
from __future__ import annotations

import json
import logging
import threading
import time
from collections.abc import Callable
from typing import Optional

import serial  # type: ignore[import-untyped]  # ← pyserial no tiene stubs

logger = logging.getLogger(__name__)


class SerialBridge:

    def __init__(self, port: str, baud: int = 9600,
                 on_message: Optional[Callable[[dict], None]] = None,  # ← callable → Callable
                 timeout: float = 1.0):
        self.port = port
        self.baud = baud
        self._on_message = on_message
        self._serial: Optional[serial.Serial] = None
        self._reader_thread: Optional[threading.Thread] = None
        self._running = False
        self.timeout = timeout

    def connect(self) -> bool:
        try:
            self._serial = serial.Serial(self.port, self.baud, timeout=self.timeout)
            self._running = True
            self._reader_thread = threading.Thread(target=self._read_loop, daemon=True)
            assert self._reader_thread is not None  # ← satisface el linter
            self._reader_thread.start()
            logger.info(f"Conectado a {self.port}")
            self._handshake_version()
            return True
        except serial.SerialException as e:
            logger.error(f"No se pudo conectar a {self.port}: {e}")
            return False

    def disconnect(self) -> None:
        self._running = False
        if self._reader_thread:
            self._reader_thread.join(timeout=2)
        if self._serial and self._serial.is_open:
            self._serial.close()
            logger.info(f"Desconectado de {self.port}")

    def is_connected(self) -> bool:
        return self._serial is not None and self._serial.is_open

    def send_command(self, cmd: dict) -> None:
        if not self.is_connected():
            logger.warning("Intento de envío sin conexión")
            return
        if self._serial is None:  # ← guard para linter
            return
        try:
            line = json.dumps(cmd) + "\n"
            self._serial.write(line.encode("utf-8"))  # ← ahora _serial no es None
            self._serial.flush()
        except serial.SerialException as e:
            logger.error(f"Error al enviar comando por {self.port}: {e}")

    def _read_loop(self) -> None:
        buffer = ""
        while self._running and self._serial and self._serial.is_open:
            try:
                if self._serial.in_waiting > 0:
                    chunk = self._serial.read(self._serial.in_waiting).decode("utf-8", errors="replace")
                    buffer += chunk
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        line = line.strip()
                        if line:
                            self._process_line(line)
                else:
                    time.sleep(0.01)
            except serial.SerialException:
                logger.error("Error de lectura serial, cerrando puerto")
                self._running = False
                break
            except Exception as e:  # ← este sí es correcto: errores inesperados
                logger.error(f"Error inesperado en lector serial: {e}")

    def _process_line(self, line: str) -> None:
        try:
            data = json.loads(line)
            if self._on_message:
                self._on_message(data)
        except json.JSONDecodeError:
            logger.warning(f"Línea no JSON recibida en {self.port}: {line}")

    def _handshake_version(self) -> None:
        self.send_command({"cmd": "version"})
