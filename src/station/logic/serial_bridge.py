# src/station/logic/serial_bridge.py
from __future__ import annotations

import json
import logging
import threading
import time
from collections.abc import Callable
from typing import Optional

import serial

logger = logging.getLogger(__name__)


class SerialBridge:
    """
    Bridge serial simplificado para el nuevo protocolo JSON del firmware.
    Soporta USB y Bluetooth (serial sobre RFCOMM).
    """

    def __init__(self,
                 port: str,
                 baud: int = 115200,
                 on_reading: Optional[Callable[[dict], None]] = None,
                 on_command_response: Optional[Callable[[dict], None]] = None,
                 timeout: float = 1.0):
        self.port = port
        self.baud = baud
        self._on_reading = on_reading  # Callback para datos de sensores
        self._on_cmd_response = on_command_response  # Callback para respuestas a comandos
        self._serial: Optional[serial.Serial] = None
        self._reader_thread: Optional[threading.Thread] = None
        self._running = False
        self.timeout = timeout

    def connect(self) -> bool:
        try:
            self._serial = serial.Serial(self.port, self.baud, timeout=self.timeout)
            self._running = True
            self._reader_thread = threading.Thread(target=self._read_loop, daemon=True)
            self._reader_thread.start()
            logger.info("Conectado a %s @ %d baud", self.port, self.baud)
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
        return self._serial is not None and self._serial.is_open

    def send_command(self, cmd_dict: dict) -> None:
        if not self.is_connected():
            logger.warning("Intento de envío sin conexión")
            return
        try:
            line = json.dumps(cmd_dict) + "\n"
            self._serial.write(line.encode("utf-8"))
            self._serial.flush()
            logger.debug("Enviado: %s", line.strip())
        except serial.SerialException as e:
            logger.error("Error al enviar: %s", e)

    def request_read(self) -> None:
        """Solicita una lectura inmediata al sensor."""
        self.send_command({"cmd": "read"})

    def request_identify(self) -> None:
        """Solicita identificación del sketch."""
        self.send_command({"cmd": "identify"})

    def set_interval(self, ms: int) -> None:
        """Cambia el intervalo de lectura del sensor."""
        self.send_command({"cmd": "interval", "ms": ms})

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
                logger.error("Error de lectura serial, cerrando")
                self._running = False
                break
            except Exception as e:
                logger.error("Error inesperado: %s", e)

    def _process_line(self, line: str) -> None:
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            logger.warning("Línea no JSON: %s", line[:80])
            return

        # Determinar tipo de mensaje
        msg_type = self._classify_message(data)

        if msg_type == "reading" and self._on_reading:
            self._on_reading(data)
        elif msg_type == "response" and self._on_cmd_response:
            self._on_cmd_response(data)
        elif msg_type == "status":
            logger.info("Estado del dispositivo: %s", data)
        else:
            logger.debug("Mensaje no clasificado: %s", data)

    def _classify_message(self, data: dict) -> str:
        """Clasifica el mensaje JSON recibido."""
        if "data" in data and "ts" in data:
            return "reading"
        if "sketch" in data or "status" in data:
            return "status"
        return "response"
