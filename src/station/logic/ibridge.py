# src/station/logic/ibridge.py
"""Interfaz común de los bridges que administra SensorManager (Facade)."""
from __future__ import annotations

from abc import ABC, abstractmethod


class IBridge(ABC):
    """Contrato que cumple cualquier transporte (Serial/BT/WiFi).

    SensorManager solo interactúa con esta interfaz, sin importar el tipo.
    """

    @abstractmethod
    def connect(self) -> bool:
        """Prepara el transporte. Devuelve True si quedó operativo."""

    @abstractmethod
    def disconnect(self) -> None:
        """Cierra el transporte (idempotente)."""

    @abstractmethod
    def is_connected(self) -> bool:
        """¿El transporte tiene canal vivo ahora mismo?"""

    @abstractmethod
    def send_command(self, cmd: dict) -> bool:
        """Envía un comando. Devuelve True si se pudo entregar al menos
        al sistema de transporte (no confirma recepción del nodo)."""

    @abstractmethod
    def check_timeout(self) -> bool:
        """Devuelve True si sigue vivo. Si venció, notifica y devuelve False."""

    def mark_seen(self) -> None:
        """Señal de vida recibida. En transportes orientados a socket es
        no-op; en WiFi es la única forma de pasar a 'conectado'."""

    def set_timeout(self, seconds: float) -> None:
        """Ajusta el timeout de inactividad (solo WiFi lo usa de verdad)."""