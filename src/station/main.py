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
from data.database import Database
from domain.user import User
from logic.data_receiver import DataReceiver
from logic.mqtt_data_dispatcher import MQTTDataDispatcher
from logic.sensor_manager import SensorManager
from logic.device_scanner import USBScanner
from service.auth_service import AuthService
from service.board_service import BoardService
from service.event_service import EventService
from ui.main_window import MainWindow
from ui.panels.login_panel import LoginPanel
from ui.theme import apply_theme
from domain.boards import resolve_board_identity

# --------------------------------------------------------------------------
# Bootstrap check
# --------------------------------------------------------------------------
_ok, _msg = bootstrap()
if not _ok:
    _root = tk.Tk()
    _root.withdraw()
    messagebox.showerror("FoT — Error de configuración", _msg)
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
                auth_ctrl: AuthController,
                board_service: BoardService,
                on_logout=None) -> MainWindow:
    """
    Construye la interfaz principal una vez que el login fue exitoso.
    Se ejecuta dentro del callback de login (todavía dentro de mainloop).

    NOTA: board_service y usb_scanner viven a nivel de proceso (creados una
    sola vez en main()) y se pasan como parámetro. NO se crean acá, porque
    esta función se ejecuta en cada login y crear instancias nuevas dejaba
    escáneres e instancias de servicio "zombie" corriendo en paralelo tras
    cada logout, pisando usuario_id en la DB de forma no determinística.
    """
    logger.info("Usuario autenticado: %s (role=%s)", current_user.username, current_user.role)
    logger.info("Cargando boards para usuario %s", current_user.username)

    # ------------------------------------------------------------------
    # Capa de Servicios
    # ------------------------------------------------------------------
    event_service = EventService(db)

    # ------------------------------------------------------------------
    # Conectar observers del SensorManager al DataReceiver.
    #
    # NOTA: como sensor_manager vive a nivel de proceso y _build_main()
    # se ejecuta en cada login, estos observers se registran una vez por
    # sesión. Deben des-registrarse en session_cleanup() al cerrar sesión,
    # o si el usuario vuelve a loguearse, DataReceiver.on_reading()
    # terminaría llamándose varias veces por cada lectura (una por cada
    # login acumulado).
    # ------------------------------------------------------------------
    def on_sensor_reading(board_id: str, data: dict):
        data_receiver.on_reading(board_id, data)

    def on_sensor_identify(board_id: str, data: dict):
        data_receiver.on_identify(board_id, data)
        board_service.on_sensor_identify(board_id, data)

    sensor_manager.add_reading_observer(on_sensor_reading)
    sensor_manager.add_identify_observer(on_sensor_identify)

    # ------------------------------------------------------------------
    # Dispatcher MQTT global para todas las placas WiFi
    # ------------------------------------------------------------------
    def on_new_wifi_board(board_id: str, conn_type: str) -> None:
        """Auto-registra una placa WiFi detectada vía MQTT si no existe."""
        existing = board_service.get_board(board_id)
        if existing is None:
            board_service.register_wifi_board(board_id, "localhost")
            logger.info("Placa WiFi auto-registrada desde MQTT: %s", board_id)

    mqtt_dispatcher = MQTTDataDispatcher(
        sensor_manager=sensor_manager,
        on_reading=on_sensor_reading,
        on_identify=on_sensor_identify,
        on_new_board=on_new_wifi_board,
    )
    mqtt_bus.register(mqtt_dispatcher, topic_filter="fot/+/sensores")
    mqtt_bus.register(mqtt_dispatcher, topic_filter="fot/+/estado")

    # ------------------------------------------------------------------
    # Capa de Controladores
    # ------------------------------------------------------------------
    event_controller = EventController(event_service)
    board_controller = BoardController(board_service)

    # ------------------------------------------------------------------
    # Vista principal
    # ------------------------------------------------------------------
    window = MainWindow(
        root=root,
        mqtt_bus=mqtt_bus,
        board_ctrl=board_controller,
        event_ctrl=event_controller,
        user=current_user,
        auth_ctrl=auth_ctrl,
        sensor_manager=sensor_manager,
        on_logout=on_logout,
    )

    # ------------------------------------------------------------------
    # Limpieza de fin de SESIÓN (no de proceso).
    # usb_scanner y mqtt_bus.stop() NO van acá: viven a nivel de proceso
    # y se cierran una sola vez en on_close_process().
    # ------------------------------------------------------------------
    def session_cleanup() -> None:
        sensor_manager.remove_reading_observer(on_sensor_reading)
        sensor_manager.remove_identify_observer(on_sensor_identify)
        sensor_manager.disconnect_all()
        mqtt_bus.unregister(mqtt_dispatcher)
        event_controller.cleanup()
        board_controller.cleanup()

    window.session_cleanup = session_cleanup  # type: ignore[attr-defined]

    logger.info("UI lista, entrando en mainloop")
    return window


def main() -> None:
    logger.info("Arrancando FoT Estación Base")

    # ------------------------------------------------------------------
    # Infraestructura
    # ------------------------------------------------------------------
    db = Database(DB_PATH)
    db.initialize()
    db.purge_old_readings(days=30)
    logger.info("Base de datos lista en %s", DB_PATH)

    auth_service = AuthService(db)
    auth_service.ensure_admin_exists()

    mqtt_bus = MQTTEventBus("localhost", 1883)
    try:
        mqtt_bus.start()
        logger.info("MQTT broker local en %s:%s", "localhost", 1883)
    except Exception as e:
        logger.error("No se pudo iniciar broker MQTT: %s", e)

    sensor_manager = SensorManager(mqtt_bus=mqtt_bus)
    data_receiver = DataReceiver(db)

    # ------------------------------------------------------------------
    # board_service y usb_scanner: ÚNICA instancia por proceso.
    # Antes vivían dentro de _build_main() y se recreaban en cada login,
    # dejando escáneres e instancias de servicio viejas corriendo en
    # paralelo (nunca se detenían en _on_logout), lo que pisaba
    # usuario_id en la DB con valores desactualizados de forma
    # no determinística. Ahora se crean una sola vez acá.
    # ------------------------------------------------------------------
    board_service = BoardService(db=db, sensor_manager=sensor_manager)
    board_service.load_from_db()

    def on_new_usb_board(port_data: dict) -> None:
        """Auto-registra (o actualiza el puerto de) una placa detectada por USB."""
        board_id = board_id = resolve_board_identity(port_data)
        board_service.register_board(
            board_id=board_id,
            port=port_data["device"],
            conn_type="usb",
            factory_data=port_data,
        )
        logger.info("Placa USB detectada: %s en %s", board_id, port_data["device"])

    def on_remove_usb_board(port_device: str) -> None:
        """Marca una placa como desconectada cuando su puerto físico desaparece."""
        for board in board_service.get_boards():
            if board.port == port_device and board.conn == "usb":
                board_service.mark_board_disconnected(
                    board.id, f"Puerto {port_device} desconectado"
                )
                logger.info(
                    "Placa USB desconectada físicamente: %s (puerto %s)",
                    board.id, port_device,
                )
                break

    usb_scanner = USBScanner(
        on_new_board=on_new_usb_board,
        on_remove_board=on_remove_usb_board,
    )
    usb_scanner.start()

    # ------------------------------------------------------------------
    # UI — Login embebido en la única ventana CTk
    # ------------------------------------------------------------------
    apply_theme()

    root = ctk.CTk()
    root.title("FoT — Iniciar sesión")
    root.geometry("600x800")
    root.resizable(False, False)
    root.grid_columnconfigure(0, weight=1)
    root.grid_rowconfigure(0, weight=1)

    auth_ctrl = AuthController(auth_service)

    current_user: User | None = None
    login_panel_ref: list[LoginPanel | None] = [None]
    main_window_ref: list[MainWindow | None] = [None]

    def _on_login_success(user: User) -> None:
        nonlocal current_user
        current_user = user

        # Destruir panel de login y limpiar la ventana
        if login_panel_ref[0]:
            login_panel_ref[0].destroy()
            login_panel_ref[0] = None

        # Reconfigurar la misma ventana para la app principal
        root.title("FoT — Estación Base")
        root.resizable(True, True)
        root.minsize(960, 960)
        root.geometry("960x960")

        # Resetear configuraciones de grid del login
        for i in range(root.grid_size()[1]):
            root.grid_rowconfigure(i, weight=0)
        for i in range(root.grid_size()[0]):
            root.grid_columnconfigure(i, weight=0)
        root.grid_rowconfigure(1, weight=1)
        root.grid_columnconfigure(1, weight=1)

        # Construir la app principal (board_service se reutiliza, no se crea de nuevo)
        main_window_ref[0] = _build_main(
            root, user, db, mqtt_bus, sensor_manager, data_receiver, auth_ctrl,
            board_service,
            on_logout=_on_logout,
        )

    def _on_logout() -> None:
        """Callback llamado cuando el usuario cierra sesión desde SettingsPanel."""
        nonlocal current_user
        current_user = None

        # Limpieza de la SESIÓN (no del proceso: usb_scanner y mqtt_bus siguen vivos)
        if main_window_ref[0]:
            session_cleanup = getattr(main_window_ref[0], "session_cleanup", None)
            if session_cleanup:
                session_cleanup()
            main_window_ref[0].cleanup()
            main_window_ref[0] = None

        # Limpiar todos los widgets del root
        for widget in root.winfo_children():
            widget.destroy()

        # Resetear grid
        for i in range(root.grid_size()[1]):
            root.grid_rowconfigure(i, weight=0)
        for i in range(root.grid_size()[0]):
            root.grid_columnconfigure(i, weight=0)
        root.grid_rowconfigure(0, weight=1)
        root.grid_columnconfigure(0, weight=1)

        # Volver a pantalla de login
        root.title("FoT — Iniciar sesión")
        root.geometry("600x800")
        root.resizable(False, False)

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

        logger.info("Sesión cerrada, volviendo a pantalla de login")

    # Login inicial
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

    # ------------------------------------------------------------------
    # Cierre del PROCESO completo (única vez que se detiene usb_scanner/mqtt/db)
    # ------------------------------------------------------------------
    def on_close_process() -> None:
        logger.info("Cerrando FoT Estación Base")
        if main_window_ref[0]:
            session_cleanup = getattr(main_window_ref[0], "session_cleanup", None)
            if session_cleanup:
                session_cleanup()
        sensor_manager.disconnect_all()
        mqtt_bus.stop()
        usb_scanner.stop()
        db.close()
        try:
            if root.winfo_exists():
                root.destroy()
        except tk.TclError:
            pass
        sys.exit(0)

    root.protocol("WM_DELETE_WINDOW", on_close_process)

    def _handle_sigterm(_signum: int, _frame: object) -> None:
        root.after(0, on_close_process)

    signal.signal(signal.SIGTERM, _handle_sigterm)

    logger.info("UI lista, entrando en mainloop (login)")
    root.mainloop()

    logger.info("IoT Estación Base cerrada")


if __name__ == "__main__":
    main()