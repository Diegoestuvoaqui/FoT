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
    def __init__(self, on_new_board=None, on_remove_board=None, interval=3):
        super().__init__(daemon=True)
        self._on_new_board = on_new_board  # callback(port_info_dict)
        self._on_remove_board = on_remove_board  # callback(port_device)
        self._interval = interval
        self._running = False
        self._known_ports = {}  # device -> port_info_dict

    def run(self):
        self._running = True
        while self._running:
            try:
                ports = list(serial.tools.list_ports.comports())

                current = {}
                for p in ports:
                    is_arduino_port = ("ttyUSB" in p.device or "ttyACM" in p.device)
                    has_serial = bool(p.serial_number)
                    if is_arduino_port and has_serial:
                        # Extraer todos los datos de fábrica relevantes
                        port_data = {
                            "device": p.device,
                            "description": p.description,
                            "hwid": p.hwid,
                            "vid": p.vid,
                            "pid": p.pid,
                            "serial_number": p.serial_number,
                            "manufacturer": p.manufacturer,
                            "product": p.product,
                            "location": p.location,
                        }
                        current[p.device] = port_data

                added = [current[d] for d in current if d not in self._known_ports]
                removed = [d for d in self._known_ports if d not in current]

                for port_data in added:
                    logger.info(
                        "Nuevo Arduino en: %s - %s (S/N: %s, VID/PID: %04X:%04X)",
                        port_data["device"],
                        port_data["description"],
                        port_data["serial_number"],
                        port_data["vid"] or 0,
                        port_data["pid"] or 0,
                    )
                    if self._on_new_board:
                        self._on_new_board(port_data)

                for dev in removed:
                    logger.info("Arduino desconectado: %s", dev)
                    if self._on_remove_board:
                        self._on_remove_board(dev)

                self._known_ports = current

            except Exception as e:
                logger.error("Error en escáner USB: %s", e)

            time.sleep(self._interval)

    def stop(self):
        self._running = False