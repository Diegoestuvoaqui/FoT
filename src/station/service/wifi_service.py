# service/wifi_service.py
import logging
import socket
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


class WiFiService:
    """
    Detecta placas Arduino UNO R4 WiFi en la red local.
    Escaneo concurrente con cancelación y timeouts agresivos.
    """

    DEFAULT_MQTT_PORT = 1883
    SCAN_TIMEOUT = 0.3  # ← reducido de 0.5s
    COMMON_IPS = ["192.168.1.100", "192.168.1.101", "192.168.1.102",
                  "192.168.0.100", "192.168.0.101"]

    def __init__(self, on_device_found=None, on_scan_complete=None):
        self._on_device_found = on_device_found
        self._on_scan_complete = on_scan_complete
        self._scanning = False
        self._cancelled = False  # ← NUEVO: flag de cancelación
        self._thread: threading.Thread | None = None
        self._executor: ThreadPoolExecutor | None = None

    def _probe_ip(self, ip: str, port: int = 80) -> tuple[bool, float]:
        """
        Prueba si hay algo respondiendo en esa IP.
        Retorna (respondió, tiempo_ms).
        """
        if self._cancelled:
            return False, 0.0

        start = time.time()
        try:
            with socket.create_connection((ip, port), timeout=self.SCAN_TIMEOUT):
                elapsed = (time.time() - start) * 1000
                return True, elapsed
        except (socket.timeout, OSError, ConnectionRefusedError):
            return False, 0.0

    def scan(self) -> list[dict]:
        """
        Escanea sincrónicamente con cancelación.
        Retorna lista de dicts.
        """
        self._scanning = True
        self._cancelled = False
        devices = []
        found_ips = set()

        # Estrategia 1: escanear IPs comunes en paralelo
        self._executor = ThreadPoolExecutor(max_workers=4)
        futures = {}

        for ip in self.COMMON_IPS:
            if self._cancelled:
                break
            # Probar puerto 80 (HTTP) y 1883 (MQTT)
            futures[self._executor.submit(self._probe_ip, ip, 80)] = (ip, 80)
            futures[self._executor.submit(self._probe_ip, ip, 1883)] = (ip, 1883)

        for future in as_completed(futures):
            if self._cancelled:
                break

            ip, port = futures[future]
            try:
                responded, elapsed = future.result()
                if responded and ip not in found_ips:
                    found_ips.add(ip)
                    device = {
                        "id": f"wifi-{ip.split('.')[-1]}",
                        "ip": ip,
                        "port": 1883,
                        "name": "UNO R4 WiFi",
                        "type": "wifi",
                        "response_ms": int(elapsed),
                    }
                    devices.append(device)
                    if self._on_device_found:
                        self._on_device_found(device["id"], ip)
            except Exception as e:
                logger.debug("Error probando %s:%s: %s", ip, port, e)

        if self._executor is not None:
            self._executor.shutdown(wait=False)
            self._executor = None

        # Estrategia 2: mDNS (solo si no cancelado)
        if not self._cancelled:
            devices.extend(self._scan_mdns())

        self._scanning = False

        if self._on_scan_complete:
            self._on_scan_complete(devices)

        return devices

    def _scan_mdns(self) -> list[dict]:
        """Escaneo mDNS con timeout corto."""
        devices = []
        try:
            from zeroconf import Zeroconf, ServiceBrowser, ServiceListener

            class MDNSListener(ServiceListener):
                def __init__(self, outer):
                    self.outer = outer
                    self.devices = []

                def add_service(self, zc, type_, name):
                    if self.outer._cancelled:
                        return
                    info = zc.get_service_info(type_, name)
                    if info and info.addresses:
                        ip = str(info.addresses[0])
                        device = {
                            "id": name.replace("._arduino._tcp.local.", ""),
                            "ip": ip,
                            "port": info.port,
                            "name": info.name,
                            "type": "wifi",
                        }
                        self.devices.append(device)
                        if self.outer._on_device_found:
                            self.outer._on_device_found(device["id"], ip)

            zc = Zeroconf()
            listener = MDNSListener(self)
            browser = ServiceBrowser(zc, "_arduino._tcp.local.", listener)

            # Esperar máximo 1.5s (reducido de 2s)
            for _ in range(15):
                if self._cancelled:
                    break
                time.sleep(0.1)

            zc.close()
            return listener.devices

        except ImportError:
            logger.debug("zeroconf no instalado, saltando mDNS")
        except Exception as e:
            logger.error("Error mDNS: %s", e)

        return devices

    def scan_async(self) -> None:
        """Inicia escaneo en hilo separado."""
        if self._scanning:
            return
        self._scanning = True
        self._cancelled = False
        self._thread = threading.Thread(target=self._scan_thread, daemon=True)
        self._thread.start()

    def _scan_thread(self):
        try:
            self.scan()
        finally:
            self._scanning = False

    def cancel(self) -> None:
        """Cancela el escaneo en curso."""
        self._cancelled = True
        if self._executor:
            self._executor.shutdown(wait=False)
            self._executor = None
        logger.info("Escaneo WiFi cancelado")

    def is_scanning(self) -> bool:
        return self._scanning