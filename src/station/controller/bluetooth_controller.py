# controller/bluetooth_controller.py
import logging

from service.bluetooth_service import BluetoothService

logger = logging.getLogger(__name__)


class BluetoothController:
    """
    Adaptador entre BluetoothScanDialog y BluetoothService.
    """

    def __init__(self, on_device_found=None, on_scan_complete=None):
        self._service = BluetoothService(
            on_device_found=on_device_found,
            on_scan_complete=on_scan_complete,
        )

    def scan(self) -> list[dict]:
        """Escaneo sincrónico. Retorna lista de dispositivos."""
        return self._service.scan()

    def scan_async(self) -> None:
        """Escaneo asincrónico en hilo."""
        self._service.scan_async()

    def is_scanning(self) -> bool:
        return self._service.is_scanning()