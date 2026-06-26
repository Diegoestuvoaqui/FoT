# src/station/logic/bluetooth_bridge.py
"""
Bridge para Bluetooth (HC-05/06) usando pyserial con RFCOMM.
En Linux, los dispositivos BT aparecen como /dev/rfcomm0, /dev/rfcomm1, etc.
"""
from __future__ import annotations

import logging

from logic.serial_bridge import SerialBridge

logger = logging.getLogger(__name__)


class BluetoothBridge(SerialBridge):
    """
    Extensión de SerialBridge para Bluetooth.
    El HC-05/06 se comporta como un puerto serial estándar una vez emparejado.
    """

    def __init__(self,
                 port: str = "/dev/rfcomm0",
                 baud: int = 9600,  # HC-05 default
                 **kwargs):
        super().__init__(port=port, baud=baud, **kwargs)
        logger.info("BluetoothBridge creado para %s", port)

    def connect(self) -> bool:
        ok = super().connect()
        if ok:
            # El HC-05 necesita un momento para estabilizar
            import time
            time.sleep(0.5)
        return ok
