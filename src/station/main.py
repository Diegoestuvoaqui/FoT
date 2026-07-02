# src/station/main.py
import logging
import signal
import sys
import tkinter as tk
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
from controller.snapshot_controller import SnapshotController
from data.database import Database
from domain.memento import ConfigManager
from domain.user import User
from logic.data_receiver import DataReceiver
from logic.sensor_manager import SensorManager
from service.auth_service import AuthService
from service.board_service import BoardService
from service.event_service import EventService
from service.export_service import ExportService
from service.snapshot_service import SnapshotService
from ui.main_window import MainWindow
from ui.panels.login_panel import LoginPanel
from ui.theme import apply_theme

# --------------------------------------------------------------------------
# Bootstrap check
# --------------------------------------------------------------------------
_ok, _msg = bootstrap()
if not _ok:
    _root = tk.Tk()
    _root.withdraw()
    messagebox.showerror("IoT — Error de configuración", _msg)
    _root.destroy()
    sys.exit(1)

# --------------------------------------------------------------------------
# Logging
# --------------------------------------------------------------------------
_LOG_PATH = Path(__file__).parent / "iot.log"

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
DB_PATH = str(Path(__file__).parent / "data" / "iot.db")


def _build_main(root: ctk.CTk,
                current_user: User,
                db: Database,
                mqtt_bus: MQTTEventBus,
                sensor_manager: SensorManager,
                data_receiver: DataReceiver,
                auth_ctrl: AuthController) -> None:
    """
    Construye la interfaz principal una vez que el login fue exitoso.
    Se ejecuta dentro del callback de login (todavía dentro de mainloop).
    """
    logger.info("Usuario autenticado: %s (role=%s)", current_user.username, current_user.role)
    logger.info("Cargando boards para usuario %s", current_user.username)

    # ------------------------------------------------------------------
    # Conectar callbacks del SensorManager al DataReceiver
    # ------------------------------------------------------------------
    def on_sensor_reading(board_id: str, data: dict):
        data_receiver.on_reading(board_id, data)

    def on_sensor_identify(board_id: str, data: dict):
        data_receiver.on_identify(board_id, data)
        board_service.on_sensor_identify(board_id, data)

    sensor_manager.set_callbacks(on_reading=on_sensor_reading, on_identify=on_sensor_identify)

    # ------------------------------------------------------------------
    # Capa de Servicios
    # ------------------------------------------------------------------
    config_manager = ConfigManager()
    event_service = EventService(db)

    board_service = BoardService(
        db=db,
        sensor_manager=sensor_manager,
    )
    board_service.load_from_db()

    snapshot_service = SnapshotService(
        db=db, config_manager=config_manager,
        event_service=event_service, usuario_id=current_user.id
    )
    export_service = ExportService(db)

    # ------------------------------------------------------------------
    # Capa de Controladores
    # ------------------------------------------------------------------
    event_controller = EventController(event_service)
    board_controller = BoardController(board_service)
    snapshot_controller = SnapshotController(snapshot_service)
    export_controller = ExportController(export_service)

    # ------------------------------------------------------------------
    # Vista principal
    # ------------------------------------------------------------------
    window = MainWindow(
        root=root,
        mqtt_bus=mqtt_bus,
        board_ctrl=board_controller,
        snap_ctrl=snapshot_controller,
        export_ctrl=export_controller,
        event_ctrl=event_controller,
        user=current_user,
        auth_ctrl=auth_ctrl,
        sensor_manager=sensor_manager,
    )

    # ------------------------------------------------------------------
    # Registro de observadores MQTT (para placas WiFi)
    # ------------------------------------------------------------------
    #mqtt_bus.register(data_receiver)

    # ------------------------------------------------------------------
    # Cierre limpio
    # ------------------------------------------------------------------
    def on_close() -> None:
        logger.info("Cerrando IoT Estación Base")
        sensor_manager.disconnect_all()
        #mqtt_bus.unregister(data_receiver)
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


def main() -> None:
    logger.info("Arrancando IoT Estación Base")

    # ------------------------------------------------------------------
    # Infraestructura
    # ------------------------------------------------------------------
    db = Database(DB_PATH)
    db.initialize()
    db.purge_old_readings(days=30)
    logger.info("Base de datos lista en %s", DB_PATH)

    auth_service = AuthService(db)
    auth_service.ensure_admin_exists()


    #el SUBJECT de los WiFiBridge
    mqtt_bus = MQTTEventBus("localhost", 1883)
    try:
        mqtt_bus.start()
        logger.info("MQTT broker local en %s:%s", "localhost", 1883)
    except Exception as e:
        logger.error("No se pudo iniciar broker MQTT: %s", e)

    sensor_manager = SensorManager(mqtt_bus=mqtt_bus)
    data_receiver = DataReceiver(db)

    # ------------------------------------------------------------------
    # UI — Login embebido en la única ventana CTk
    # ------------------------------------------------------------------
    apply_theme()

    root = ctk.CTk()
    root.title("IoT — Iniciar sesión")
    root.geometry("600x800")
    root.resizable(False, False)
    root.grid_columnconfigure(0, weight=1)
    root.grid_rowconfigure(0, weight=1)

    auth_ctrl = AuthController(auth_service)

    current_user: User | None = None
    login_panel_ref: list[LoginPanel | None] = [None]

    def _on_login_success(user: User) -> None:
        nonlocal current_user
        current_user = user

        # Destruir panel de login y limpiar la ventana
        if login_panel_ref[0]:
            login_panel_ref[0].destroy()

        # Reconfigurar la misma ventana para la app principal
        root.title("IoT — Estación Base")
        root.resizable(True, True)
        root.minsize(960, 640)
        root.geometry("960x960")

        # Resetear configuraciones de grid del login
        for i in range(root.grid_size()[1]):
            root.grid_rowconfigure(i, weight=0)
        for i in range(root.grid_size()[0]):
            root.grid_columnconfigure(i, weight=0)
        root.grid_rowconfigure(1, weight=1)
        root.grid_columnconfigure(1, weight=1)

        # Construir la app principal
        _build_main(root, user, db, mqtt_bus, sensor_manager, data_receiver, auth_ctrl)

    login_panel = LoginPanel(
        root,
        auth_controller=auth_ctrl,
        on_login=_on_login_success,
        on_register=None,
    )
    login_panel.grid(row=0, column=0, sticky="nsew")
    login_panel_ref[0] = login_panel

    if not auth_service._db.user_exists():
        login_panel.set_first_user_info(True)

    # Cierre durante la pantalla de login
    def _on_close_during_login() -> None:
        logger.info("Login cancelado, saliendo")
        try:
            if root.winfo_exists():
                root.destroy()
        except tk.TclError:
            pass
        sys.exit(0)

    root.protocol("WM_DELETE_WINDOW", _on_close_during_login)

    logger.info("UI lista, entrando en mainloop (login)")
    root.mainloop()

    # Si el loop terminó sin usuario, fue porque cerraron la ventana
    if current_user is None:
        logger.info("Login cancelado, saliendo")
        sys.exit(0)

    logger.info("IoT Estación Base cerrada")


if __name__ == "__main__":
    main()