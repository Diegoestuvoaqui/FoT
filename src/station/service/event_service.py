# service/event_service.py
import logging

logger = logging.getLogger(__name__)


class EventService:
    def __init__(self, db):
        self._db = db
        self._observers = []

    def add_observer(self, callback):
        self._observers.append(callback)

    def remove_observer(self, callback):
        self._observers.remove(callback)

    def log(self, board_id: str | None, descripcion: str, tipo: str = "") -> None:
        mapped_tipo = self._map_type(tipo)
        self._db.save_event(board_id, tipo, descripcion)
        for obs in self._observers:
            obs(descripcion, mapped_tipo)

    def load_history(self, board_id: str | None = None) -> list[dict]:
        events = []
        for e in reversed(self._db.get_events(board_id, limit=20)):
            ts = e.get("ts", "")
            tipo = e.get("tipo", "")
            desc = e.get("descripcion", "")
            mapped = self._map_type(tipo)
            events.append({
                "text": f"[{ts}] {tipo} — {desc}",
                "tipo": mapped,
            })
        return events

    @staticmethod
    def _map_type(tipo_evento: str) -> str:
        tipo = tipo_evento.lower()
        if "error" in tipo or "fallo" in tipo:
            return "error"
        if "conexion" in tipo or "desconexion" in tipo:
            return "conexion"
        return ""