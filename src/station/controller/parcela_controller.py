# controller/parcela_controller.py
import logging

from service.parcela_service import ParcelaService

logger = logging.getLogger(__name__)


class ParcelaController:
    """
    Adaptador entre la UI (MainPanel) y ParcelaService.
    """

    def __init__(self,
                 parcela_service: ParcelaService,
                 on_refresh_ui=None,
                 on_select_ui=None):
        self._service = parcela_service
        self._on_refresh_ui = on_refresh_ui
        self._on_select_ui = on_select_ui
        self._selected_id: str | None = None

        self._service.add_observer(self._on_service_changed)

    # ------------------------------------------------------------------
    # Callbacks para la UI
    # ------------------------------------------------------------------
    def set_ui_callback(self, on_refresh=None, on_select=None):
        """La UI registra callbacks para ser notificada de cambios."""
        self._on_refresh_ui = on_refresh
        self._on_select_ui = on_select

    # ------------------------------------------------------------------
    # Callback interno
    # ------------------------------------------------------------------
    def _on_service_changed(self):
        if self._on_refresh_ui:
            self._on_refresh_ui()

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------
    def add_parcela(self, parcela_id: str, name: str) -> tuple[bool, str]:
        """
        Crea una nueva parcela.
        Retorna (éxito, mensaje_error). Si éxito=True, mensaje_error="".
        """
        try:
            self._service.create(parcela_id, name)
            return True, ""
        except ValueError as e:
            logger.warning("Error al crear parcela: %s", e)
            return False, str(e)
        except RuntimeError as e:
            logger.error("Error de BD al crear parcela: %s", e)
            return False, "Error de escritura en base de datos"

    def delete_parcela(self, parcela_id: str | None) -> tuple[bool, str]:
        """
        Elimina una parcela con confirmación del usuario.
        La UI debe mostrar el diálogo de confirmación antes de llamar esto.
        """
        if not parcela_id:
            return False, "ID de parcela requerido"

        try:
            if self._service.get(parcela_id) is None:
                return False, "Parcela no encontrada"

            self._service.delete(parcela_id)

            if self._selected_id == parcela_id:
                self._selected_id = None
                if self._on_select_ui:
                    self._on_select_ui(None)

            return True, ""
        except ValueError as e:
            return False, str(e)
        except RuntimeError as e:
            return False, "Error de escritura en base de datos"

    # ------------------------------------------------------------------
    # Selección
    # ------------------------------------------------------------------
    def select_parcela(self, parcela_id: str | None):
        self._selected_id = parcela_id
        if not parcela_id:
            return None
        return self._service.get(parcela_id)

    def list_parcelas(self):
        return self._service.list_all()

    # ------------------------------------------------------------------
    # Umbrales
    # ------------------------------------------------------------------
    def apply_thresholds(self, parcela_id: str | None, min_str: str, max_str: str) -> tuple[bool, str]:
        if not parcela_id:
            return False, "Ninguna parcela seleccionada"

        try:
            self._service.set_thresholds(parcela_id, min_str, max_str)
            return True, ""
        except ValueError as e:
            return False, str(e)
        except RuntimeError as e:
            return False, "Error de escritura en base de datos"

    # ------------------------------------------------------------------
    # Modo
    # ------------------------------------------------------------------
    def change_mode(self, parcela_id: str | None, value: str) -> tuple[bool, str]:
        if not parcela_id:
            return False, "Ninguna parcela seleccionada"

        try:
            self._service.set_mode(parcela_id, value)
            return True, ""
        except ValueError as e:
            return False, str(e)
