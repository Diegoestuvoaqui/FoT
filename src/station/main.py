import logging
import signal
import sys
import tkinter as tk
from pathlib import Path

import customtkinter as ctk  # ← añadir

# --------------------------------------------------------------------------
# Bootstrap — primera ejecución o verificación de entorno
# --------------------------------------------------------------------------
from bootstrap import bootstrap
from connection.mqtt_client import MQTTEventBus  # ← connection, no mqtt
from data.database import Database
from domain.components import Finca, Parcela
from domain.memento import ConfigManager
from logic.data_receiver import DataReceiver
from ui.main_window import MainWindow

apply_theme()
root = ctk.CTk()

_ok, _msg = bootstrap()
if not _ok:
    # Mostrar error gráfico y salir — funciona incluso antes de crear root
    _root = tk.Tk()
    _root.withdraw()
    messagebox.showerror("FoT — Error de configuración", _msg)
    _root.destroy()
    sys.exit(1)

# --------------------------------------------------------------------------
# Logging
# --------------------------------------------------------------------------


_LOG_PATH = Path(__file__).parent / "fot.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(_LOG_PATH, encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------
# Configuración
# --------------------------------------------------------------------------
BROKER_IP = "localhost"
BROKER_PORT = 1883
DB_PATH = str(Path(__file__).parent / "data" / "fot.db")


def build_finca_from_db(db: Database) -> Finca:
    finca = Finca("finca-1", "Finca Principal")
    for row in db.get_parcelas():
        parcela = Parcela(
            id=row["id"],
            name=row["name"],
            umbral_min=row["umbral_min"],
            umbral_max=row["umbral_max"],
            modo=row["modo"],
        )
        finca.add_parcela(parcela)
    return finca


def main() -> None:
    logger.info("Arrancando FoT Estación Base")

    db = Database(DB_PATH)
    db.initialize()
    db.purge_old_readings(days=30)
    logger.info("Base de datos lista en %s", DB_PATH)

    finca = build_finca_from_db(db)
    logger.info("Finca cargada: %d parcelas", len(finca.get_children()))

    mqtt_bus = MQTTEventBus(BROKER_IP, BROKER_PORT)

    config_manager = ConfigManager()
    data_receiver = DataReceiver(db, finca)
    mqtt_bus.register(data_receiver)

    try:
        mqtt_bus.start()
        logger.info("MQTT conectado a %s:%s", BROKER_IP, BROKER_PORT)
    except Exception as e:
        logger.error("No se pudo conectar al broker MQTT: %s", e)

    root = tk.Tk()
    window = MainWindow(root, finca, mqtt_bus, db, config_manager)
    mqtt_bus.register(window)

    def on_close() -> None:
        logger.info("Cerrando FoT Estación Base")
        mqtt_bus.unregister(window)
        mqtt_bus.unregister(data_receiver)
        mqtt_bus.stop()
        db.close()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    signal.signal(signal.SIGTERM, lambda *_: root.after(0, on_close))

    logger.info("UI lista, entrando en mainloop")
    root.mainloop()
    logger.info("FoT Estación Base cerrada")


if __name__ == "__main__":
    main()
