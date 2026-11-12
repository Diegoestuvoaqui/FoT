"""Ajustes persistentes de la estación (~/.config/fot/settings.json).

Los valores por defecto sirven para desarrollo; las fases siguientes los
consumen (broker, retención de datos, seguridad, bloqueo por inactividad).
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass

from config.paths import config_dir

logger = logging.getLogger(__name__)


@dataclass
class Settings:
    broker_host: str = "0.0.0.0"          # bind del broker amqtt embebido
    broker_port: int = 1883
    mqtt_auth_mode: str = "open"          # "open" (dev) | "secure" (Fase 7)
    raw_retention_days: int = 30          # retención de lecturas crudas
    hourly_retention_days: int = 365      # retención de agregados por hora
    idle_lock_minutes: int = 0            # 0 = bloqueo por inactividad desactivado
    allow_self_register: bool = True      # alta de usuarios desde el login
    

    # --------------------------------------------------------------
    def save(self) -> None:
        path = config_dir() / "settings.json"
        try:
            path.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")
            path.chmod(0o600)
        except OSError as e:
            logger.error("No se pudo guardar settings.json: %s", e)

    @classmethod
    def load(cls) -> "Settings":
        path = config_dir() / "settings.json"
        if not path.exists():
            return cls()
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            known = set(cls.__dataclass_fields__)
            return cls(**{k: v for k, v in raw.items() if k in known})
        except (OSError, json.JSONDecodeError, TypeError) as e:
            logger.error("settings.json invalido (%s), usando valores por defecto", e)
            return cls()
