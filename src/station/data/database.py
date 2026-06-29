import json
import sqlite3
import threading
from datetime import datetime


class Database:

    def __init__(self, db_path: str = "data/iot.db"):
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        self._conn.execute("PRAGMA foreign_keys = ON")

    # --------------------------------------------------------------------------
    # Inicialización
    # --------------------------------------------------------------------------
    def initialize(self) -> None:
        with self._lock:
            cur = self._conn.cursor()
            cur.executescript("""
                PRAGMA foreign_keys = ON;

                CREATE TABLE IF NOT EXISTS usuarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'user',
                    is_active INTEGER DEFAULT 1, 
                    must_change_password INTEGER DEFAULT 0, -- NUEVO: forzar cambio
                    created_at TEXT DEFAULT (datetime('now')),
                    last_login TEXT
                );

                CREATE TABLE IF NOT EXISTS boards (
                    id TEXT PRIMARY KEY,
                    usuario_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
                    conn TEXT DEFAULT 'usb',
                    port TEXT,
                    sketch_id TEXT,
                    sketch_name TEXT,
                    sketch_version TEXT DEFAULT '1.0',
                    status TEXT DEFAULT 'Sin asignar',
                    last_seen TEXT,
                    created_at TEXT DEFAULT (datetime('now')),
                    hwid TEXT,
                    vid INTEGER,
                    pid INTEGER,
                    serial_number TEXT,
                    manufacturer TEXT,
                    product TEXT,
                    location TEXT
                );

                CREATE TABLE IF NOT EXISTS boards_sensors (
                    board_id TEXT REFERENCES boards(id) ON DELETE CASCADE,
                    sensor_type TEXT NOT NULL,
                    pin TEXT,
                    enabled INTEGER DEFAULT 1,
                    config_json TEXT,
                    PRIMARY KEY (board_id, sensor_type)
                );

                CREATE TABLE IF NOT EXISTS lecturas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    board_id TEXT NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
                    sensor_type TEXT NOT NULL,
                    valor REAL,
                    unidad TEXT,
                    raw_data TEXT,
                    ts_arduino INTEGER,
                    ts_base TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS eventos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    board_id TEXT REFERENCES boards(id) ON DELETE CASCADE,
                    tipo TEXT NOT NULL,
                    descripcion TEXT,
                    ts TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS configuracion_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    usuario_id INTEGER REFERENCES usuarios(id) ON DELETE CASCADE,
                    descripcion TEXT,
                    datos_json TEXT NOT NULL,
                    ts TEXT DEFAULT (datetime('now'))
                );

                CREATE INDEX IF NOT EXISTS idx_lecturas_board_ts
                    ON lecturas(board_id, ts_base);
                CREATE INDEX IF NOT EXISTS idx_lecturas_sensor
                    ON lecturas(board_id, sensor_type);
                CREATE INDEX IF NOT EXISTS idx_eventos_board_ts
                    ON eventos(board_id, ts);
                CREATE INDEX IF NOT EXISTS idx_boards_usuario
                    ON boards(usuario_id);
                CREATE INDEX IF NOT EXISTS idx_boards_sketch
                    ON boards(sketch_id);
                CREATE INDEX IF NOT EXISTS idx_snapshots_usuario
                    ON configuracion_snapshots(usuario_id);
            """)
            self._conn.commit()

    # --------------------------------------------------------------------------
    # USUARIOS
    # --------------------------------------------------------------------------
    def create_user(self, username: str, password_hash: str, role: str = "user") -> int:
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO usuarios (username, password_hash, role) VALUES (?, ?, ?)",
                (username, password_hash, role),
            )
            self._conn.commit()
            return cur.lastrowid

    def get_user_by_username(self, username: str) -> dict | None:
        with self._lock:
            cur = self._conn.execute(
                "SELECT * FROM usuarios WHERE username = ?", (username,)
            )
            row = cur.fetchone()
            return dict(row) if row else None

    def get_user_by_id(self, user_id: int) -> dict | None:
        with self._lock:
            cur = self._conn.execute(
                "SELECT * FROM usuarios WHERE id = ?", (user_id,)
            )
            row = cur.fetchone()
            return dict(row) if row else None

    def list_users(self) -> list[dict]:
        with self._lock:
            cur = self._conn.execute("SELECT * FROM usuarios ORDER BY created_at")
            return [dict(row) for row in cur.fetchall()]

    def delete_user(self, user_id: int) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM usuarios WHERE id = ?", (user_id,))
            self._conn.commit()

    def update_user_password(self, user_id: int, password_hash: str) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE usuarios SET password_hash = ? WHERE id = ?",
                (password_hash, user_id),
            )
            self._conn.commit()

    def user_exists(self) -> bool:
        with self._lock:
            cur = self._conn.execute("SELECT 1 FROM usuarios LIMIT 1")
            return cur.fetchone() is not None

    # --------------------------------------------------------------------------
    # BOARDS
    # --------------------------------------------------------------------------
    def save_board(self, board: dict) -> None:
        if not board.get("id"):
            raise ValueError("board['id'] es obligatorio")
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO boards (
                    id, usuario_id, conn, port, sketch_id, sketch_name,
                    sketch_version, status, last_seen,
                    hwid, vid, pid, serial_number, manufacturer, product, location
                ) VALUES (
                    :id, :usuario_id, :conn, :port, :sketch_id, :sketch_name,
                    :sketch_version, :status, :last_seen,
                    :hwid, :vid, :pid, :serial_number, :manufacturer, :product, :location
                )
                ON CONFLICT(id) DO UPDATE SET
                    usuario_id = excluded.usuario_id,
                    conn = excluded.conn,
                    port = excluded.port,
                    sketch_id = excluded.sketch_id,
                    sketch_name = excluded.sketch_name,
                    sketch_version = excluded.sketch_version,
                    status = excluded.status,
                    last_seen = excluded.last_seen,
                    hwid = excluded.hwid,
                    vid = excluded.vid,
                    pid = excluded.pid,
                    serial_number = excluded.serial_number,
                    manufacturer = excluded.manufacturer,
                    product = excluded.product,
                    location = excluded.location
                """,
                board,
            )
            self._conn.commit()

    def get_board_by_id(self, board_id: str) -> dict | None:
        with self._lock:
            cur = self._conn.execute(
                "SELECT * FROM boards WHERE id = ?", (board_id,)
            )
            row = cur.fetchone()
            return dict(row) if row else None

    def get_unclaimed_boards(self) -> list[dict]:
        """Boards sin usuario asignado."""
        with self._lock:
            cur = self._conn.execute(
                "SELECT * FROM boards WHERE usuario_id IS NULL ORDER BY created_at"
            )
            return [dict(row) for row in cur.fetchall()]

    def get_boards_by_user_id(self, usuario_id: int) -> list[dict]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT * FROM boards WHERE usuario_id = ? ORDER BY created_at",
                (usuario_id,),
            )
            return [dict(row) for row in cur.fetchall()]

    def get_boards_by_sketch(self, sketch_id: str) -> list[dict]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT * FROM boards WHERE sketch_id = ? ORDER BY created_at",
                (sketch_id,),
            )
            return [dict(row) for row in cur.fetchall()]

    def get_all_boards(self) -> list[dict]:
        with self._lock:
            cur = self._conn.execute("SELECT * FROM boards ORDER BY created_at")
            return [dict(row) for row in cur.fetchall()]

    def delete_board(self, board_id: str) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM boards WHERE id = ?", (board_id,))
            self._conn.commit()

    def update_board_last_seen(self, board_id: str, timestamp: str | None = None) -> None:
        ts = timestamp or datetime.now().isoformat()
        with self._lock:
            self._conn.execute(
                "UPDATE boards SET last_seen = ? WHERE id = ?",
                (ts, board_id),
            )
            self._conn.commit()

    # --------------------------------------------------------------------------
    # BOARDS_SENSORS
    # --------------------------------------------------------------------------
    def save_board_sensor(self, board_id: str, sensor_type: str, pin: str,
                          enabled: int = 1, config_json: str | None = None) -> None:
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO boards_sensors (board_id, sensor_type, pin, enabled, config_json)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(board_id, sensor_type) DO UPDATE SET
                    pin = excluded.pin,
                    enabled = excluded.enabled,
                    config_json = excluded.config_json
                """,
                (board_id, sensor_type, pin, enabled, config_json),
            )
            self._conn.commit()

    def get_board_sensors(self, board_id: str) -> list[dict]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT * FROM boards_sensors WHERE board_id = ?", (board_id,)
            )
            return [dict(row) for row in cur.fetchall()]

    # --------------------------------------------------------------------------
    # LECTURAS
    # --------------------------------------------------------------------------
    def save_reading(self, board_id: str, sensor_type: str, valor: float,
                     unidad: str, raw_data: str | None = None,
                     ts_arduino: int | None = None) -> None:
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO lecturas (board_id, sensor_type, valor, unidad, raw_data, ts_arduino)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (board_id, sensor_type, valor, unidad, raw_data, ts_arduino),
            )
            self._conn.commit()

    def save_reading_batch(self, board_id: str, data: dict, ts_arduino: int | None = None) -> None:
        with self._lock:
            raw_json = json.dumps(data, ensure_ascii=False) if not isinstance(data, str) else data
            for sensor_name, sensor_data in data.items():
                if isinstance(sensor_data, dict) and "value" in sensor_data:
                    self._conn.execute(
                        """
                        INSERT INTO lecturas (board_id, sensor_type, valor, unidad, raw_data, ts_arduino)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            board_id,
                            sensor_name,
                            sensor_data["value"],
                            sensor_data.get("unit", ""),
                            raw_json,
                            ts_arduino,
                        ),
                    )
            self._conn.commit()

    def get_readings(self, board_id: str, sensor_type: str | None = None,
                     limit: int = 100,
                     start: datetime | None = None,
                     end: datetime | None = None) -> list[dict]:
        query = "SELECT * FROM lecturas WHERE board_id = ?"
        params: list = [board_id]

        if sensor_type:
            query += " AND sensor_type = ?"
            params.append(sensor_type)
        if start:
            query += " AND ts_base >= ?"
            params.append(start.strftime("%Y-%m-%d"))
        if end:
            query += " AND ts_base <= ?"
            params.append(end.strftime("%Y-%m-%d"))

        query += " ORDER BY ts_base DESC, id DESC LIMIT ?"
        params.append(limit)

        with self._lock:
            cur = self._conn.execute(query, params)
            return [dict(row) for row in cur.fetchall()]

    def get_latest_reading(self, board_id: str, sensor_type: str) -> dict | None:
        with self._lock:
            cur = self._conn.execute(
                """SELECT * FROM lecturas
                   WHERE board_id = ? AND sensor_type = ?
                   ORDER BY ts_base DESC, id DESC LIMIT 1""",
                (board_id, sensor_type),
            )
            row = cur.fetchone()
            return dict(row) if row else None

    def purge_old_readings(self, days: int = 30) -> int:
        """Retorna cantidad de filas eliminadas."""
        with self._lock:
            cur = self._conn.execute(
                "DELETE FROM lecturas WHERE ts_base < datetime('now', ?)",
                (f"-{days} days",),
            )
            self._conn.commit()
            return cur.rowcount

    # --------------------------------------------------------------------------
    # EVENTOS
    # --------------------------------------------------------------------------
    def save_event(self, board_id: str | None, tipo: str, descripcion: str = "") -> None:
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO eventos (board_id, tipo, descripcion)
                VALUES (?, ?, ?)
                """,
                (board_id, tipo, descripcion),
            )
            self._conn.commit()

    def get_events(self, board_id: str | None = None,
                   limit: int = 50,
                   start: datetime | None = None,
                   end: datetime | None = None) -> list[dict]:
        query = "SELECT * FROM eventos"
        params: list = []
        conditions = []

        if board_id:
            conditions.append("board_id = ?")
            params.append(board_id)
        if start:
            conditions.append("ts >= ?")
            params.append(start.strftime("%Y-%m-%d"))
        if end:
            conditions.append("ts <= ?")
            params.append(end.strftime("%Y-%m-%d"))

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY ts DESC, id DESC LIMIT ?"
        params.append(limit)

        with self._lock:
            cur = self._conn.execute(query, params)
            return [dict(row) for row in cur.fetchall()]

    # --------------------------------------------------------------------------
    # SNAPSHOTS
    # --------------------------------------------------------------------------
    def save_snapshot(self, usuario_id: int | None, descripcion: str, datos_json: str) -> None:
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO configuracion_snapshots (usuario_id, descripcion, datos_json)
                VALUES (?, ?, ?)
                """,
                (usuario_id, descripcion, datos_json),
            )
            self._conn.commit()

    def get_snapshots(self, usuario_id: int | None = None) -> list[dict]:
        with self._lock:
            if usuario_id is None:
                cur = self._conn.execute(
                    "SELECT * FROM configuracion_snapshots ORDER BY id DESC"
                )
            else:
                cur = self._conn.execute(
                    "SELECT * FROM configuracion_snapshots WHERE usuario_id = ? ORDER BY id DESC",
                    (usuario_id,),
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

    def update_user_last_login(self, user_id: int) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE usuarios SET last_login = datetime('now') WHERE id = ?",
                (user_id,),
            )
            self._conn.commit()

    def set_must_change_password(self, user_id: int, must_change: bool) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE usuarios SET must_change_password = ? WHERE id = ?",
                (1 if must_change else 0, user_id),
            )
            self._conn.commit()

    def set_user_active(self, user_id: int, active: bool) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE usuarios SET is_active = ? WHERE id = ?",
                (1 if active else 0, user_id),
            )
            self._conn.commit()

    # --------------------------------------------------------------------------
    # CIERRE
    # --------------------------------------------------------------------------
    def close(self) -> None:
        with self._lock:
            self._conn.close()