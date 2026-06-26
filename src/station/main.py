# src/station/main.py
import logging
import signal
import sys
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk

# --------------------------------------------------------------------------
# Bootstrap
# --------------------------------------------------------------------------
from bootstrap import bootstrap
from connection.mqtt_client import MQTTEventBus
from controller.auth_controller import AuthController
from controller.board_controller import BoardController
from controller.event_controller import EventController
from controller.export_controller import ExportController
from controller.parcela_controller import ParcelaController
from controller.snapshot_controller import SnapshotController
from data.database import Database
from domain.components import Finca, Parcela
from domain.memento import ConfigManager
from domain.user import User
from logic.data_receiver import DataReceiver
from logic.sensor_manager import SensorManager
from service.auth_service import AuthService
from service.board_service import BoardService
from service.event_service import EventService
from service.export_service import ExportService
from service.parcela_service import ParcelaService
from service.snapshot_service import SnapshotService
from ui.dialogs.login_dialog import LoginDialog
from ui.main_window import MainWindow
from ui.theme import apply_theme

# --------------------------------------------------------------------------
# Bootstrap check
# --------------------------------------------------------------------------
_ok, _msg = bootstrap()
if not _ok:
    import tkinter as tk

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


def build_finca_from_db(db: Database, usuario_id: int | None = None) -> Finca:
    finca = Finca("finca-1", "Finca Principal")
    rows = db.get_parcelas(usuario_id)
    for row in rows:
        parcela = Parcela(
            id=row["id"],
            name=row["name"],
            usuario_id=row["usuario_id"],
            umbral_min=row["umbral_min"],
            umbral_max=row["umbral_max"],
            modo=row["modo"],
            board_id=row.get("board_id"),
        )
        finca.add_parcela(parcela)
    return finca


def show_login(root: ctk.CTk, auth_ctrl: AuthController) -> User | None:
    """
    Muestra el diálogo de login.
    Retorna User autenticado o None si cancela.
    """
    user = [None]

    def on_login(u: User):
        user[0] = u

    LoginDialog(
        root,
        auth_ctrl._service,
        on_login=on_login,
        on_register=None,
    )

    return user[0]


def main() -> None:
    logger.info("Arrancando FoT Estación Base")

    # ------------------------------------------------------------------
    # Infraestructura
    # ------------------------------------------------------------------
    db = Database(DB_PATH)
    db.initialize()
    db.purge_old_readings(days=30)
    logger.info("Base de datos lista en %s", DB_PATH)

    # Crear admin si no hay usuarios
    auth_service = AuthService(db)
    auth_service.ensure_admin_exists()

    # MQTT para la estación (broker local)
    mqtt_bus = MQTTEventBus(BROKER_IP, BROKER_PORT)

    try:
        mqtt_bus.start()
        logger.info("MQTT broker local en %s:%s", BROKER_IP, BROKER_PORT)
    except Exception as e:
        logger.error("No se pudo iniciar broker MQTT: %s", e)

    # ------------------------------------------------------------------
    # SensorManager: gestiona conexiones USB/Bluetooth a placas
    # ------------------------------------------------------------------
    sensor_manager = SensorManager()

    # DataReceiver: recibe lecturas y las persiste
    data_receiver = DataReceiver(db)

    # ------------------------------------------------------------------
    # UI — Login primero
    # ------------------------------------------------------------------
    apply_theme()
    root = ctk.CTk()

    auth_ctrl = AuthController(auth_service)

    current_user = show_login(root, auth_ctrl)
    if current_user is None:
        logger.info("Login cancelado, saliendo")
        root.destroy()
        sys.exit(0)

    logger.info("Usuario autenticado: %s (role=%s)", current_user.username, current_user.role)

    # ------------------------------------------------------------------
    # Cargar datos del usuario
    # ------------------------------------------------------------------
    finca = build_finca_from_db(db, current_user.id)
    data_receiver.set_finca(finca)
    logger.info("Finca cargada: %d parcelas para usuario %s",
                len(finca.get_children()), current_user.username)

    # ------------------------------------------------------------------
    # Conectar callbacks del SensorManager al DataReceiver
    # ------------------------------------------------------------------
    def on_sensor_reading(parcela_id: str, data: dict):
        """Callback cuando llega lectura de sensor."""
        data_receiver.on_reading(parcela_id, data)

    def on_sensor_identify(parcela_id: str, data: dict):
        """Callback cuando placa se identifica."""
        data_receiver.on_identify(parcela_id, data)
        # Notificar al BoardService para actualizar UI
        board_service.on_sensor_identify(parcela_id, data)

    sensor_manager._on_reading = on_sensor_reading
    sensor_manager._on_identify = on_sensor_identify

    # ------------------------------------------------------------------
    # Capa de Servicios
    # ------------------------------------------------------------------
    config_manager = ConfigManager()
    event_service = EventService(db)

    # BoardService integrado con SensorManager
    board_service = BoardService(
        db=db,
        sensor_manager=sensor_manager,
    )
    board_service.load_from_db()

    parcela_service = ParcelaService(
        finca, db, config_manager, None, current_user.id  # irrigation_service=None
    )
    snapshot_service = SnapshotService(
        finca, db, config_manager, event_service, current_user.id
    )
    export_service = ExportService(db)

    # ------------------------------------------------------------------
    # Capa de Controladores
    # ------------------------------------------------------------------
    event_controller = EventController(event_service)
    board_controller = BoardController(board_service)
    parcela_controller = ParcelaController(parcela_service)
    snapshot_controller = SnapshotController(snapshot_service)
    export_controller = ExportController(export_service)

    # ------------------------------------------------------------------
    # Vista principal
    # ------------------------------------------------------------------
    window = MainWindow(
        root=root,
        finca=finca,
        mqtt_bus=mqtt_bus,
        parcela_ctrl=parcela_controller,
        board_ctrl=board_controller,
        snap_ctrl=snapshot_controller,
        export_ctrl=export_controller,
        event_ctrl=event_controller,
        user=current_user,
        auth_ctrl=auth_ctrl,
        sensor_manager=sensor_manager,  # NUEVO
    )

    # ------------------------------------------------------------------
    # Registro de observadores MQTT (para placas WiFi que publican por MQTT)
    # ------------------------------------------------------------------
    mqtt_bus.register(data_receiver)

    # ------------------------------------------------------------------
    # Cierre limpio
    # ------------------------------------------------------------------
    def on_close() -> None:
        logger.info("Cerrando FoT Estación Base")
        sensor_manager.disconnect_all()
        mqtt_bus.unregister(data_receiver)
        mqtt_bus.stop()
        event_controller.cleanup()
        board_controller.cleanup()
        db.close()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)

    def _handle_sigterm(_signum: int, _frame: object) -> None:
        root.after(0, on_close)

    signal.signal(signal.SIGTERM, _handle_sigterm)

    logger.info("UI lista, entrando en mainloop")
    root.mainloop()
    logger.info("FoT Estación Base cerrada")


if __name__ == "__main__":
    main()
