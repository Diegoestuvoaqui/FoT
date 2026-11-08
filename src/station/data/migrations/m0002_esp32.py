# data/migrations/m0002_esp32.py
"""Esquema v2 (Fase 3): pensado para nodos WiFi, actuadores, series largas
y auditoría.

- boards: hw_model, mac, ip, fw_version, rssi, uptime_s, power_mode,
  interval_ms, approved.
- boards_sensors: unit, label, min_valid, max_valid.
- Nuevas: board_actuators, relay_events, lecturas_hora, audit_log,
  device_credentials.
- usuarios: failed_attempts, locked_until.
- eventos: usuario_id, categoria, ts_utc.
- lecturas: se recrea sin unidad/raw_data, con ts_utc (epoch) y
  ts_device_ms. Datos migrados de ts_base (texto UTC) a epoch en Python,
  validando fila a fila; las no convertibles se descartan y se cuentan.
- sketches: alta del ESP32 (panel_key 'dht11'; la Fase 8 lo renombra).

Los ALTER TABLE van protegidos con PRAGMA table_info por si alguna columna
ya existiera.
"""
from datetime import datetime, timezone

SKETCH_ESP32 = (
    "esp32_wifi_dht22", "ESP32 + DHT22", "dht11", "ESP32 WiFi + DHT22 + relé"
)


def _to_epoch(ts_base) -> int | None:
    """Convierte ts_base (texto UTC de datetime('now')) a epoch segundos."""
    if ts_base is None:
        return None
    if isinstance(ts_base, (int, float)):
        return int(ts_base)
    text = str(ts_base).strip()
    dt = None
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(text, fmt)
                break
            except ValueError:
                continue
    if dt is None:
        return None
    if dt.tzinfo is None:
        # datetime('now') guarda UTC sin indicarlo
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp())


def _add_columns(conn, table: str, cols: list[tuple[str, str]]) -> None:
    existing = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
    for name, ddl in cols:
        if name not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")


def upgrade(conn) -> dict:
    _add_columns(conn, "boards", [
        ("hw_model", "TEXT"),
        ("mac", "TEXT"),
        ("ip", "TEXT"),
        ("fw_version", "TEXT"),
        ("rssi", "INTEGER"),
        ("uptime_s", "INTEGER"),
        ("power_mode", "TEXT DEFAULT 'normal'"),
        ("interval_ms", "INTEGER"),
        ("approved", "INTEGER DEFAULT 0"),
    ])
    _add_columns(conn, "boards_sensors", [
        ("unit", "TEXT"),
        ("label", "TEXT"),
        ("min_valid", "REAL"),
        ("max_valid", "REAL"),
    ])
    _add_columns(conn, "usuarios", [
        ("failed_attempts", "INTEGER DEFAULT 0"),
        ("locked_until", "INTEGER"),
    ])
    _add_columns(conn, "eventos", [
        ("usuario_id", "INTEGER REFERENCES usuarios(id) ON DELETE SET NULL"),
        ("categoria", "TEXT"),
        ("ts_utc", "INTEGER"),
    ])

    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS board_actuators (
            board_id TEXT NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
            actuator_id TEXT NOT NULL,
            kind TEXT NOT NULL DEFAULT 'relay',
            label TEXT,
            pin TEXT,
            active_low INTEGER DEFAULT 0,
            max_on_s INTEGER,
            desired_state INTEGER DEFAULT 0,
            reported_state INTEGER DEFAULT 0,
            reported_ts INTEGER,
            PRIMARY KEY (board_id, actuator_id)
        );

        CREATE TABLE IF NOT EXISTS relay_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            board_id TEXT NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
            actuator_id TEXT NOT NULL,
            state INTEGER NOT NULL,
            source TEXT NOT NULL DEFAULT 'ui',
            usuario_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
            seq INTEGER,
            ts_cmd INTEGER NOT NULL,
            ts_ack INTEGER
        );
        CREATE INDEX IF NOT EXISTS idx_relay_events_board_ts
            ON relay_events(board_id, ts_cmd);

        CREATE TABLE IF NOT EXISTS lecturas_hora (
            board_id TEXT NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
            sensor_type TEXT NOT NULL,
            hora_utc INTEGER NOT NULL,
            n INTEGER NOT NULL,
            vmin REAL, vmax REAL, vavg REAL,
            PRIMARY KEY (board_id, sensor_type, hora_utc)
        );

        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts_utc INTEGER NOT NULL,
            usuario_id INTEGER,
            username TEXT,
            accion TEXT NOT NULL,
            objetivo TEXT,
            resultado TEXT DEFAULT 'ok',
            detalle TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_audit_ts ON audit_log(ts_utc);

        CREATE TABLE IF NOT EXISTS device_credentials (
            board_id TEXT PRIMARY KEY REFERENCES boards(id) ON DELETE CASCADE,
            mqtt_user TEXT UNIQUE NOT NULL,
            secret_hash TEXT NOT NULL,
            created_at INTEGER,
            revoked_at INTEGER
        );
        """
    )

    # lecturas: recreación con ts_utc (epoch)
    conn.execute(
        """
        CREATE TABLE lecturas_v2 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            board_id TEXT NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
            sensor_type TEXT NOT NULL,
            valor REAL NOT NULL,
            ts_utc INTEGER NOT NULL,
            ts_device_ms INTEGER
        )
        """
    )
    rows = conn.execute(
        """
        SELECT id, board_id, sensor_type, valor, ts_arduino, ts_base
        FROM lecturas WHERE valor IS NOT NULL
        """
    ).fetchall()
    converted, skipped = [], 0
    for rid, board_id, sensor_type, valor, ts_dev, ts_base in rows:
        ts_utc = _to_epoch(ts_base)
        if ts_utc is None:
            skipped += 1
            continue
        converted.append((rid, board_id, sensor_type, valor, ts_utc, ts_dev))
    conn.executemany(
        """
        INSERT INTO lecturas_v2 (id, board_id, sensor_type, valor, ts_utc, ts_device_ms)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        converted,
    )
    conn.execute("DROP TABLE lecturas")
    conn.execute("ALTER TABLE lecturas_v2 RENAME TO lecturas")
    conn.executescript(
        """
        CREATE INDEX IF NOT EXISTS idx_lecturas_board_ts
            ON lecturas(board_id, sensor_type, ts_utc);
        CREATE INDEX IF NOT EXISTS idx_lecturas_sensor
            ON lecturas(board_id, sensor_type);
        """
    )

    conn.execute(
        "INSERT OR IGNORE INTO sketches (sketch_id, sketch_name, panel_key, description)"
        " VALUES (?, ?, ?, ?)",
        SKETCH_ESP32,
    )
    return {"lecturas_migradas": len(converted), "lecturas_descartadas": skipped}