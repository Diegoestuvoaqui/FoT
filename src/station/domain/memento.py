import json
import logging
from datetime import datetime

from data.database import Database
from domain.components import Finca, Parcela

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------
# Memento — contiene el estado serializado en un momento dado
# --------------------------------------------------------------------------
class ConfigSnapshot:

    def __init__(self, state: str, timestamp: str = ""):
        self._state = state
        self._timestamp = timestamp or datetime.now().isoformat(timespec="seconds")

    def get_state(self) -> str:
        return self._state

    def get_timestamp(self) -> str:
        return self._timestamp

    def __repr__(self) -> str:
        return f"ConfigSnapshot(ts={self._timestamp!r}, bytes={len(self._state)})"


# --------------------------------------------------------------------------
# ConfigManager — Originator + Caretaker en uno
# --------------------------------------------------------------------------
class ConfigManager:

    # --------------------------------------------------------------------------
    # Guardar snapshot
    # --------------------------------------------------------------------------
    def save_snapshot(self,
                      finca: Finca,
                      descripcion: str,
                      db: Database,
                      usuario_id: int | None = None) -> ConfigSnapshot:
        """
        Serializa la jerarquía de parcelas a JSON y la persiste en la base de datos.
        """
        state_dict = self._serialize_finca(finca)
        state_json = json.dumps(state_dict, ensure_ascii=False, indent=None)

        snapshot = ConfigSnapshot(state=state_json)
        try:
            db.save_snapshot(usuario_id, descripcion, state_json)
            logger.info("Snapshot guardado: %s (usuario=%s)", descripcion, usuario_id)
        except Exception as e:
            logger.error("Error guardando snapshot: %s", e)

        return snapshot

    # --------------------------------------------------------------------------
    # Listar snapshots
    # --------------------------------------------------------------------------
    def list_snapshots(self, db: Database, usuario_id: int | None = None) -> list[dict]:
        """Retorna snapshots del usuario (o todos si es admin con None)."""
        return db.get_snapshots(usuario_id)

    # --------------------------------------------------------------------------
    # Restaurar snapshot
    # --------------------------------------------------------------------------
    def restore_snapshot(self, snapshot_id: int, db: Database) -> dict:
        """
        Retorna el dict deserializado para que la UI pueda reconstruir la jerarquía.
        """
        row = db.get_snapshot(snapshot_id)
        if row is None:
            logger.warning("Snapshot %s no encontrado", snapshot_id)
            return {}

        try:
            return json.loads(row["datos_json"])
        except json.JSONDecodeError as e:
            logger.error("Snapshot %s contiene JSON inválido: %s", snapshot_id, e)
            return {}

    # --------------------------------------------------------------------------
    # Serialización interna
    # --------------------------------------------------------------------------
    def _serialize_finca(self, finca: Finca) -> dict:
        """Convierte la jerarquía Finca → Parcelas a dict."""
        return {
            "finca_id": finca.get_id(),
            "finca_name": finca.get_name(),
            "parcelas": [
                self._serialize_parcela(p)
                for p in finca.get_children()
            ]
        }

    def _serialize_parcela(self, parcela: Parcela) -> dict:
        """Serializa una parcela (ya no tiene dispositivos, solo board_id)."""
        return {
            "id": parcela.get_id(),
            "name": parcela.get_name(),
            "usuario_id": parcela.usuario_id,
            "umbral_min": parcela.umbral_min,
            "umbral_max": parcela.umbral_max,
            "modo": parcela.modo,
            "board_id": parcela.board_id,
        }
