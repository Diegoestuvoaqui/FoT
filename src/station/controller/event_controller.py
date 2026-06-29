# controller/event_controller.py
import logging

from service.event_service import EventService

logger = logging.getLogger(__name__)


class EventController:
    def __init__(self, event_service: EventService):
        self._event_service = event_service
        self._ui_callback = None

    def set_ui_callback(self, callback):
        self._ui_callback = callback
        self._event_service.add_observer(self._on_service_event)

    def cleanup(self):
        if self._ui_callback:
            self._event_service.remove_observer(self._on_service_event)
            self._ui_callback = None

    def _on_service_event(self, text: str, tipo: str):
        if self._ui_callback:
            self._ui_callback(text, tipo)

    def append(self, board_id: str | None, descripcion: str, tipo: str = "") -> None:
        self._event_service.log(board_id, descripcion, tipo)

    def load_history(self, board_id: str | None = None) -> list[dict]:
        return self._event_service.load_history(board_id)