# src/station/data/database.py
"""Acceso a datos SQLite para la estación FoT (esquema v2, Fase 3).

- Migraciones versionadas en data/migrations/ (PRAGMA user_version).
- WAL + busy_timeout + permisos 0600 sobre el fichero.
- lecturas en epoch UTC (ts_utc) + ts_device_ms.
- Tablas nuevas: board_actuators, relay_events, lecturas_hora, audit_log,
  device_credentials.
- Compatibilidad v1: se conservan save_board, get_boards_by_user_id,
  save_event, get_events, get_readings, save_board_sensor, etc.
"""
import csv
import logging
import math
import os
import shutil
import sqlite3
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

# Campos de boards que update_board_fields permite tocar (whitelist).
_BOARD_UPDATABLE = {
    "usuario_id", "conn", "port", "sketch_id", "sketch_name",
    "sketch_version", "status", "last_seen",
    "hwid", "vid", "pid", "serial_number", "manufacturer", "product",
    "location",
    "hw_model", "mac", "ip", "fw_version", "rssi", "uptime_s",
    "power_mode", "interval_ms", "approved",
}


def _to_epoch(value) -> int | None:
    """datetime | str | int | float -> epoch UTC segundos, o None."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).strip()
        if not text:
            return None
        try:
            dt = datetime.fromisoformat(text)
        except ValueError:
            dt = None
            for fmt in ("%Y-%m-%d %H:%M:%S",
                        "%Y-%m-%d %H:%M:%S.%f",
                        "%Y-%m-%dT%H:%M:%S",
                        "%Y-%m-%d"):
                try:
                    dt = datetime.strptime(text, fmt)
                    break
                except ValueError:
                    continue
            if dt is None:
                return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp())


class Database:

    def __init__(self, db_path: str = "data/iot.db"):
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path),
                                     check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.execute("PRAGMA journal_mode = WAL")
        self._conn.execute("PRAGMA busy_timeout = 5000")
        self._conn.execute("PRAGMA synchronous = NORMAL")
        try:
            os.chmod(self._db_path, 0o600)
        except OSError:
            pass

    # ==================================================================
    # MIGRACIONES
    # ==================================================================
    def _backup(self, version: int) -> Path | None:
        if not self._db_path.exists():
            return None
        try:
            self._conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        except sqlite3.DatabaseError:
            pass
        dst = self._db_path.with_name(
            f"{self._db_path.name}.bak-v{version}")
        shutil.copy2(self._db_path, dst)
        logger.info("Backup de BD creado en %s", dst)
        return dst

    def migrate(self) -> None:
        """Aplica las migraciones pendientes de data/migrations/."""
        from data.migrations import MIGRATIONS
        with self._lock:
            current = self._conn.execute(
                "PRAGMA user_version").fetchone()[0]
            if current > len(MIGRATIONS):
                raise RuntimeError(
                    f"BD con user_version={current} pero solo hay "
                    f"{len(MIGRATIONS)} migraciones conocidas.")
            if current == len(MIGRATIONS):
                return
            if current == 0:
                self._backup(current)
            for version in range(current, len(MIGRATIONS)):
                name, upgrade = MIGRATIONS[version]
                try:
                    self._conn.execute("BEGIN IMMEDIATE")
                    result = upgrade(self._conn)
                    self._conn.execute(f"PRAGMA user_version = {version + 1}")
                    self._conn.commit()
                    logger.info("Migración %s aplicada (v%d)%s",
                                name, version + 1,
                                f" -> {result}" if result else "")
                except Exception:
                    self._conn.rollback()
                    logger.exception(
                        "Migración %s falló; se revirtió", name)
                    raise

    def initialize(self) -> None:
        """Compatibilidad v1: ahora es alias de migrate()."""
        self.migrate()

    # ==================================================================
    # USUARIOS
    # ==================================================================
    def create_user(self, username: str, password_hash: str,
                    role: str = "user") -> int:
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO usuarios (username, password_hash, role)"
                " VALUES (?, ?, ?)",
                (username, password_hash, role),
            )
            self._conn.commit()
            return cur.lastrowid

    def get_user_by_username(self, username: str) -> dict | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM usuarios WHERE username = ?", (username,)
            ).fetchone()
            return dict(row) if row else None

    def get_user_by_id(self, user_id: int) -> dict | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM usuarios WHERE id = ?", (user_id,)
            ).fetchone()
            return dict(row) if row else None

    def list_users(self) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM usuarios ORDER BY created_at"
            ).fetchall()
            return [dict(r) for r in rows]

    def delete_user(self, user_id: int) -> None:
        with self._lock:
            self._conn.execute(
                "DELETE FROM usuarios WHERE id = ?", (user_id,))
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
            return self._conn.execute(
                "SELECT 1 FROM usuarios LIMIT 1").fetchone() is not None

    def update_user_last_login(self, user_id: int) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE usuarios SET last_login = datetime('now')"
                " WHERE id = ?", (user_id,),
            )
            self._conn.commit()

    def set_must_change_password(self, user_id: int,
                                 must_change: bool) -> None:
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

    # -------- Bloqueo de login (columnas v2) -------------------------
    def register_failed_login(self, user_id: int, max_attempts: int = 5,
                              lock_seconds: int = 900) -> int:
        """Incrementa failed_attempts; bloquea si alcanza max_attempts.
        Devuelve el número de intentos acumulados."""
        with self._lock:
            row = self._conn.execute(
                "SELECT failed_attempts FROM usuarios WHERE id = ?",
                (user_id,),
            ).fetchone()
            if not row:
                return 0
            attempts = (row["failed_attempts"] or 0) + 1
            locked_until = (int(time.time()) + lock_seconds
                            if attempts >= max_attempts else None)
            self._conn.execute(
                "UPDATE usuarios SET failed_attempts = ?, locked_until = ?"
                " WHERE id = ?",
                (attempts, locked_until, user_id),
            )
            self._conn.commit()
            return attempts

    def reset_failed_login(self, user_id: int) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE usuarios SET failed_attempts = 0, locked_until = NULL"
                " WHERE id = ?", (user_id,),
            )
            self._conn.commit()

    def is_user_locked(self, user_id: int) -> bool:
        with self._lock:
            row = self._conn.execute(
                "SELECT locked_until FROM usuarios WHERE id = ?",
                (user_id,),
            ).fetchone()
            if not row or not row["locked_until"]:
                return False
            return int(time.time()) < int(row["locked_until"])

    # ==================================================================
    # BOARDS
    # ==================================================================
    _BOARD_COLS = [
        "id", "usuario_id", "conn", "port", "sketch_id", "sketch_name",
        "sketch_version", "status", "last_seen",
        "hwid", "vid", "pid", "serial_number", "manufacturer", "product",
        "location",
        "hw_model", "mac", "ip", "fw_version", "rssi", "uptime_s",
        "power_mode", "interval_ms", "approved",
    ]

    def save_board(self, board: dict) -> None:
        if not board.get("id"):
            raise ValueError("board['id'] es obligatorio")
        defaults = {
            "usuario_id": None, "conn": "usb", "port": None,
            "sketch_id": None, "sketch_name": None,
            "sketch_version": "1.0", "status": "Sin asignar",
            "last_seen": None, "hwid": None, "vid": None, "pid": None,
            "serial_number": None, "manufacturer": None, "product": None,
            "location": None,
            "hw_model": None, "mac": None, "ip": None, "fw_version": None,
            "rssi": None, "uptime_s": None, "power_mode": "normal",
            "interval_ms": None, "approved": 0,
        }
        merged = {**defaults,
                  **{k: v for k, v in board.items()
                     if k in self._BOARD_COLS}}
        cols = ", ".join(self._BOARD_COLS)
        placeholders = ", ".join(f":{c}" for c in self._BOARD_COLS)
        updates = ", ".join(
            f"{c} = excluded.{c}"
            for c in self._BOARD_COLS if c != "id")
        with self._lock:
            self._conn.execute(
                f"INSERT INTO boards ({cols}) VALUES ({placeholders})"
                f" ON CONFLICT(id) DO UPDATE SET {updates}",
                merged,
            )
            self._conn.commit()

    def update_board_fields(self, board_id: str, fields: dict) -> None:
        if not fields:
            return
        invalid = set(fields) - _BOARD_UPDATABLE
        if invalid:
            raise ValueError(
                f"Campos no permitidos en update_board_fields: {invalid}")
        sets = ", ".join(f"{k} = ?" for k in fields)
        with self._lock:
            self._conn.execute(
                f"UPDATE boards SET {sets} WHERE id = ?",
                (*fields.values(), board_id),
            )
            self._conn.commit()

    def get_board_by_id(self, board_id: str) -> dict | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM boards WHERE id = ?", (board_id,)
            ).fetchone()
            return dict(row) if row else None

    def get_unclaimed_boards(self) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM boards WHERE usuario_id IS NULL"
                " ORDER BY created_at"
            ).fetchall()
            return [dict(r) for r in rows]

    def get_boards_by_user_id(self, usuario_id: int) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM boards WHERE usuario_id = ?"
                " ORDER BY created_at", (usuario_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_boards_by_sketch(self, sketch_id: str) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM boards WHERE sketch_id = ?"
                " ORDER BY created_at", (sketch_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_all_boards(self) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM boards ORDER BY created_at"
            ).fetchall()
            return [dict(r) for r in rows]

    def delete_board(self, board_id: str) -> None:
        with self._lock:
            self._conn.execute(
                "DELETE FROM boards WHERE id = ?", (board_id,))
            self._conn.commit()

    def update_board_last_seen(self, board_id: str,
                               timestamp: str | None = None) -> None:
        ts = timestamp or datetime.now().isoformat()
        with self._lock:
            self._conn.execute(
                "UPDATE boards SET last_seen = ? WHERE id = ?",
                (ts, board_id),
            )
            self._conn.commit()

    # ==================================================================
    # BOARDS_SENSORS
    # ==================================================================
    def save_board_sensor(self, board_id: str, sensor_type: str, pin: str,
                          enabled: int = 1,
                          config_json: str | None = None) -> None:
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO boards_sensors
                    (board_id, sensor_type, pin, enabled, config_json)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(board_id, sensor_type) DO UPDATE SET
                    pin = excluded.pin,
                    enabled = excluded.enabled,
                    config_json = excluded.config_json
                """,
                (board_id, sensor_type, pin, enabled, config_json),
            )
            self._conn.commit()

    def upsert_board_sensor(self, board_id: str, sensor_type: str,
                            pin: str | None = None,
                            enabled: int = 1,
                            config_json: str | None = None,
                            unit: str | None = None,
                            label: str | None = None,
                            min_valid: float | None = None,
                            max_valid: float | None = None) -> None:
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO boards_sensors
                    (board_id, sensor_type, pin, enabled, config_json,
                     unit, label, min_valid, max_valid)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(board_id, sensor_type) DO UPDATE SET
                    pin = COALESCE(excluded.pin, boards_sensors.pin),
                    enabled = excluded.enabled,
                    config_json = COALESCE(excluded.config_json,
                                           boards_sensors.config_json),
                    unit = COALESCE(excluded.unit, boards_sensors.unit),
                    label = COALESCE(excluded.label, boards_sensors.label),
                    min_valid = COALESCE(excluded.min_valid,
                                         boards_sensors.min_valid),
                    max_valid = COALESCE(excluded.max_valid,
                                         boards_sensors.max_valid)
                """,
                (board_id, sensor_type, pin, enabled, config_json,
                 unit, label, min_valid, max_valid),
            )
            self._conn.commit()

    def get_board_sensors(self, board_id: str) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM boards_sensors WHERE board_id = ?",
                (board_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    # ==================================================================
    # SKETCHES
    # ==================================================================
    def get_all_sketches(self) -> list[dict]:
        with self._lock:
            rows = self._conn.execute("SELECT * FROM sketches").fetchall()
            return [dict(r) for r in rows]

    def get_sketch(self, sketch_id: str) -> dict | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM sketches WHERE sketch_id = ?", (sketch_id,)
            ).fetchone()
            return dict(row) if row else None

    def upsert_sketch(self, sketch_id: str, sketch_name: str = "",
                      panel_key: str | None = None,
                      description: str = "") -> None:
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO sketches
                    (sketch_id, sketch_name, panel_key, description)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(sketch_id) DO UPDATE SET
                    sketch_name = excluded.sketch_name,
                    panel_key = COALESCE(excluded.panel_key,
                                         sketches.panel_key),
                    description = excluded.description
                """,
                (sketch_id, sketch_name, panel_key, description),
            )
            self._conn.commit()

    # ==================================================================
    # LECTURAS (v2: ts_utc epoch + ts_device_ms)
    # ==================================================================
    def save_reading_batch(self, board_id: str, data: dict, ts_utc: int,
                           ts_device_ms: int | None = None) -> int:
        """Inserta un lote de lecturas en una transacción.

        data: {sensor_type: valor_numérico}. Devuelve filas insertadas.
        """
        rows = []
        for sensor_type, valor in data.items():
            try:
                v = float(valor)
            except (TypeError, ValueError):
                continue
            if not math.isfinite(v):
                continue
            rows.append(
                (board_id, sensor_type, v, int(ts_utc), ts_device_ms))
        if not rows:
            return 0
        with self._lock:
            try:
                self._conn.execute("BEGIN IMMEDIATE")
                self._conn.executemany(
                    """
                    INSERT INTO lecturas
                        (board_id, sensor_type, valor, ts_utc, ts_device_ms)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    rows,
                )
                self._conn.commit()
                return len(rows)
            except Exception:
                self._conn.rollback()
                raise

    def get_latest(self, board_id: str,
                   sensor_type: str | None = None):
        """Última lectura. Si sensor_type es None devuelve
        {sensor_type: row} con la más reciente de cada sensor."""
        with self._lock:
            if sensor_type is not None:
                row = self._conn.execute(
                    """
                    SELECT * FROM lecturas
                    WHERE board_id = ? AND sensor_type = ?
                    ORDER BY ts_utc DESC, id DESC LIMIT 1
                    """,
                    (board_id, sensor_type),
                ).fetchone()
                return dict(row) if row else None
            rows = self._conn.execute(
                """
                SELECT l.* FROM lecturas l
                INNER JOIN (
                    SELECT sensor_type, MAX(ts_utc) AS mts
                    FROM lecturas WHERE board_id = ?
                    GROUP BY sensor_type
                ) m ON m.sensor_type = l.sensor_type AND m.mts = l.ts_utc
                WHERE l.board_id = ?
                """,
                (board_id, board_id),
            ).fetchall()
            return {r["sensor_type"]: dict(r) for r in rows}

    # Alias v1
    def get_latest_reading(self, board_id: str,
                           sensor_type: str) -> dict | None:
        return self.get_latest(board_id, sensor_type)

    def get_readings(self, board_id: str, sensor_type: str | None = None,
                     limit: int = 100,
                     start: datetime | None = None,
                     end: datetime | None = None) -> list[dict]:
        """Compatibilidad v1: filtra por ts_utc (epoch UTC)."""
        q = "SELECT * FROM lecturas WHERE board_id = ?"
        params: list = [board_id]
        if sensor_type:
            q += " AND sensor_type = ?"
            params.append(sensor_type)
        st = _to_epoch(start)
        if st is not None:
            q += " AND ts_utc >= ?"
            params.append(st)
        et = _to_epoch(end)
        if et is not None:
            q += " AND ts_utc <= ?"
            params.append(et)
        q += " ORDER BY ts_utc DESC, id DESC LIMIT ?"
        params.append(limit)
        with self._lock:
            return [dict(r) for r in self._conn.execute(q, params).fetchall()]

    def get_series(self, board_id: str,
                   sensor_types: list[str] | None = None,
                   start_ts: int | None = None,
                   end_ts: int | None = None,
                   max_points: int = 500) -> dict:
        """Serie temporal alineada.

        Devuelve {"ts": [...], "<sensor>": [...], ...} con listas de la
        misma longitud (None donde no hay dato). Elige la fuente según
        el rango: lecturas crudas / bucket de 5 min / horario.
        """
        now = int(time.time())
        if end_ts is None:
            end_ts = now
        if start_ts is None:
            start_ts = end_ts - 3600
        span = max(1, int(end_ts) - int(start_ts))
        with self._lock:
            if span <= 6 * 3600:
                rows = self._fetch_series_raw(
                    board_id, sensor_types, start_ts, end_ts)
            elif span <= 48 * 3600:
                rows = self._fetch_series_buckets(
                    board_id, sensor_types, start_ts, end_ts, 300)
            elif span <= 60 * 86400:
                rows = self._fetch_series_buckets(
                    board_id, sensor_types, start_ts, end_ts, 3600)
            else:
                rows = self._fetch_series_hourly(
                    board_id, sensor_types, start_ts, end_ts)
        return self._assemble_series(rows, max_points)

    def _fetch_series_raw(self, board_id, sensor_types, start_ts, end_ts):
        q = ("SELECT sensor_type, ts_utc AS ts, valor FROM lecturas "
             "WHERE board_id = ? AND ts_utc BETWEEN ? AND ?")
        params = [board_id, int(start_ts), int(end_ts)]
        if sensor_types:
            q += f" AND sensor_type IN ({','.join('?'*len(sensor_types))})"
            params.extend(sensor_types)
        q += " ORDER BY ts_utc, id"
        return self._conn.execute(q, params).fetchall()

    def _fetch_series_buckets(self, board_id, sensor_types,
                              start_ts, end_ts, bucket):
        q = ("SELECT sensor_type, (ts_utc / ?) * ? AS ts, AVG(valor) AS valor "
             "FROM lecturas WHERE board_id = ? AND ts_utc BETWEEN ? AND ?")
        params = [bucket, bucket, board_id, int(start_ts), int(end_ts)]
        if sensor_types:
            q += f" AND sensor_type IN ({','.join('?'*len(sensor_types))})"
            params.extend(sensor_types)
        q += " GROUP BY sensor_type, ts ORDER BY ts"
        return self._conn.execute(q, params).fetchall()

    def _fetch_series_hourly(self, board_id, sensor_types, start_ts, end_ts):
        q = ("SELECT sensor_type, hora_utc AS ts, vavg AS valor "
             "FROM lecturas_hora WHERE board_id = ? AND hora_utc BETWEEN ? AND ?")
        params = [board_id, int(start_ts), int(end_ts)]
        if sensor_types:
            q += f" AND sensor_type IN ({','.join('?'*len(sensor_types))})"
            params.extend(sensor_types)
        q += " ORDER BY hora_utc"
        return self._conn.execute(q, params).fetchall()

    @staticmethod
    def _assemble_series(rows, max_points: int) -> dict:
        if not rows:
            return {"ts": []}
        by_ts: dict[int, dict[str, float]] = {}
        for r in rows:
            by_ts.setdefault(int(r[1]), {})[r[0]] = float(r[2])
        all_ts = sorted(by_ts.keys())

        if len(all_ts) > max_points and max_points > 1:
            span = all_ts[-1] - all_ts[0]
            step = max(1, span // (max_points - 1))
            buckets: dict[int, list[int]] = {}
            for ts in all_ts:
                buckets.setdefault((ts - all_ts[0]) // step, []).append(ts)
            new_by_ts: dict[int, dict[str, list[float]]] = {}
            for b, ts_list in buckets.items():
                bts = all_ts[0] + b * step
                new_by_ts[bts] = {}
                for ts in ts_list:
                    for s, v in by_ts[ts].items():
                        new_by_ts[bts].setdefault(s, []).append(v)
            all_ts = sorted(new_by_ts.keys())
            by_ts = {ts: {s: sum(vs) / len(vs)
                          for s, vs in sensors.items()}
                     for ts, sensors in new_by_ts.items()}

        sensors = sorted({s for d in by_ts.values() for s in d})
        out: dict = {"ts": all_ts}
        for s in sensors:
            out[s] = [by_ts[ts].get(s) for ts in all_ts]
        return out

    # ==================================================================
    # ACTUADORES
    # ==================================================================
    def upsert_actuator(self, board_id: str, actuator_id: str,
                        kind: str = "relay", label: str | None = None,
                        pin: str | None = None, active_low: int = 0,
                        max_on_s: int | None = None) -> None:
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO board_actuators
                    (board_id, actuator_id, kind, label, pin,
                     active_low, max_on_s)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(board_id, actuator_id) DO UPDATE SET
                    kind = excluded.kind,
                    label = COALESCE(excluded.label,
                                     board_actuators.label),
                    pin = COALESCE(excluded.pin, board_actuators.pin),
                    active_low = excluded.active_low,
                    max_on_s = COALESCE(excluded.max_on_s,
                                        board_actuators.max_on_s)
                """,
                (board_id, actuator_id, kind, label, pin,
                 active_low, max_on_s),
            )
            self._conn.commit()

    def get_actuators(self, board_id: str) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM board_actuators WHERE board_id = ?"
                " ORDER BY actuator_id", (board_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def set_actuator_desired(self, board_id: str, actuator_id: str,
                             state: bool) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE board_actuators SET desired_state = ?"
                " WHERE board_id = ? AND actuator_id = ?",
                (int(bool(state)), board_id, actuator_id),
            )
            self._conn.commit()

    def set_actuator_reported(self, board_id: str, actuator_id: str,
                              state: bool, ts: int | None = None) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE board_actuators SET reported_state = ?,"
                " reported_ts = ? WHERE board_id = ? AND actuator_id = ?",
                (int(bool(state)), ts or int(time.time()),
                 board_id, actuator_id),
            )
            self._conn.commit()

    # ==================================================================
    # RELAY EVENTS
    # ==================================================================
    def save_relay_event(self, board_id: str, actuator_id: str, state: bool,
                         source: str = "ui", usuario_id: int | None = None,
                         seq: int | None = None) -> int:
        with self._lock:
            cur = self._conn.execute(
                """
                INSERT INTO relay_events
                    (board_id, actuator_id, state, source, usuario_id,
                     seq, ts_cmd)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (board_id, actuator_id, int(bool(state)), source,
                 usuario_id, seq, int(time.time())),
            )
            self._conn.commit()
            return cur.lastrowid

    def ack_relay_event(self, event_id: int) -> None:
        """Marca ts_ack; ignora si ya estaba ack (evita duplicados)."""
        with self._lock:
            self._conn.execute(
                "UPDATE relay_events SET ts_ack = ?"
                " WHERE id = ? AND ts_ack IS NULL",
                (int(time.time()), event_id),
            )
            self._conn.commit()

    def get_relay_events(self, board_id: str | None = None,
                         limit: int = 50) -> list[dict]:
        with self._lock:
            if board_id:
                rows = self._conn.execute(
                    "SELECT * FROM relay_events WHERE board_id = ?"
                    " ORDER BY ts_cmd DESC, id DESC LIMIT ?",
                    (board_id, limit),
                ).fetchall()
            else:
                rows = self._conn.execute(
                    "SELECT * FROM relay_events"
                    " ORDER BY ts_cmd DESC, id DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            return [dict(r) for r in rows]

    # ==================================================================
    # EVENTOS
    # ==================================================================
    def save_event(self, board_id: str | None, tipo: str,
                   descripcion: str = "",
                   usuario_id: int | None = None,
                   categoria: str | None = None) -> None:
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO eventos
                    (board_id, tipo, descripcion, usuario_id,
                     categoria, ts_utc)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (board_id, tipo, descripcion, usuario_id,
                 categoria, int(time.time())),
            )
            self._conn.commit()

    def get_events(self, board_id: str | None = None, limit: int = 50,
                   start: datetime | None = None,
                   end: datetime | None = None) -> list[dict]:
        q = "SELECT * FROM eventos"
        params: list = []
        conds = []
        if board_id:
            conds.append("board_id = ?")
            params.append(board_id)
        st = _to_epoch(start)
        if st is not None:
            conds.append("ts_utc >= ?")
            params.append(st)
        et = _to_epoch(end)
        if et is not None:
            conds.append("ts_utc <= ?")
            params.append(et)
        if conds:
            q += " WHERE " + " AND ".join(conds)
        q += " ORDER BY COALESCE(ts_utc, 0) DESC, ts DESC, id DESC LIMIT ?"
        params.append(limit)
        with self._lock:
            return [dict(r) for r in self._conn.execute(q, params).fetchall()]

    # ==================================================================
    # AUDIT LOG
    # ==================================================================
    def save_audit(self, accion: str, objetivo: str | None = None,
                   usuario_id: int | None = None,
                   username: str | None = None,
                   resultado: str = "ok",
                   detalle: str | None = None) -> None:
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO audit_log
                    (ts_utc, usuario_id, username, accion,
                     objetivo, resultado, detalle)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (int(time.time()), usuario_id, username, accion,
                 objetivo, resultado, detalle),
            )
            self._conn.commit()

    def get_audit(self, limit: int = 100,
                  usuario_id: int | None = None) -> list[dict]:
        with self._lock:
            if usuario_id is not None:
                rows = self._conn.execute(
                    "SELECT * FROM audit_log WHERE usuario_id = ?"
                    " ORDER BY ts_utc DESC, id DESC LIMIT ?",
                    (usuario_id, limit),
                ).fetchall()
            else:
                rows = self._conn.execute(
                    "SELECT * FROM audit_log"
                    " ORDER BY ts_utc DESC, id DESC LIMIT ?", (limit,),
                ).fetchall()
            return [dict(r) for r in rows]

    # ==================================================================
    # CREDENCIALES MQTT POR DISPOSITIVO
    # ==================================================================
    def save_device_credentials(self, board_id: str, mqtt_user: str,
                                secret_hash: str) -> None:
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO device_credentials
                    (board_id, mqtt_user, secret_hash, created_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(board_id) DO UPDATE SET
                    mqtt_user = excluded.mqtt_user,
                    secret_hash = excluded.secret_hash,
                    created_at = excluded.created_at,
                    revoked_at = NULL
                """,
                (board_id, mqtt_user, secret_hash, int(time.time())),
            )
            self._conn.commit()

    def get_device_credentials(self, board_id: str) -> dict | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM device_credentials WHERE board_id = ?",
                (board_id,),
            ).fetchone()
            return dict(row) if row else None

    def revoke_device_credentials(self, board_id: str) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE device_credentials SET revoked_at = ?"
                " WHERE board_id = ?", (int(time.time()), board_id),
            )
            self._conn.commit()

    # ==================================================================
    # MANTENIMIENTO: agrega a lecturas_hora y purga
    # ==================================================================
    def maintenance(self, raw_days: int = 30,
                    hourly_days: int = 180) -> dict:
        """Agrega lecturas crudas > raw_days a lecturas_hora y las purga.

        Devuelve {"purged_raw": N, "purged_hora": M}.
        """
        now = int(time.time())
        raw_cutoff = now - raw_days * 86400
        hourly_cutoff = now - hourly_days * 86400
        with self._lock:
            try:
                self._conn.execute("BEGIN IMMEDIATE")
                # 1) Agregar horas antiguas a lecturas_hora
                self._conn.execute(
                    """
                    INSERT INTO lecturas_hora
                        (board_id, sensor_type, hora_utc,
                         n, vmin, vmax, vavg)
                    SELECT board_id, sensor_type,
                           (ts_utc / 3600) * 3600 AS hora_utc,
                           COUNT(*), MIN(valor), MAX(valor), AVG(valor)
                    FROM lecturas
                    WHERE ts_utc < ?
                    GROUP BY board_id, sensor_type, hora_utc
                    ON CONFLICT(board_id, sensor_type, hora_utc) DO UPDATE SET
                        vavg = (lecturas_hora.vavg * lecturas_hora.n
                                + excluded.vavg * excluded.n)
                               / (lecturas_hora.n + excluded.n),
                        vmin = MIN(lecturas_hora.vmin, excluded.vmin),
                        vmax = MAX(lecturas_hora.vmax, excluded.vmax),
                        n = lecturas_hora.n + excluded.n
                    """,
                    (raw_cutoff,),
                )
                # 2) Purgar crudas ya agregadas
                cur = self._conn.execute(
                    "DELETE FROM lecturas WHERE ts_utc < ?", (raw_cutoff,))
                purged_raw = cur.rowcount
                # 3) Purgar histórico horario muy viejo
                cur2 = self._conn.execute(
                    "DELETE FROM lecturas_hora WHERE hora_utc < ?",
                    (hourly_cutoff,))
                purged_hora = cur2.rowcount
                self._conn.commit()
                return {"purged_raw": purged_raw,
                        "purged_hora": purged_hora}
            except Exception:
                self._conn.rollback()
                raise

    # Alias por compatibilidad con cualquier llamada v1 suelta
    def purge_old_readings(self, days: int = 30) -> int:
        return self.maintenance(raw_days=days).get("purged_raw", 0)

    # ==================================================================
    # EXPORT CSV
    # ==================================================================
    def export_readings_csv(self, path: str,
                            board_id: str | None = None,
                            start_ts: int | None = None,
                            end_ts: int | None = None) -> int:
        q = "SELECT * FROM lecturas"
        params: list = []
        conds = []
        if board_id:
            conds.append("board_id = ?")
            params.append(board_id)
        if start_ts is not None:
            conds.append("ts_utc >= ?")
            params.append(int(start_ts))
        if end_ts is not None:
            conds.append("ts_utc <= ?")
            params.append(int(end_ts))
        if conds:
            q += " WHERE " + " AND ".join(conds)
        q += " ORDER BY ts_utc, id"
        with self._lock:
            rows = self._conn.execute(q, params).fetchall()
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["id", "board_id", "sensor_type", "valor",
                        "ts_utc", "ts_utc_iso", "ts_device_ms"])
            for r in rows:
                w.writerow([
                    r["id"], r["board_id"], r["sensor_type"], r["valor"],
                    r["ts_utc"],
                    datetime.fromtimestamp(
                        r["ts_utc"], tz=timezone.utc).isoformat(),
                    r["ts_device_ms"],
                ])
        return len(rows)

    # ==================================================================
    # CIERRE
    # ==================================================================
    def close(self) -> None:
        with self._lock:
            try:
                self._conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            except sqlite3.DatabaseError:
                pass
            self._conn.close()