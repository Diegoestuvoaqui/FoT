# logic/data_receiver.py
# Fase 3: guarda con save_reading_batch (una transacción por mensaje,
# sin raw_data duplicado). La validación completa llega en la Fase 4.
import logging
import math
import time

from data.database import Database

logger = logging.getLogger(__name__)


class DataReceiver:
    def __init__(self, db: Database):
        self._db = db

    def on_reading(self, board_id: str, data: dict) -> None:
        readings = data.get("data", {})
        ts_device = data.get("ts", 0)

        flat: dict[str, float] = {}
        for sensor_name, sensor_data in readings.items():
            if not (isinstance(sensor_data, dict) and "value" in sensor_data):
                continue
            try:
                value = float(sensor_data["value"])
            except (TypeError, ValueError):
                logger.warning("Valor no numérico de %s/%s: %r",
                               board_id, sensor_name, sensor_data["value"])
                continue
            if not math.isfinite(value):
                continue
            flat[sensor_name] = value

        if not flat:
            return
        try:
            self._db.save_reading_batch(
                board_id, flat,
                ts_utc=int(time.time()),
                ts_device_ms=ts_device,
            )
        except Exception as e:
            logger.error("Error guardando lecturas de %s: %s", board_id, e)

    def on_identify(self, board_id: str, data: dict) -> None:
        logger.info("Sketch identificado en %s: %s v%s (%s sensores)",
                    board_id, data.get("name", "unknown"),
                    data.get("version", "?"), data.get("sensors", 0))