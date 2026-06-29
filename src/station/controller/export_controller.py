# controller/export_controller.py
import logging

from service.export_service import ExportService

logger = logging.getLogger(__name__)


class ExportController:
    def __init__(self, export_service: ExportService):
        self._service = export_service

    def get_boards(self, sketch_id: str | None = None) -> list[dict]:
        return self._service.get_boards_for_export(sketch_id)

    def export(self,
               board_id: str,
               format: str,
               output_path: str,
               start_date=None,
               end_date=None,
               sensor_type: str | None = None,
               tipo: str = "lecturas") -> tuple[bool, str]:
        return self._service.export(
            board_id=board_id,
            format=format,
            output_path=output_path,
            start_date=start_date,
            end_date=end_date,
            sensor_type=sensor_type,
            tipo=tipo
        )