"""
logic/exporter.py
Exportación de datos a CSV y JSON.

Uso:
    exporter = DataExporter(db)
    exporter.export_readings(parcela_id, start, end, fmt="csv", filepath="datos.csv")
    exporter.export_events(parcela_id, start, end, fmt="json", filepath="eventos.json")
"""
from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path

from data.database import Database


class DataExporter:
    def __init__(self, db: Database):
        self._db = db

    # ------------------------------------------------------------------
    # Lecturas de sensores
    # ------------------------------------------------------------------
    def export_readings(self, parcela_id: str,
                        start: datetime | None = None,
                        end: datetime | None = None,
                        fmt: str = "csv",
                        filepath: str | Path = "lecturas.csv") -> bool:
        """
        Exporta las lecturas de sensores de una parcela en un rango de fechas.
        Retorna True si se escribió correctamente.
        """
        rows = self._db.get_readings(parcela_id, start=start, end=end)
        if not rows:
            return False

        if fmt == "json":
            return self._write_json(filepath, rows)
        else:
            return self._write_csv(filepath, rows,
                                   fieldnames=["ts", "hum_suelo", "hum_aire", "temp"])

    # ------------------------------------------------------------------
    # Eventos
    # ------------------------------------------------------------------
    def export_events(self, parcela_id: str,
                      start: datetime | None = None,
                      end: datetime | None = None,
                      fmt: str = "csv",
                      filepath: str | Path = "eventos.csv") -> bool:
        """
        Exporta el historial de eventos de una parcela.
        """
        rows = self._db.get_events(parcela_id, start=start, end=end)
        if not rows:
            return False

        if fmt == "json":
            return self._write_json(filepath, rows)
        else:
            return self._write_csv(filepath, rows,
                                   fieldnames=["ts", "tipo", "descripcion"])

    # ------------------------------------------------------------------
    # Configuración actual (snapshot)
    # ------------------------------------------------------------------
    def export_config(self, parcela_id: str,
                      fmt: str = "json",
                      filepath: str | Path = "config.json") -> bool:
        """
        Exporta la configuración actual de una parcela (umbrales, modo, etc.).
        """
        parcela = self._db.get_parcela(parcela_id)
        if not parcela:
            return False
        data = {
            "id": parcela.get("id"),
            "name": parcela.get("name"),
            "umbral_min": parcela.get("umbral_min"),
            "umbral_max": parcela.get("umbral_max"),
            "modo": parcela.get("modo"),
            "exported_at": datetime.now().isoformat(),
        }
        if fmt == "json":
            return self._write_json(filepath, [data])
        else:
            return self._write_csv(filepath, [data],
                                   fieldnames=["id", "name", "umbral_min", "umbral_max", "modo"])

    # ------------------------------------------------------------------
    # Helpers internos
    # ------------------------------------------------------------------
    @staticmethod
    def _write_csv(filepath: str | Path, rows: list[dict],  # ← tipos explícitos
                   fieldnames: list[str]) -> bool:
        try:
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
                writer.writeheader()
                for r in rows:
                    writer.writerow(r)
            return True
        except OSError:
            return False

    @staticmethod
    def _write_json(filepath: str | Path, rows: list[dict]) -> bool:  # ← tipos explícitos
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(rows, f, default=str, indent=2, ensure_ascii=False)
            return True
        except OSError:
            return False
