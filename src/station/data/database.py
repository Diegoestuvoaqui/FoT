import sqlite3
import threading


class Database:

    def __init__(self, db_path: str = "data/fot.db"):
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row  # filas accesibles como dict
        self._lock = threading.Lock()

    # --------------------------------------------------------------------------
    # Inicialización del esquema
    # --------------------------------------------------------------------------
    def initialize(self) -> None:
        with self._lock:
            cur = self._conn.cursor()
            cur.executescript("""
                              CREATE TABLE IF NOT EXISTS parcelas
                              (
                                  id
                                  TEXT
                                  PRIMARY
                                  KEY,
                                  name
                                  TEXT
                                  NOT
                                  NULL,
                                  umbral_min
                                  REAL
                                  DEFAULT
                                  30.0,
                                  umbral_max
                                  REAL
                                  DEFAULT
                                  70.0,
                                  modo
                                  TEXT
                                  DEFAULT
                                  'manual',
                                  created_at
                                  TEXT
                                  DEFAULT (
                                  datetime
                              (
                                  'now'
                              ))
                                  );

                              CREATE TABLE IF NOT EXISTS dispositivos
                              (
                                  id
                                  TEXT
                                  PRIMARY
                                  KEY,
                                  parcela_id
                                  TEXT
                                  NOT
                                  NULL
                                  REFERENCES
                                  parcelas
                              (
                                  id
                              ),
                                  name TEXT NOT NULL,
                                  tipo TEXT NOT NULL
                                  );

                              CREATE TABLE IF NOT EXISTS lecturas
                              (
                                  id
                                  INTEGER
                                  PRIMARY
                                  KEY
                                  AUTOINCREMENT,
                                  parcela_id
                                  TEXT
                                  NOT
                                  NULL,
                                  hum_suelo
                                  REAL,
                                  hum_aire
                                  REAL,
                                  temp
                                  REAL,
                                  ts_arduino
                                  INTEGER,
                                  ts_base
                                  TEXT
                                  DEFAULT (
                                  datetime
                              (
                                  'now'
                              ))
                                  );

                              CREATE TABLE IF NOT EXISTS eventos
                              (
                                  id
                                  INTEGER
                                  PRIMARY
                                  KEY
                                  AUTOINCREMENT,
                                  parcela_id
                                  TEXT
                                  NOT
                                  NULL,
                                  tipo
                                  TEXT
                                  NOT
                                  NULL,
                                  descripcion
                                  TEXT,
                                  ts
                                  TEXT
                                  DEFAULT (
                                  datetime
                              (
                                  'now'
                              ))
                                  );

                              CREATE TABLE IF NOT EXISTS configuracion_snapshots
                              (
                                  id
                                  INTEGER
                                  PRIMARY
                                  KEY
                                  AUTOINCREMENT,
                                  descripcion
                                  TEXT,
                                  datos_json
                                  TEXT
                                  NOT
                                  NULL,
                                  ts
                                  TEXT
                                  DEFAULT (
                                  datetime
                              (
                                  'now'
                              ))
                                  );
                              """)
            self._conn.commit()

    # --------------------------------------------------------------------------
    # Lecturas de sensores
    # --------------------------------------------------------------------------
    def save_reading(self, parcela_id: str, data: dict) -> None:
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO lecturas (parcela_id, hum_suelo, hum_aire, temp, ts_arduino)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    parcela_id,
                    data.get("hum_suelo"),
                    data.get("hum_aire"),
                    data.get("temp"),
                    data.get("ts"),
                ),
            )
            self._conn.commit()

    def get_readings(self, parcela_id: str, limit: int = 100) -> list[dict]:
        with self._lock:
            cur = self._conn.execute(
                """
                SELECT *
                FROM lecturas
                WHERE parcela_id = ?
                ORDER BY id DESC LIMIT ?
                """,
                (parcela_id, limit),
            )
            return [dict(row) for row in cur.fetchall()]

    def purge_old_readings(self, days: int = 30) -> None:
        """Elimina lecturas anteriores a N días. Llamar una vez al día desde main.py."""
        with self._lock:
            self._conn.execute(
                "DELETE FROM lecturas WHERE ts_base < datetime('now', ?)",
                (f"-{days} days",),
            )
            self._conn.commit()

    # --------------------------------------------------------------------------
    # Eventos
    # --------------------------------------------------------------------------
    def save_event(self, parcela_id: str, tipo: str, descripcion: str = "") -> None:
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO eventos (parcela_id, tipo, descripcion)
                VALUES (?, ?, ?)
                """,
                (parcela_id, tipo, descripcion),
            )
            self._conn.commit()

    def get_events(self, parcela_id: str, limit: int = 50) -> list[dict]:
        with self._lock:
            cur = self._conn.execute(
                """
                SELECT *
                FROM eventos
                WHERE parcela_id = ?
                ORDER BY id DESC LIMIT ?
                """,
                (parcela_id, limit),
            )
            return [dict(row) for row in cur.fetchall()]

    # --------------------------------------------------------------------------
    # Parcelas
    # --------------------------------------------------------------------------
    def get_parcelas(self) -> list[dict]:
        with self._lock:
            cur = self._conn.execute("SELECT * FROM parcelas ORDER BY created_at")
            return [dict(row) for row in cur.fetchall()]

    def save_parcela(self, parcela: dict) -> None:
        """UPSERT — inserta o actualiza si el id ya existe."""
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO parcelas (id, name, umbral_min, umbral_max, modo)
                VALUES (:id, :name, :umbral_min, :umbral_max, :modo) ON CONFLICT(id) DO
                UPDATE SET
                    name = excluded.name,
                    umbral_min = excluded.umbral_min,
                    umbral_max = excluded.umbral_max,
                    modo = excluded.modo
                """,
                parcela,
            )
            self._conn.commit()

    # --------------------------------------------------------------------------
    # Snapshots de configuración
    # --------------------------------------------------------------------------
    def save_snapshot(self, descripcion: str, datos_json: str) -> None:
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO configuracion_snapshots (descripcion, datos_json)
                VALUES (?, ?)
                """,
                (descripcion, datos_json),
            )
            self._conn.commit()

    def get_snapshots(self) -> list[dict]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT * FROM configuracion_snapshots ORDER BY id DESC"
            )
            return [dict(row) for row in cur.fetchall()]

    def get_snapshot(self, snapshot_id: int) -> dict | None:
        with self._lock:
            cur = self._conn.execute(
                "SELECT * FROM configuracion_snapshots WHERE id = ?",
                (snapshot_id,),
            )
            row = cur.fetchone()
            return dict(row) if row else None

    # --------------------------------------------------------------------------
    # Cierre limpio
    # --------------------------------------------------------------------------
    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def delete_parcela(self, parcela_id: str) -> None:
        with self._lock:
            self._conn.execute(
                "DELETE FROM parcelas WHERE id = ?",
                (parcela_id,)
            )
            self._conn.commit()
