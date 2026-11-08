# src/station/logic/bluetooth_bridge.py
"""Bridge para HC-05/06 vía RFCOMM (pyserial sobre /dev/rfcommN)."""
from __future__ import annotations

import logging
import time

from logic.serial_bridge import SerialBridge

logger = logging.getLogger(__name__)


class BluetoothBridge(SerialBridge):
    """SerialBridge adaptado a las particularidades del HC-05/06."""

    def __init__(self,
                 port: str = "/dev/rfcomm0",
                 baud: int = 9600,
                 **kwargs):
        super().__init__(port=port, baud=baud, **kwargs)
        logger.info("BluetoothBridge creado para %s", port)

    def connect(self) -> bool:
        ok = super().connect()
        if ok:
            # El HC-05 necesita un momento extra tras abrir el puerto.
            time.sleep(0.5)
        return ok