# src/station/logic/data_receiver.py
import logging

from data.database import Database
from domain.components import Finca

logger = logging.getLogger(__name__)


class DataReceiver:
    """
    Observer que recibe lecturas de sensores y las persiste.
    Simplificado: solo guarda datos, sin lógica de riego ni estados FSM.
    """

    def __init__(self, db: Database, finca: Finca | None = None):
        self._db = db
        self._finca = finca

    def set_finca(self, finca: Finca) -> None:
        self._finca = finca

    def on_reading(self, parcela_id: str, data: dict) -> None:
        """
        Procesa una lectura recibida de un sensor.
        data: {"ts": 12345, "data": {"temp": {"value": 22.5, "unit": "C"}, ...}, "valid": true}
        """
        if not self._finca:
            logger.debug("Finca no asignada, descartando lectura")
            return

        parcela = self._finca.get_parcela(parcela_id)
        if not parcela:
            logger.warning("Parcela desconocida: %s", parcela_id)
            return

        # Extraer valores planos para la BD
        readings = data.get("data", {})
        flat_data = {
            "ts": data.get("ts", 0),
        }

        for sensor_name, sensor_data in readings.items():
            if isinstance(sensor_data, dict) and "value" in sensor_data:
                flat_data[sensor_name] = sensor_data["value"]

        # Guardar en BD
        try:
            self._db.save_reading(parcela_id, flat_data)
        except Exception as e:
            logger.error("Error guardando lectura: %s", e)
            return

        # Actualizar modelo en memoria
        parcela.update_reading(flat_data)

        logger.debug("Lectura guardada para %s: %s", parcela_id, flat_data)

    def on_identify(self, parcela_id: str, data: dict) -> None:
        """Procesa respuesta de identificación del sketch."""
        logger.info("Sketch identificado en %s: %s v%s (%d sensores)",
                    parcela_id,
                    data.get("name", "unknown"),
                    data.get("version", "?"),
                    data.get("sensors", 0))
