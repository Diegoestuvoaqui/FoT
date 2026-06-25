import os
import shutil
import subprocess
import time
from pathlib import Path

# --------------------------------------------------------------------------
# Rutas
# --------------------------------------------------------------------------
STATION_DIR = Path(__file__).parent
CONFIG_DIR = Path.home() / ".config" / "fot"
SENTINEL = CONFIG_DIR / ".configured"
MOSQ_CONF = CONFIG_DIR / "mosquitto.conf"
MOSQ_LOG = CONFIG_DIR / "mosquitto.log"
SERVICE_DIR = Path.home() / ".config" / "systemd" / "user"
SERVICE_FILE = SERVICE_DIR / "estacion_base.service"

# --------------------------------------------------------------------------
# Contenido de la config de Mosquitto (sin sudo — config local de usuario)
# --------------------------------------------------------------------------
_MOSQ_CONF = f"""\
listener 1883
allow_anonymous true
log_dest file {MOSQ_LOG}
log_type error
log_type warning
"""

# --------------------------------------------------------------------------
# Contenido del servicio systemd de usuario
# --------------------------------------------------------------------------
_SERVICE = f"""\
[Unit]
Description=FoT Estacion Base
After=graphical-session.target

[Service]
ExecStart=/usr/bin/python3 {STATION_DIR}/main.py
WorkingDirectory={STATION_DIR}
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
"""


# --------------------------------------------------------------------------
# Checks
# --------------------------------------------------------------------------
def _mosquitto_installed() -> bool:
    return shutil.which("mosquitto") is not None


def _avrdude_installed() -> bool:
    return shutil.which("avrdude") is not None


def _mosquitto_running() -> bool:
    try:
        r = subprocess.run(["pgrep", "-x", "mosquitto"], capture_output=True)
        return r.returncode == 0
    except OSError:
        return False


def _is_configured() -> bool:
    return SENTINEL.exists()


# --------------------------------------------------------------------------
# Acciones de setup
# --------------------------------------------------------------------------
def _configure_mosquitto() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    MOSQ_CONF.write_text(_MOSQ_CONF)


def _start_mosquitto() -> None:
    if _mosquitto_running():
        return
    subprocess.Popen(
        ["mosquitto", "-c", str(MOSQ_CONF), "-d"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(1)  # dar tiempo al broker para que abra el puerto


def _create_systemd_service() -> None:
    SERVICE_DIR.mkdir(parents=True, exist_ok=True)
    SERVICE_FILE.write_text(_SERVICE)
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=False)
    subprocess.run(["systemctl", "--user", "enable", "estacion_base"], check=False)
    # loginctl enable-linger para que arranque sin sesión abierta
    subprocess.run(["loginctl", "enable-linger", os.getenv("USER", "")], check=False)


def _write_sentinel() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    SENTINEL.touch()


# --------------------------------------------------------------------------
# Punto de entrada público
# --------------------------------------------------------------------------
def bootstrap() -> tuple[bool, str]:
    """
    Verifica y configura el entorno en la primera ejecución.
    Retorna (ok: bool, mensaje: str).
    ok=False significa que falta un requisito que el usuario debe instalar.
    """
    if not _mosquitto_installed():
        return False, (
            "Mosquitto no está instalado.\n"
            "Instálalo con:\n\n"
            "  sudo pacman -S mosquitto      # Arch\n"
            "  sudo apt install mosquitto    # Debian/Ubuntu"
        )

    if not _avrdude_installed():
        return False, (
            "avrdude no está instalado.\n"
            "Instálalo con:\n\n"
            "  sudo pacman -S avrdude        # Arch\n"
            "  sudo apt install avrdude      # Debian/Ubuntu"
        )
    
    if not _is_configured():
        _configure_mosquitto()
        _create_systemd_service()
        _write_sentinel()

    # En cada arranque — asegurar que mosquitto esté corriendo
    # (puede haberse detenido tras un reinicio del sistema)
    if not _mosquitto_running():
        _start_mosquitto()

    if not _mosquitto_running():
        return False, (
            "No se pudo arrancar Mosquitto.\n"
            f"Revisa el log en:\n  {MOSQ_LOG}"
        )

    return True, "OK"
