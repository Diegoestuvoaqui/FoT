from __future__ import annotations

import os
import sys
from pathlib import Path


def resource(rel: str) -> Path:
    """Ruta a un recurso, tanto en desarrollo como empaquetado (PyInstaller/AppImage)."""
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / rel
    # FoT/src/station/flasher/paths.py -> raíz del proyecto = parents[3]
    return Path(__file__).resolve().parents[3] / rel


TOOLS_DIR = resource("tools/linux-x86_64")
AVRDUDE = TOOLS_DIR / "avrdude"
AVRDUDE_CONF = TOOLS_DIR / "avrdude.conf"


def ensure_executable(path: Path) -> bool:
    """Garantiza el bit de ejecución. Devuelve False si no se pudo."""
    if os.access(path, os.X_OK):
        return True
    try:
        path.chmod(0o755)
    except OSError:
        return False
    return os.access(path, os.X_OK)
