# controller/wifi_controller.py
import logging

from service.wifi_service import WiFiService

logger = logging.getLogger(__name__)


class WiFiController:
    """
    Adaptador entre WiFiScanDialog y WiFiService.
    """

    def __init__(self, on_device_found=None, on_scan_complete=None):
        self._service = WiFiService(
            on_device_found=on_device_found,
            on_scan_complete=on_scan_complete,
        )

    def scan(self) -> list[dict]:
        """Escaneo sincrónico. Retorna lista de dispositivos WiFi."""
        return self._service.scan()

    def scan_async(self) -> None:
        """Escaneo asincrónico en hilo."""
        self._service.scan_async()

    def is_scanning(self) -> bool:
        return self._service.is_scanning()