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
# Controladores
from controller.event_controller import EventController
from controller.export_controller import ExportController
from controller.irrigation_controller import IrrigationController
from controller.parcela_controller import ParcelaController
from controller.snapshot_controller import SnapshotController
from data.database import Database
from domain.components import Finca, Parcela
from domain.memento import ConfigManager
from domain.user import User
from logic.data_receiver import DataReceiver
from service.auth_service import AuthService
from service.board_service import BoardService
# Servicios
from service.event_service import EventService
from service.export_service import ExportService
from service.irrigation_service import IrrigationService
from service.parcela_service import ParcelaService
from service.snapshot_service import SnapshotService
from ui.dialogs.login_dialog import LoginDialog
# UI
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
    user = [None]  # mutable para capturar desde callback

    def on_login(u: User):
        user[0] = u

    LoginDialog(
        root,
        auth_ctrl._service,
        on_login=on_login,
        on_register=None,  # ← NO hay registro desde login inicial
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

    mqtt_bus = MQTTEventBus(BROKER_IP, BROKER_PORT)
    config_manager = ConfigManager()
    data_receiver = DataReceiver(db)  # ← SIN None, finca se asigna después

    try:
        mqtt_bus.start()
        logger.info("MQTT conectado a %s:%s", BROKER_IP, BROKER_PORT)
    except Exception as e:
        logger.error("No se pudo conectar al broker MQTT: %s", e)

    # ------------------------------------------------------------------
    # UI — Login primero
    # ------------------------------------------------------------------
    apply_theme()
    root = ctk.CTk()

    auth_ctrl = AuthController(auth_service)

    # Mostrar login modal
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
    data_receiver.set_finca(finca)  # ← NUEVO: asignar finca aquí
    logger.info("Finca cargada: %d parcelas para usuario %s",
                len(finca.get_children()), current_user.username)
    # DataReceiver necesita la finca
    # TODO: refactorizar DataReceiver para que reciba finca dinámicamente
    # o reconstruirlo aquí

    # ------------------------------------------------------------------
    # Capa de Servicios (con usuario)
    # ------------------------------------------------------------------
    event_service = EventService(db)
    board_service = BoardService(mqtt_bus, data_receiver)
    irrigation_service = IrrigationService(board_service, mqtt_bus, event_service)
    parcela_service = ParcelaService(
        finca, db, config_manager, irrigation_service, current_user.id
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
    irrigation_controller = IrrigationController(irrigation_service)
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
        irrig_ctrl=irrigation_controller,
        snap_ctrl=snapshot_controller,
        export_ctrl=export_controller,
        event_ctrl=event_controller,
        user=current_user,
        auth_ctrl=auth_ctrl,
    )

    # ------------------------------------------------------------------
    # Registro de observadores MQTT
    # ------------------------------------------------------------------
    mqtt_bus.register(data_receiver)
    mqtt_bus.register(window)

    # ------------------------------------------------------------------
    # Cierre limpio
    # ------------------------------------------------------------------
    def on_close() -> None:
        logger.info("Cerrando FoT Estación Base")
        board_service.stop()
        mqtt_bus.unregister(window)
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
