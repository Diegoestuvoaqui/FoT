"""Rutas estándar de datos y configuración de la estación FoT (XDG Base Directory).

- Datos (BD, log):   ~/.local/share/fot/
- Configuración:     ~/.config/fot/  (respeta XDG_CONFIG_HOME)

Ambos se crean con permisos 0700. Nada vive ya dentro del árbol del código.
"""

from __future__ import annotations

import os
from pathlib import Path

APP_NAME = "fot"


def data_dir() -> Path:
    """Directorio de datos de la aplicación (BD, log)."""
    xdg = os.environ.get("XDG_DATA_HOME")
    p = (Path(xdg) if xdg else Path.home() / ".local" / "share") / APP_NAME
    p.mkdir(parents=True, exist_ok=True, mode=0o700)
    return p


def config_dir() -> Path:
    """Directorio de configuración (settings.json, secretos, notificaciones)."""
    xdg = os.environ.get("XDG_CONFIG_HOME")
    p = (Path(xdg) if xdg else Path.home() / ".config") / APP_NAME
    p.mkdir(parents=True, exist_ok=True, mode=0o700)
    return p


def db_path() -> Path:
    return data_dir() / "iot.db"


def log_path() -> Path:
    return data_dir() / "iot.log"


def legacy_db_path() -> Path | None:
    """Ubicación antigua de la BD dentro del árbol del código (para migración única)."""
    p = Path(__file__).resolve().parents[1] / "data" / "iot.db"
    return p if p.exists() else None


def migrate_legacy_db_once() -> bool:
    """
    Si existe una BD antigua dentro del árbol del código y aún no hay una en
    la nueva ubicación, la copia una sola vez. Devuelve True si migró.
    """
    target = db_path()
    if target.exists():
        return False
    legacy = legacy_db_path()
    if legacy is None:
        return False
    import shutil

    shutil.copy2(legacy, target)
    target.chmod(0o600)
    return True
