# service/export_service.py
import logging
from datetime import datetime
from typing import Optional

from logic.exporter import DataExporter

logger = logging.getLogger(__name__)


class ExportService:
    """
    Orquesta la exportación de datos de parcelas.
    Recolecta los datos de la BD y delega en DataExporter para generar archivos.
    """

    def __init__(self, db):
        self._db = db
        self._exporter = DataExporter(db)

    # ------------------------------------------------------------------
    # Datos para la UI
    # ------------------------------------------------------------------
    def get_parcelas_for_export(self, finca) -> list[dict]:
        """
        Retorna la lista de parcelas para poblar el diálogo de exportación.
        """
        return [
            {"id": p.get_id(), "name": p.get_name()}
            for p in finca.get_children()
        ]

    # ------------------------------------------------------------------
    # Exportación
    # ------------------------------------------------------------------
    def export(self,
               parcela_id: str,
               format: str,  # "csv" | "json"
               output_path: str,
               start_date: Optional[datetime] = None,
               end_date: Optional[datetime] = None,
               tipo: str = "lecturas") -> tuple[bool, str]:
        """
        Exporta datos de una parcela.
        tipo: "lecturas" | "eventos" | "config"
        Retorna (éxito, mensaje).
        """
        try:
            if tipo == "lecturas":
                ok = self._exporter.export_readings(
                    parcela_id, start_date, end_date, format, output_path
                )
            elif tipo == "eventos":
                ok = self._exporter.export_events(
                    parcela_id, start_date, end_date, format, output_path
                )
            elif tipo == "config":
                ok = self._exporter.export_config(
                    parcela_id, format, output_path
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
