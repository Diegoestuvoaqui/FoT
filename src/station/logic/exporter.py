# logic/exporter.py
import csv
import json
from datetime import datetime
from pathlib import Path

from data.database import Database


class DataExporter:
    def __init__(self, db: Database):
        self._db = db

    def export_readings(self, board_id: str,
                        sensor_type: str | None = None,
                        start: datetime | None = None,
                        end: datetime | None = None,
                        fmt: str = "csv",
                        filepath: str | Path = "lecturas.csv") -> bool:
        rows = self._db.get_readings(board_id, sensor_type, start=start, end=end)
        if not rows:
            return False

        if fmt == "json":
            return self._write_json(filepath, rows)
        else:
            return self._write_csv(filepath, rows,
                                   fieldnames=["ts_base", "sensor_type", "valor", "unidad", "ts_arduino"])

    def export_events(self, board_id: str,
                      start: datetime | None = None,
                      end: datetime | None = None,
                      fmt: str = "csv",
                      filepath: str | Path = "eventos.csv") -> bool:
        rows = self._db.get_events(board_id, start=start, end=end)
        if not rows:
            return False

        if fmt == "json":
            return self._write_json(filepath, rows)
        else:
            return self._write_csv(filepath, rows,
                                   fieldnames=["ts", "tipo", "descripcion"])

    @staticmethod
    def _write_csv(filepath, rows, fieldnames):
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
    def _write_json(filepath, rows):
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(rows, f, default=str, indent=2, ensure_ascii=False)
            return True
        except OSError:
            return False