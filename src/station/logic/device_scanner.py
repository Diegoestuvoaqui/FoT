# logic/device_scanner.py
"""
logic/device_scanner.py
Hilo daemon que escanea puertos USB cada 3 segundos y notifica cambios.
"""
import logging
import threading
import time

import serial.tools.list_ports

logger = logging.getLogger(__name__)


# VIDs conocidos de chips usados en Arduinos y compatibles
KNOWN_ARDUINO_VIDS = {
    0x0403,   # FTDI
    0x1A86,   # WCH (CH340/CH341)
    0x10C4,   # Silicon Labs (CP210x)
    0x2341,   # Arduino
    0x2A03,   # Arduino (Genuino)
    0x239A,   # Adafruit
    0x0483,   # STMicroelectronics
    0x16C0,   # Teensy
    0x0483,   # STM32
}


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
                    # ← CORREGIDO: detectar por nombre de dispositivo O VID conocido
                    is_arduino_port = self._is_likely_arduino(p)

                    if is_arduino_port:
                        # Extraer todos los datos de fábrica relevantes
                        port_data = {
                            "device": p.device,
                            "description": p.description,
                            "hwid": p.hwid,
                            "vid": p.vid,
                            "pid": p.pid,
                            "serial_number": p.serial_number,  # puede ser None
                            "manufacturer": p.manufacturer,
                            "product": p.product,
                            "location": p.location,
                        }
                        current[p.device] = port_data

                added = [current[d] for d in current if d not in self._known_ports]
                removed = [d for d in self._known_ports if d not in current]

                for port_data in added:
                    logger.info(
                        "Arduino detectado: %s - %s (S/N: %s, VID/PID: %04X:%04X, chip: %s)",
                        port_data["device"],
                        port_data["description"],
                        port_data["serial_number"] or "N/A",
                        port_data["vid"] or 0,
                        port_data["pid"] or 0,
                        self._guess_chip_name(port_data["vid"]),
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

    def get_known_ports(self) -> dict:
        """← NUEVO: Retorna los puertos actualmente conocidos."""
        return dict(self._known_ports)

    def is_port_connected(self, port: str) -> bool:
        """← NUEVO: Verifica si un puerto específico sigue conectado."""
        return port in self._known_ports

    @staticmethod
    def _is_likely_arduino(port) -> bool:
        """
        Determina si un puerto serial es probablemente un Arduino.
        Usa múltiples heurísticas para no depender solo de serial_number.
        """
        # 1. Nombre de dispositivo típico en Linux
        device_name = port.device.lower()
        if "ttyusb" in device_name or "ttyacm" in device_name:
            # Es un puerto serial USB, verificar si el chip es conocido
            if port.vid is not None and port.vid in KNOWN_ARDUINO_VIDS:
                return True

            # Si no tenemos VID, confiar en la descripción
            desc = (port.description or "").lower()
            arduino_keywords = [
                "arduino", "ch340", "ch341", "ft232", "cp210",
                "usb-serial", "usb serial", "serial"
            ]
            if any(kw in desc for kw in arduino_keywords):
                return True

        # 2. macOS: /dev/cu.usbserial* o /dev/cu.usbmodem*
        if "usbserial" in device_name or "usbmodem" in device_name:
            return True

        # 3. Windows: COMx con VID conocido
        if port.vid is not None and port.vid in KNOWN_ARDUINO_VIDS:
            return True

        return False

    @staticmethod
    def _guess_chip_name(vid: int | None) -> str:
        """Retorna nombre legible del chip basado en VID."""
        if vid is None:
            return "Desconocido"
        names = {
            0x0403: "FTDI",
            0x1A86: "WCH CH340/CH341",
            0x10C4: "Silicon Labs CP210x",
            0x2341: "Arduino",
            0x2A03: "Arduino (Genuino)",
            0x239A: "Adafruit",
            0x0483: "STMicroelectronics",
            0x16C0: "Teensy",
        }
        return names.get(vid, f"VID:{vid:04X}")