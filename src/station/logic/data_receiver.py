# logic/data_receiver.py
import logging

from data.database import Database
from domain.components import Finca

logger = logging.getLogger(__name__)


class DataReceiver:
    """
    Observer concreto — solo persiste datos y actualiza el modelo de dominio.
    No evalúa umbrales, no publica comandos, no tiene lógica de riego.
    """

    def __init__(self, db: Database, finca: Finca | None = None):
        self._db = db
        self._finca = finca

    def set_finca(self, finca: Finca) -> None:
        """Asigna la finca después de la autenticación del usuario."""
        self._finca = finca

    # --------------------------------------------------------------------------
    # Interfaz Observer
    # --------------------------------------------------------------------------
    def on_event(self, topic: str, data: dict) -> None:
        try:
            parcela_id = topic.split("/")[1]
        except IndexError:
            logger.warning("Tópico con formato inesperado: %s", topic)
            return

        if topic.endswith("/sensores"):
            self._handle_sensores(parcela_id, data)
        elif topic.endswith("/estado"):
            self._handle_estado(parcela_id, data)
        else:
            logger.debug("Tópico no manejado por DataReceiver: %s", topic)

    # --------------------------------------------------------------------------
    # Handlers privados
    # --------------------------------------------------------------------------
    def _handle_sensores(self, parcela_id: str, data: dict) -> None:
        # 1. Persistir en base de datos
        try:
            self._db.save_reading(parcela_id, data)
        except Exception as e:
            logger.error("Error guardando lectura de %s: %s", parcela_id, e)

        # 2. Actualizar modelo de dominio directamente en la parcela
        if self._finca is None:
            logger.debug("Finca no asignada aún, lectura solo en BD")
            return

        parcela = self._finca.get_parcela(parcela_id)
        if parcela is None:
            logger.warning("Lectura recibida de parcela desconocida: %s", parcela_id)
            return

        parcela.update_reading(data)

    def _handle_estado(self, parcela_id: str, data: dict) -> None:
        if self._finca is None:
            return

        parcela = self._finca.get_parcela(parcela_id)
        if parcela is None:
            logger.warning("Estado recibido de parcela desconocida: %s", parcela_id)
            return

        # 1. Actualizar modo y estado FSM en el modelo de dominio
        state = data.get("state", "")
        if state in ("Monitoring",):
            parcela.modo = "auto"
        elif state in ("Idle",):
            parcela.modo = "manual"
        # Irrigating y Fault no cambian el modo — solo reflejan un estado transitorio

        parcela.fsm_state = state  # atributo dinámico — la UI lo lee para el color
        parcela.relay_on = data.get("relay", False)

        # 2. Persistir evento de fallo
        if state == "Fault":
            try:
                self._db.save_event(parcela_id, "fault", str(data))
            except Exception as e:
                logger.error("Error guardando evento fault de %s: %s", parcela_id, e)
