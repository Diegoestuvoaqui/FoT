# service/snapshot_service.py
import logging

from data.database import Database
from domain.memento import ConfigManager

logger = logging.getLogger(__name__)


class SnapshotService:
    def __init__(self,
                 db: Database,
                 config_manager: ConfigManager,
                 event_service,
                 usuario_id: int):
        self._db = db
        self._config_manager = config_manager
        self._event_service = event_service
        self._usuario_id = usuario_id

    def save_manual(self, boards: list) -> None:
        self._config_manager.save_snapshot(
            boards,
            "Instantánea manual",
            self._db,
            self._usuario_id
        )
        self._event_service.log(
            board_id=None,
            descripcion="Instantánea de configuración guardada",
            tipo="config"
        )

    def list_all(self) -> list[dict]:
        return self._config_manager.list_snapshots(self._db)

    def restore(self, snapshot_id: int) -> dict:
        return self._config_manager.restore_snapshot(snapshot_id, self._db)