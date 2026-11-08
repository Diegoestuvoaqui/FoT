# src/station/data/migrations/m0001_initial.py
"""Baseline: esquema v1 tal cual existía antes de la Fase 3.

Usa CREATE TABLE IF NOT EXISTS a propósito: una BD vieja ya tiene estas
tablas y la migración debe ser un no-op; una BD nueva las crea desde cero.
"""


def upgrade(conn) -> None:
    conn.executescript(
        """
        PRAGMA foreign_keys = ON;

        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            is_active INTEGER DEFAULT 1,
            must_change_password INTEGER DEFAULT 0,
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

        CREATE TABLE IF NOT EXISTS sketches (
            sketch_id TEXT PRIMARY KEY,
            sketch_name TEXT,
            panel_key TEXT,
            description TEXT
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
        """
    )
    conn.executemany(
        """
        INSERT OR IGNORE INTO sketches (sketch_id, sketch_name, panel_key, description)
        VALUES (?, ?, ?, ?)
        """,
        [
            ("dht11", "DHT11 Sensor", "dht11", "UNO R4 WiFi + DHT11"),
            ("uno_r3_dht11", "UNO R3 + DHT11", "dht11", "UNO R3 clásico + DHT11"),
            ("uno_r4_wifi_dht11", "UNO R4 + DHT11", "dht11", "UNO R4 para DHT11"),
            ("lafvin_r3_ch340_dht11", "LAFVIN R3 CH340 + DHT11", "dht11",
             "Clon CH340 + DHT11 via SERIAL"),
        ],
    )