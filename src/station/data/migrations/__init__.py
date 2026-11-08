# src/station/data/migrations/__init__.py
"""Migraciones de esquema de la BD, en orden de aplicación.

Cada migración es un módulo con una función `upgrade(conn)` que recibe la
conexión sqlite3 ya dentro de una transacción (BEGIN IMMEDIATE). El runner
está en `Database.migrate()` y usa `PRAGMA user_version` para saber por
dónde va. Para añadir una migración: crear m000X_nombre.py y registrarla
abajo en MIGRATIONS.
"""
from data.migrations import m0001_initial, m0002_esp32

MIGRATIONS = [
    ("0001_initial", m0001_initial.upgrade),
    ("0002_esp32", m0002_esp32.upgrade),
]