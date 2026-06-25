# controller/snapshot_controller.py
import logging

from station.service.snapshot_service import SnapshotService

logger = logging.getLogger(__name__)


class SnapshotController:
    """
    Adaptador entre la UI y SnapshotService.
    Expone acciones de snapshot al usuario (guardar manual, listar, restaurar).
    """

    def __init__(self, snapshot_service: SnapshotService):
        self._service = snapshot_service

    # ------------------------------------------------------------------
    # Operaciones
    # ------------------------------------------------------------------
    def save_manual(self) -> None:
        """El usuario solicita guardar un snapshot manual."""
        self._service.save_manual()

    def list_snapshots(self) -> list[dict]:
        """
        Retorna todos los snapshots para mostrar en un diálogo de restauración.
        """
        return self._service.list_all()

    def restore(self, snapshot_id: int) -> dict:
        """
        Restaura un snapshot. Retorna el dict deserializado.
        La UI es responsable de reconstruir el modelo con estos datos.
        """
        return self._service.restore(snapshot_id)
