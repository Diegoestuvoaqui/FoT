# service/event_service.py
import logging

logger = logging.getLogger(__name__)


class EventService:
    """
    Servicio de logging de eventos.
    No importa tkinter. Recibe una lista de observadores para notificar
    cuando se registra un nuevo evento.
    """

    def __init__(self, db):
        self._db = db
        self._observers = []

    # ------------------------------------------------------------------
    # Suscripción de observadores (la UI se suscribe aquí)
    # ------------------------------------------------------------------
    def add_observer(self, callback):
        """Registra un callback on_event_logged(text, tipo)."""
        self._observers.append(callback)

    def remove_observer(self, callback):
        self._observers.remove(callback)

    # ------------------------------------------------------------------
    # Operaciones principales
    # ------------------------------------------------------------------
    def log(self, parcela_id: str, descripcion: str, tipo: str = "") -> None:
        """
        Persiste un evento en BD y notifica a todos los observadores.
        El tipo mapeado (error, riego, modo) se usa para el color en UI.
        """
        mapped_tipo = self._map_type(tipo)
        self._db.save_event(parcela_id, tipo, descripcion)
        for obs in self._observers:
            obs(descripcion, mapped_tipo)

    def load_history(self, finca) -> list[dict]:
        """
        Carga el historial de eventos de todas las parcelas.
        Devuelve una lista de dicts para que la UI itere y pinte.
        """
        events = []
        for parcela in finca.get_children():
            for e in reversed(self._db.get_events(parcela.get_id(), limit=20)):
                ts = e.get("ts", "")
                tipo = e.get("tipo", "")
                desc = e.get("descripcion", "")
                mapped = self._map_type(tipo)
                events.append({
                    "text": f"[{ts}] {tipo} — {desc}",
                    "tipo": mapped,
                })
        return events

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _map_type(tipo_evento: str) -> str:
        tipo = tipo_evento.lower()
        if "error" in tipo or "fallo" in tipo:
            return "error"
        if "riego" in tipo:
            return "riego"
        if "modo" in tipo:
            return "modo"
        return ""
