# logic/data_receiver.py
import logging

from data.database import Database

logger = logging.getLogger(__name__)


class DataReceiver:
    def __init__(self, db: Database):
        self._db = db

    def on_reading(self, board_id: str, data: dict) -> None:
        readings = data.get("data", {})
        ts = data.get("ts", 0)

        for sensor_name, sensor_data in readings.items():
            if isinstance(sensor_data, dict) and "value" in sensor_data:
                try:
                    self._db.save_reading(
                        board_id=board_id,
                        sensor_type=sensor_name,
                        valor=float(sensor_data["value"]),
                        unidad=sensor_data.get("unit", ""),
                        raw_data=str(data),
                        ts_arduino=ts,
                    )
                except Exception as e:
                    logger.error("Error guardando lectura: %s", e)

    def on_identify(self, board_id: str, data: dict) -> None:
        logger.info("Sketch identificado en %s: %s v%s (%s sensores)",
                    board_id,
                    data.get("name", "unknown"),
                    data.get("version", "?"),
                    data.get("sensors", 0))