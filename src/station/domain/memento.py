# domain/memento.py
import json
import logging
from datetime import datetime

from data.database import Database

logger = logging.getLogger(__name__)


class ConfigSnapshot:
    def __init__(self, state: str, timestamp: str = ""):
        self._state = state
        self._timestamp = timestamp or datetime.now().isoformat(timespec="seconds")

    def get_state(self) -> str:
        return self._state

    def get_timestamp(self) -> str:
        return self._timestamp


class ConfigManager:
    def save_snapshot(self, boards: list, descripcion: str,
                      db: Database, usuario_id: int | None = None):
        state_dict = {"boards": [self._serialize_board(b) for b in boards]}
        state_json = json.dumps(state_dict, ensure_ascii=False, indent=None)
        db.save_snapshot(usuario_id, descripcion, state_json)
        return ConfigSnapshot(state=state_json)

    def list_snapshots(self, db: Database, usuario_id: int | None = None) -> list[dict]:
        return db.get_snapshots(usuario_id)

    def restore_snapshot(self, snapshot_id: int, db: Database) -> dict:
        row = db.get_snapshot(snapshot_id)
        if row is None:
            return {}
        try:
            return json.loads(row["datos_json"])
        except json.JSONDecodeError:
            return {}

    def _serialize_board(self, board) -> dict:
        return {
            "id": board.id,
            "conn": board.conn,
            "port": board.port,
            "sketch_id": board.sketch_id,
            "sketch_name": board.sketch_name,
            "sketch_version": board.sketch_version,
            "status": board.status,
        }