"""Descubrimiento mDNS del broker embebido en la LAN.

Los nodos ESP32 localizan la estación consultando el servicio
`_mqtt._tcp.local.` ("FoT Broker") en lugar de depender de una IP fija
(la IP de la PC puede cambiar según la red). Si mDNS falla, el nodo usa
la IP configurada en secrets.h como respaldo.
"""

from __future__ import annotations

import logging
import socket

from zeroconf import ServiceInfo, Zeroconf

logger = logging.getLogger(__name__)

SERVICE_TYPE = "_mqtt._tcp.local."
SERVICE_NAME = "FoT Broker"


def _lan_ip() -> str:
    """IP de la interfaz de la ruta por defecto (sin enviar trafico real)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


class BrokerDiscovery:
    def __init__(self, port: int = 1883, name: str = SERVICE_NAME):
        self._port = port
        self._name = name
        self._zc: Zeroconf | None = None
        self._info: ServiceInfo | None = None

    def start(self) -> None:
        ip = _lan_ip()
        self._zc = Zeroconf()
        self._info = ServiceInfo(
            SERVICE_TYPE,
            f"{self._name}.{SERVICE_TYPE}",
            addresses=[socket.inet_aton(ip)],
            port=self._port,
            properties={"path": "/"},
        )
        self._zc.register_service(self._info)
        logger.info("mDNS: '%s' anunciado en %s:%s (%s)",
                    self._name, ip, self._port, SERVICE_TYPE)

    def stop(self) -> None:
        if self._zc is not None:
            try:
                if self._info is not None:
                    self._zc.unregister_service(self._info)
            finally:
                self._zc.close()
                self._zc = None
                self._info = None
