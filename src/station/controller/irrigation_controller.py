# controller/irrigation_controller.py
import logging

from station.service.irrigation_service import IrrigationService

logger = logging.getLogger(__name__)


class IrrigationController:
    """
    Adaptador entre la UI (botones de riego en MainPanel) y IrrigationService.
    Sin lógica de negocio; solo traduce clicks del usuario en comandos al servicio.
    """

    def __init__(self, irrigation_service: IrrigationService):
        self._service = irrigation_service

    # ------------------------------------------------------------------
    # Comandos de riego
    # ------------------------------------------------------------------
    def irrigate(self, parcela_id: str | None) -> bool:
        """Activa el riego en la parcela seleccionada."""
        if not parcela_id:
            logger.warning("Irrigate llamado sin parcela seleccionada")
            return False
        self._service.irrigate(parcela_id)
        return True

    def stop(self, parcela_id: str | None) -> bool:
        """Detiene el riego en la parcela seleccionada."""
        if not parcela_id:
            logger.warning("Stop llamado sin parcela seleccionada")
            return False
        self._service.stop(parcela_id)
        return True

    # ------------------------------------------------------------------
    # Modo y umbrales (delegados en ParcelaController, pero expuestos aquí si se necesitan)
    # ------------------------------------------------------------------
    def set_mode(self, parcela_id: str | None, mode: str) -> bool:
        """Cambia el modo de la parcela."""
        if not parcela_id:
            return False
        self._service.set_mode(parcela_id, mode)
        return True
