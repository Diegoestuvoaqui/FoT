# service/export_service.py
import logging
from datetime import datetime
from typing import Optional

from logic.exporter import DataExporter

logger = logging.getLogger(__name__)


class ExportService:
    def __init__(self, db):
        self._db = db
        self._exporter = DataExporter(db)

    def get_boards_for_export(self, sketch_id: str | None = None) -> list[dict]:
        if sketch_id:
            rows = self._db.get_boards_by_sketch(sketch_id)
        else:
            rows = self._db.get_all_boards()
        return [{"id": r["id"], "name": r.get("sketch_name") or r["id"]} for r in rows]

    def export(self,
               board_id: str,
               format: str,
               output_path: str,
               start_date: Optional[datetime] = None,
               end_date: Optional[datetime] = None,
               sensor_type: str | None = None,
               tipo: str = "lecturas") -> tuple[bool, str]:
        try:
            if tipo == "lecturas":
                ok = self._exporter.export_readings(
                    board_id, sensor_type, start_date, end_date, format, output_path
                )
            elif tipo == "eventos":
                ok = self._exporter.export_events(
                    board_id, start_date, end_date, format, output_path
                )
            else:
                return False, f"Tipo no soportado: {tipo}"

            if ok:
                return True, f"Datos exportados a {output_path}"
            else:
                return False, "No hay datos para exportar o error de escritura"

        except Exception as e:
            logger.error("Error en exportación: %s", e)
            return False, str(e)