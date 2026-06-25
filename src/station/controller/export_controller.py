# controller/export_controller.py
import logging

from service.export_service import ExportService

logger = logging.getLogger(__name__)


class ExportController:
    def __init__(self, export_service: ExportService):
        self._service = export_service

    def get_parcelas(self, finca) -> list[dict]:
        return self._service.get_parcelas_for_export(finca)

    def export(self,
               parcela_id: str,
               format: str,
               output_path: str,
               start_date=None,
               end_date=None,
               tipo: str = "lecturas") -> tuple[bool, str]:
        return self._service.export(
            parcela_id=parcela_id,
            format=format,
            output_path=output_path,
            start_date=start_date,
            end_date=end_date,
            tipo=tipo
        )
