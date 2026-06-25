import sqlite3
import threading
from datetime import datetime


class Database:

    def __init__(self, db_path: str = "data/fot.db"):
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        # Activar claves foráneas en cada conexión
        self._conn.execute("PRAGMA foreign_keys = ON")

    # --------------------------------------------------------------------------
    # Inicialización del esquema
    # --------------------------------------------------------------------------
    def initialize(self) -> None:
        with self._lock:
            cur = self._conn.cursor()
            cur.executescript("""
                PRAGMA foreign_keys = ON;

                -- ============================================================
                -- USUARIOS
                -- ============================================================
                CREATE TABLE IF NOT EXISTS usuarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'user',
                    created_at TEXT DEFAULT (datetime('now'))
                );

                -- ============================================================
                -- BOARDS (reemplaza dispositivos)
                -- ============================================================
                CREATE TABLE IF NOT EXISTS boards (
                    id TEXT PRIMARY KEY,
                    usuario_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
                    parcela_id TEXT REFERENCES parcelas(id) ON DELETE SET NULL,
                    conn TEXT DEFAULT 'usb',
                    port TEXT,
                    firmware_version TEXT,
                    status TEXT DEFAULT 'Sin asignar',
                    last_seen TEXT,
                    created_at TEXT DEFAULT (datetime('now'))
                );

                -- ============================================================
                -- SENSORES CONFIGURADOS POR BOARD (declarativo, no auto-detectado)
                -- ============================================================
                CREATE TABLE IF NOT EXISTS boards_sensors (
                    board_id TEXT REFERENCES boards(id) ON DELETE CASCADE,
                    sensor_type TEXT NOT NULL,
                    pin TEXT,
                    enabled INTEGER DEFAULT 1,
                    config_json TEXT,
                    PRIMARY KEY (board_id, sensor_type)
                );

                -- ============================================================
                -- PARCELAS
                -- ============================================================
                CREATE TABLE IF NOT EXISTS parcelas (
                    id TEXT PRIMARY KEY,
                    usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
                    name TEXT NOT NULL,
                    umbral_min REAL DEFAULT 30.0,
                    umbral_max REAL DEFAULT 70.0,
                    modo TEXT DEFAULT 'manual',
                    board_id TEXT REFERENCES boards(id) ON DELETE SET NULL,
                    created_at TEXT DEFAULT (datetime('now'))
                );

                -- ============================================================
                -- LECTURAS
                -- ============================================================
                CREATE TABLE IF NOT EXISTS lecturas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    parcela_id TEXT NOT NULL REFERENCES parcelas(id) ON DELETE CASCADE,
                    hum_suelo REAL,
                    hum_aire REAL,
                    temp REAL,
                    relay_state INTEGER,
                    ts_arduino INTEGER,
                    ts_base TEXT DEFAULT (datetime('now'))
                );

                -- ============================================================
                -- EVENTOS
                -- ============================================================
                CREATE TABLE IF NOT EXISTS eventos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    parcela_id TEXT NOT NULL REFERENCES parcelas(id) ON DELETE CASCADE,
                    tipo TEXT NOT NULL,
                    descripcion TEXT,
                    ts TEXT DEFAULT (datetime('now'))
                );

                -- ============================================================
                -- SNAPSHOTS
                -- ============================================================
                CREATE TABLE IF NOT EXISTS configuracion_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    usuario_id INTEGER REFERENCES usuarios(id) ON DELETE CASCADE,
                    descripcion TEXT,
                    datos_json TEXT NOT NULL,
                    ts TEXT DEFAULT (datetime('now'))
                );

                -- ============================================================
                -- ÍNDICES
                -- ============================================================
                CREATE INDEX IF NOT EXISTS idx_lecturas_parcela_ts 
                    ON lecturas(parcela_id, ts_base);
                CREATE INDEX IF NOT EXISTS idx_eventos_parcela_ts 
                    ON eventos(parcela_id, ts);
                CREATE INDEX IF NOT EXISTS idx_boards_usuario 
                    ON boards(usuario_id);
                CREATE INDEX IF NOT EXISTS idx_boards_parcela 
                    ON boards(parcela_id);
                CREATE INDEX IF NOT EXISTS idx_parcelas_usuario 
                    ON parcelas(usuario_id);
                CREATE INDEX IF NOT EXISTS idx_parcelas_board 
                    ON parcelas(board_id);
                CREATE INDEX IF NOT EXISTS idx_snapshots_usuario 
                    ON configuracion_snapshots(usuario_id);
            """)
            self._conn.commit()

    # --------------------------------------------------------------------------
    # USUARIOS
    # --------------------------------------------------------------------------
    def create_user(self, username: str, password_hash: str, role: str = "user") -> int:
        """Crea un usuario. Retorna el id generado."""
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
        """True si hay al menos un usuario en la BD."""
        with self._lock:
            cur = self._conn.execute("SELECT 1 FROM usuarios LIMIT 1")
            return cur.fetchone() is not None

    # --------------------------------------------------------------------------
    # BOARDS
    # --------------------------------------------------------------------------
    def save_board(self, board: dict) -> None:
        """UPSERT de board."""
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO boards (id, usuario_id, parcela_id, conn, port, 
                                    firmware_version, status, last_seen)
                VALUES (:id, :usuario_id, :parcela_id, :conn, :port,
                        :firmware_version, :status, :last_seen)
                ON CONFLICT(id) DO UPDATE SET
                    usuario_id = excluded.usuario_id,
                    parcela_id = excluded.parcela_id,
                    conn = excluded.conn,
                    port = excluded.port,
                    firmware_version = excluded.firmware_version,
                    status = excluded.status,
                    last_seen = excluded.last_seen
                """,
                board,
            )
            self._conn.commit()

    def get_board(self, board_id: str) -> dict | None:
        with self._lock:
            cur = self._conn.execute(
                "SELECT * FROM boards WHERE id = ?", (board_id,)
            )
            row = cur.fetchone()
            return dict(row) if row else None

    def get_boards_by_user(self, usuario_id: int | None) -> list[dict]:
        """Si usuario_id es None, retorna boards sin dueño."""
        with self._lock:
            if usuario_id is None:
                cur = self._conn.execute(
                    "SELECT * FROM boards WHERE usuario_id IS NULL ORDER BY created_at"
                )
            else:
                cur = self._conn.execute(
                    "SELECT * FROM boards WHERE usuario_id = ? ORDER BY created_at",
                    (usuario_id,),
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
    # BOARDS_SENSORS (configuración declarativa)
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
    def save_reading(self, parcela_id: str, data: dict) -> None:
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO lecturas (parcela_id, hum_suelo, hum_aire, temp, relay_state, ts_arduino)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    parcela_id,
                    data.get("hum_suelo"),
                    data.get("hum_aire"),
                    data.get("temp"),
                    data.get("relay_state"),
                    data.get("ts"),
                ),
            )
            self._conn.commit()

    def purge_old_readings(self, days: int = 30) -> None:
        with self._lock:
            self._conn.execute(
                "DELETE FROM lecturas WHERE ts_base < datetime('now', ?)",
                (f"-{days} days",),
            )
            self._conn.commit()

    # --------------------------------------------------------------------------
    # EVENTOS
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

    # --------------------------------------------------------------------------
    # PARCELAS
    # --------------------------------------------------------------------------
    def get_parcelas(self, usuario_id: int | None = None) -> list[dict]:
        """Si usuario_id es None, retorna todas (para admin)."""
        with self._lock:
            if usuario_id is None:
                cur = self._conn.execute(
                    "SELECT * FROM parcelas ORDER BY created_at"
                )
            else:
                cur = self._conn.execute(
                    "SELECT * FROM parcelas WHERE usuario_id = ? ORDER BY created_at",
                    (usuario_id,),
                )
            return [dict(row) for row in cur.fetchall()]

    def save_parcela(self, parcela: dict) -> None:
        """UPSERT completo con usuario_id y board_id."""
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO parcelas (id, usuario_id, name, umbral_min, umbral_max, modo, board_id)
                VALUES (:id, :usuario_id, :name, :umbral_min, :umbral_max, :modo, :board_id)
                ON CONFLICT(id) DO UPDATE SET
                    usuario_id = excluded.usuario_id,
                    name = excluded.name,
                    umbral_min = excluded.umbral_min,
                    umbral_max = excluded.umbral_max,
                    modo = excluded.modo,
                    board_id = excluded.board_id
                """,
                parcela,
            )
            self._conn.commit()

    def get_parcela(self, parcela_id: str) -> dict | None:
        with self._lock:
            cur = self._conn.execute(
                "SELECT * FROM parcelas WHERE id = ?", (parcela_id,)
            )
            row = cur.fetchone()
            return dict(row) if row else None

    def delete_parcela(self, parcela_id: str) -> None:
        with self._lock:
            self._conn.execute(
                "DELETE FROM parcelas WHERE id = ?",
                (parcela_id,)
            )
            self._conn.commit()

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

    # --------------------------------------------------------------------------
    # LECTURAS / EVENTOS (filtrados)
    # --------------------------------------------------------------------------
    def get_readings(self, parcela_id: str,
                     limit: int = 100,
                     start: datetime | None = None,
                     end: datetime | None = None) -> list[dict]:
        query = "SELECT * FROM lecturas WHERE parcela_id = ?"
        params: list = [parcela_id]
        if start:
            query += " AND ts_base >= ?"
            params.append(start.strftime("%Y-%m-%d"))
        if end:
            query += " AND ts_base <= ?"
            params.append(end.strftime("%Y-%m-%d"))
        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        with self._lock:
            cur = self._conn.execute(query, params)
            return [dict(row) for row in cur.fetchall()]

    def get_events(self, parcela_id: str,
                   limit: int = 50,
                   start: datetime | None = None,
                   end: datetime | None = None) -> list[dict]:
        query = "SELECT * FROM eventos WHERE parcela_id = ?"
        params: list = [parcela_id]
        if start:
            query += " AND ts >= ?"
            params.append(start.strftime("%Y-%m-%d"))
        if end:
            query += " AND ts <= ?"
            params.append(end.strftime("%Y-%m-%d"))
        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        with self._lock:
            cur = self._conn.execute(query, params)
            return [dict(row) for row in cur.fetchall()]

    # --------------------------------------------------------------------------
    # CIERRE
    # --------------------------------------------------------------------------
    def close(self) -> None:
        with self._lock:
            self._conn.close()
