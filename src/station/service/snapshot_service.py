# service/snapshot_service.py
import logging

from data.database import Database
from domain.components import Finca
from domain.memento import ConfigManager

logger = logging.getLogger(__name__)


class SnapshotService:
    """
    Gestiona snapshots de configuración de la finca.
    Envuelve ConfigManager para desacoplar la UI de la lógica de memento.
    """

    def __init__(self,
                 finca: Finca,
                 db: Database,
                 config_manager: ConfigManager,
                 event_service,
                 usuario_id: int):
        self._finca = finca
        self._db = db
        self._config_manager = config_manager
        self._event_service = event_service
        self._usuario_id = usuario_id

    # ------------------------------------------------------------------
    # Operaciones
    # ------------------------------------------------------------------
    def save_manual(self) -> None:
        """Guarda un snapshot manual con descripción genérica."""
        self._config_manager.save_snapshot(
            self._finca,
            "Instantánea manual",
            self._db
        )
        self._event_service.log(
            parcela_id="system",
            descripcion="Instantánea de configuración guardada",
            tipo="config"
        )
        logger.info("Snapshot manual guardado")

    def save_before_change(self, description: str) -> None:
        """
        Guarda un snapshot antes de una modificación.
        Usado internamente por otros servicios (ParcelaService, etc.).
        """
        self._config_manager.save_snapshot(
            self._finca,
            description,
            self._db
        )
        logger.info("Snapshot guardado: %s", description)

    def list_all(self) -> list[dict]:
        """Retorna todos los snapshots ordenados del más reciente al más antiguo."""
        return self._config_manager.list_snapshots(self._db)

    def restore(self, snapshot_id: int) -> dict:
        """
        Retorna el estado deserializado de un snapshot.
        La UI es responsable de reconstruir el modelo con estos datos.
        """
        return self._config_manager.restore_snapshot(snapshot_id, self._db)
