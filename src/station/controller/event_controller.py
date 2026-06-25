# controller/event_controller.py
import logging

from service.event_service import EventService

logger = logging.getLogger(__name__)


class EventController:
    def __init__(self, event_service: EventService):
        self._event_service = event_service
        self._ui_callback = None

    def set_ui_callback(self, callback):
        """La UI registra callback para recibir eventos."""
        self._ui_callback = callback
        self._event_service.add_observer(self._on_service_event)

    def cleanup(self):
        """Desuscribirse del servicio al cerrar la ventana."""
        if self._ui_callback:
            self._event_service.remove_observer(self._on_service_event)
            self._ui_callback = None

    # ------------------------------------------------------------------
    # Callback interno — recibe del servicio y redirige a UI
    # ------------------------------------------------------------------
    def _on_service_event(self, text: str, tipo: str):
        """Llamado por EventService cuando hay un nuevo evento."""
        if self._ui_callback:
            self._ui_callback(text, tipo)

    # ------------------------------------------------------------------
    # Operaciones públicas (llamadas desde la UI)
    # ------------------------------------------------------------------
    def append(self, parcela_id: str, descripcion: str, tipo: str = "") -> None:
        """
        La UI puede forzar el log de un evento (ej: acciones manuales).
        Normalmente los servicios logean solos; esto es para casos especiales.
        """
        self._event_service.log(parcela_id, descripcion, tipo)

    def load_history(self, finca) -> list[dict]:
        """
        La UI llama esto al iniciar para cargar el historial previo.
        Retorna lista de dicts {text, tipo} para que la UI itere.
        """
        return self._event_service.load_history(finca)
