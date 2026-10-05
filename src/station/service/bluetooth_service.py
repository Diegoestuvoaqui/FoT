# service/bluetooth_service.py
import logging
import subprocess
import threading
import time

import serial.tools.list_ports

logger = logging.getLogger(__name__)


class BluetoothService:
    """
    Escanea dispositivos Bluetooth seriales (HC-05/06) emparejados.
    En Linux aparecen como /dev/rfcomm0, /dev/rfcomm1, etc.
    """

    def __init__(self, on_device_found=None, on_scan_complete=None):
        self._on_device_found = on_device_found   # callback(board_id, port)
        self._on_scan_complete = on_scan_complete  # callback(list[dict])
        self._scanning = False
        self._thread: threading.Thread | None = None

    def scan(self) -> list[dict]:
        """
        Escanea sincrónicamente. Retorna lista de dicts:
        [{"id": "rfcomm0", "port": "/dev/rfcomm0", "name": "HC-05", "type": "bluetooth"}]
        """
        devices = []
        try:
            # Listar puertos rfcomm
            ports = list(serial.tools.list_ports.comports())
            for p in ports:
                if "rfcomm" in p.device:
                    devices.append({
                        "id": p.device.replace("/dev/", ""),
                        "port": p.device,
                        "name": p.description or "Bluetooth",
                        "type": "bluetooth",
                        "hwid": p.hwid,
                    })
                    if self._on_device_found:
                        self._on_device_found(p.device.replace("/dev/", ""), p.device)
        except Exception as e:
            logger.error("Error escaneando Bluetooth: %s", e)

        if self._on_scan_complete:
            self._on_scan_complete(devices)

        return devices

    def scan_async(self) -> None:
        """Inicia escaneo en hilo separado."""
        if self._scanning:
            return
        self._scanning = True
        self._thread = threading.Thread(target=self._scan_thread, daemon=True)
        self._thread.start()

    def _scan_thread(self):
        try:
            self.scan()
        finally:
            self._scanning = False

    def is_scanning(self) -> bool:
        return self._scanning