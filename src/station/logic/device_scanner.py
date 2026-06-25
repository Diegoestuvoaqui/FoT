"""
logic/device_scanner.py
Hilo daemon que escanea puertos USB cada 3 segundos y notifica cambios.
"""
import logging
import threading
import time

import serial.tools.list_ports

logger = logging.getLogger(__name__)


class USBScanner(threading.Thread):
    """
    Escanea puertos seriales y avisa de placas nuevas/desconectadas.
    Uso:
        scanner = USBScanner(on_new_board=callback, interval=3)
        scanner.start()
    """

    def __init__(self, on_new_board=None, on_remove_board=None, interval=3):
        super().__init__(daemon=True)
        self._on_new_board = on_new_board  # callback(port_info)
        self._on_remove_board = on_remove_board  # callback(port_info)
        self._interval = interval
        self._running = False
        self._known_ports = set()

    def run(self):
        self._running = True
        while self._running:
            try:
                ports = list(serial.tools.list_ports.comports())

                # Solo puertos que sean ttyUSB o ttyACM con número de serie
                # Ignora ttyS* (puertos nativos del sistema, no son Arduinos)
                current = set()
                for p in ports:
                    is_arduino_port = ("ttyUSB" in p.device or "ttyACM" in p.device)
                    has_serial = bool(p.serial_number)
                    if is_arduino_port and has_serial:
                        current.add(p.device)

                added = current - self._known_ports
                removed = self._known_ports - current

                for dev in added:
                    port = next(p for p in ports if p.device == dev)
                    logger.info(f"Nuevo Arduino en: {port.device} - {port.description}")
                    if self._on_new_board:
                        self._on_new_board(port)

                for dev in removed:
                    logger.info(f"Arduino desconectado: {dev}")
                    if self._on_remove_board:
                        self._on_remove_board(dev)

                self._known_ports = current

            except Exception as e:
                logger.error(f"Error en escáner USB: {e}")

            time.sleep(self._interval)

    def stop(self):
        self._running = False
