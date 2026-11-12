# src/station/main.py
import logging
import signal
import sys
import tkinter as tk
from logging.handlers import RotatingFileHandler

import customtkinter as ctk

from config.paths import db_path, log_path, migrate_legacy_db_once
from config.settings import Settings
from connection.broker import EmbeddedBroker
from connection.discovery import BrokerDiscovery
from connection.mqtt_client import MQTTEventBus
from controller.auth_controller import AuthController
from controller.board_controller import BoardController
from controller.event_controller import EventController
from data.database import Database
from domain.boards import resolve_board_identity
from domain.user import User
from logic.data_receiver import DataReceiver
from logic.device_scanner import USBScanner
from logic.mqtt_data_dispatcher import MQTTDataDispatcher
from logic.sensor_manager import SensorManager
from service.auth_service import AuthService
from service.board_service import BoardService
from service.event_service import EventService
from ui.main_window import MainWindow
from ui.panels.login_panel import LoginPanel
from ui.theme import apply_theme

_LOG_PATH = log_path()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        RotatingFileHandler(_LOG_PATH, maxBytes=1_000_000,
                            backupCount=3, encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

if migrate_legacy_db_once():
    logger.info("BD migrada desde la ubicación antigua dentro del repo")
DB_PATH = str(db_path())


def _build_main(root: ctk.CTk,
                current_user: User,
                db: Database,
                mqtt_bus: MQTTEventBus,
                sensor_manager: SensorManager,
                auth_ctrl: AuthController,
                board_service: BoardService,
                broker: EmbeddedBroker | None,
                on_logout=None) -> MainWindow:
    """Construye la UI autenticada. El pipeline de ingesta ya vive a nivel
    de proceso (ver main()): aquí solo servicios y vistas de la sesión."""
    logger.info("Usuario autenticado: %s (role=%s)",
                current_user.username, current_user.role)
    logger.info("Cargando boards para usuario %s", current_user.username)

    event_service = EventService(db)
    event_controller = EventController(event_service)
    board_controller = BoardController(board_service)

    window = MainWindow(
        root=root,
        mqtt_bus=mqtt_bus,
        board_ctrl=board_controller,
        event_ctrl=event_controller,
        user=current_user,
        auth_ctrl=auth_ctrl,
        sensor_manager=sensor_manager,
        on_logout=on_logout,
        broker=broker,
    )

    def session_cleanup() -> None:
        # Solo lo de la sesión. Los bridges, dispatcher y observers de proceso
        # siguen vivos entre logins (ingesta activa sin sesión).
        event_controller.cleanup()
        board_controller.cleanup()

    window.session_cleanup = session_cleanup  # type: ignore[attr-defined]
    logger.info("UI lista, entrando en mainloop")
    return window


def main() -> None:
    logger.info("Arrancando FoT Estación Base")

    settings = Settings.load()

    # --------------------------------------------------------------
    # Broker embebido amqtt
    # --------------------------------------------------------------
    broker: EmbeddedBroker | None = None
    try:
        broker = EmbeddedBroker(
            host=settings.broker_host,
            port=settings.broker_port,
            auth_mode=settings.mqtt_auth_mode,
        )
        broker.start(timeout=10)
        logger.info("Broker embebido amqtt en %s:%s (modo %s)",
                    settings.broker_host, settings.broker_port,
                    settings.mqtt_auth_mode)
    except Exception as e:
        logger.error("No se pudo iniciar el broker interno: %s", e)
        broker = None

    discovery: BrokerDiscovery | None = None
    if broker is not None:
        discovery = BrokerDiscovery(port=settings.broker_port)
        try:
            discovery.start()
        except Exception as e:
            logger.error("No se pudo registrar el servicio mDNS: %s", e)
            discovery = None

    # --------------------------------------------------------------
    # Infraestructura
    # --------------------------------------------------------------
    db = Database(DB_PATH)
    db.migrate()
    db.maintenance(
        raw_days=settings.raw_retention_days,
        hourly_days=getattr(settings, "hourly_retention_days", 180),
    )
    logger.info("Base de datos lista en %s", DB_PATH)

    auth_service = AuthService(
        db,
        allow_self_register=settings.allow_self_register,
    )

    mqtt_bus = MQTTEventBus("127.0.0.1", settings.broker_port)
    mqtt_bus.start()
    logger.info("Bus MQTT local hacia 127.0.0.1:%s", settings.broker_port)

    sensor_manager = SensorManager(mqtt_bus=mqtt_bus)
    data_receiver = DataReceiver(db)

    # board_service: instancia única por proceso (antes vivía en _build_main)
    board_service = BoardService(db=db, sensor_manager=sensor_manager)
    board_service.load_from_db()

    # --------------------------------------------------------------
    # Pipeline de ingesta A NIVEL DE PROCESO
    # --------------------------------------------------------------
    def _on_reading_process(board_id: str, data: dict) -> None:
        data_receiver.on_reading(board_id, data)
        board_service.on_board_reading(board_id)

    def _on_identify_process(board_id: str, data: dict) -> None:
        data_receiver.on_identify(board_id, data)
        board_service.on_sensor_identify(board_id, data)

    def _on_state_process(board_id: str, data: dict) -> None:
        board_service.on_board_state(board_id, data)

    def _on_disconnect_process(board_id: str) -> None:
        board_service.mark_board_disconnected(
            board_id, reason="Bridge sin heartbeat")

    sensor_manager.add_reading_observer(_on_reading_process)
    sensor_manager.add_identify_observer(_on_identify_process)
    sensor_manager.add_state_observer(_on_state_process)
    sensor_manager.add_disconnect_observer(_on_disconnect_process)

    def on_new_wifi_board(board_id: str, conn_type: str) -> None:
        if board_service.get_board(board_id) is None:
            board_service.register_wifi_board(board_id, ip="")
            logger.info("Placa WiFi auto-registrada desde MQTT: %s", board_id)

    mqtt_dispatcher = MQTTDataDispatcher(
        sensor_manager=sensor_manager,
        on_new_board=on_new_wifi_board,
    )
    mqtt_bus.register(mqtt_dispatcher, topic_filter="fot/+/sensores")
    mqtt_bus.register(mqtt_dispatcher, topic_filter="fot/+/estado")

    # --------------------------------------------------------------
    # USB scanner
    # --------------------------------------------------------------
    def on_new_usb_board(port_data: dict) -> None:
        board_id = resolve_board_identity(port_data)
        board_service.register_board(
            board_id=board_id,
            port=port_data["device"],
            conn_type="usb",
            factory_data=port_data,
        )
        logger.info("Placa USB detectada: %s en %s",
                    board_id, port_data["device"])

    def on_remove_usb_board(port_device: str) -> None:
        for board in board_service.get_boards():
            if board.port == port_device and board.conn == "usb":
                board_service.mark_board_disconnected(
                    board.id, f"Puerto {port_device} desconectado")
                logger.info(
                    "Placa USB desconectada: %s (puerto %s)",
                    board.id, port_device)
                break

    usb_scanner = USBScanner(
        on_new_board=on_new_usb_board,
        on_remove_board=on_remove_usb_board,
    )
    usb_scanner.start()

    # Relay

    def _on_relay_ack_process(board_id: str, data: dict) -> None:
        board_service.on_relay_ack(board_id, data)

    sensor_manager.add_relay_ack_observer(_on_relay_ack_process)
    
    # --------------------------------------------------------------
    # UI con login embebido
    # --------------------------------------------------------------
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

        if login_panel_ref[0]:
            login_panel_ref[0].destroy()
            login_panel_ref[0] = None

        root.title("FoT — Estación Base")
        root.resizable(True, True)
        root.minsize(960, 960)
        root.geometry("960x960")

        for i in range(root.grid_size()[1]):
            root.grid_rowconfigure(i, weight=0)
        for i in range(root.grid_size()[0]):
            root.grid_columnconfigure(i, weight=0)
        root.grid_rowconfigure(1, weight=1)
        root.grid_columnconfigure(1, weight=1)

        main_window_ref[0] = _build_main(
            root, user, db, mqtt_bus, sensor_manager, auth_ctrl,
            board_service, broker,
            on_logout=_on_logout,
        )

    def _on_logout() -> None:
        nonlocal current_user
        current_user = None

        if main_window_ref[0]:
            cleanup = getattr(main_window_ref[0], "session_cleanup", None)
            if cleanup:
                cleanup()
            main_window_ref[0].cleanup()
            main_window_ref[0] = None

        for widget in root.winfo_children():
            widget.destroy()

        for i in range(root.grid_size()[1]):
            root.grid_rowconfigure(i, weight=0)
        for i in range(root.grid_size()[0]):
            root.grid_columnconfigure(i, weight=0)
        root.grid_rowconfigure(0, weight=1)
        root.grid_columnconfigure(0, weight=1)

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

        if not auth_service.user_exists():
            login_panel.set_first_user_info(True)

        logger.info("Sesión cerrada, volviendo a pantalla de login")

    login_panel = LoginPanel(
        root,
        auth_controller=auth_ctrl,
        on_login=_on_login_success,
        on_register=None,
    )
    login_panel.grid(row=0, column=0, sticky="nsew")
    login_panel_ref[0] = login_panel

    if not auth_service.user_exists():
        login_panel.set_first_user_info(True)

    def on_close_process() -> None:
        logger.info("Cerrando FoT Estación Base")
        if main_window_ref[0]:
            session_cleanup = getattr(main_window_ref[0], "session_cleanup", None)
            if session_cleanup:
                session_cleanup()
            main_window_ref[0].cleanup()
            main_window_ref[0] = None
        board_service.stop()
        sensor_manager.disconnect_all()
        mqtt_bus.stop()
        if discovery is not None:
            discovery.stop()
        if broker is not None:
            broker.stop()
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