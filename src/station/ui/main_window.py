# ui/main_window.py
import logging
import tkinter as tk

import customtkinter as ctk
from controller.bluetooth_controller import BluetoothController
from controller.wifi_controller import WiFiController
from ui.dialogs.firmware_dialog import FirmwareDialog
from ui.dialogs.register_dialog import RegisterDialog
from ui.panels.admin_panel import AdminPanel
from ui.panels.arduino_panel import ArduinoPanel
from ui.panels.dht11_panel import DHT11Panel
from ui.panels.help_panel import HelpPanel
from ui.panels.login_panel import LoginPanel
from ui.panels.settings_panel import SettingsPanel
from ui.theme import FONT_NORMAL, FONT_SMALL, TOPBAR_HEIGHT
from ui.widgets.notification_manager import NotificationManager
from ui.widgets.notification_panel import NotificationPanel
from ui.widgets.side_bar import SideBar
from ui.widgets.status_bar import StatusBar
from ui.widgets.top_bar import TopBar
from domain.boards import Board

from ui.dialogs.bluetooth_scan_dialog import BluetoothScanDialog
from ui.dialogs.wifi_scan_dialog import WiFiScanDialog

logger = logging.getLogger(__name__)


class MainWindow:
    def __init__(self,
                 root: ctk.CTk,
                 mqtt_bus,
                 board_ctrl,
                 event_ctrl,
                 auth_ctrl,
                 sensor_manager,
                 user=None,
                 on_logout=None):
        self._root = root
        self._mqtt_bus = mqtt_bus
        self._sensor_manager = sensor_manager

        self._board_ctrl = board_ctrl
        self._event_ctrl = event_ctrl
        self._auth_ctrl = auth_ctrl
        self._user = user
        self._on_logout = on_logout

        self._selected_board_id: str | None = None
        self._current_panel: ctk.CTkFrame | None = None
        self._notif_panel_visible = False

        # Sistema de notificaciones
        self._notif_mgr = NotificationManager(root)

        self._root.title("FoT — Estación Base")
        self._root.minsize(960, 640)
        self._root.grid_rowconfigure(1, weight=1)
        self._root.grid_columnconfigure(1, weight=1)

        self._build_layout()

        if self._user is not None:
            self._setup_authenticated_ui()
        else:
            self._show_auth_ui()

        self._status_bar.start_clock(root)

    def _build_layout(self) -> None:
        self._top_bar = TopBar(
            self._root,
            notification_manager=self._notif_mgr,
            on_bell_click=self._on_bell_clicked,
        )
        self._top_bar.grid(row=0, column=0, columnspan=2, sticky="ew")

        self._side_bar = SideBar(self._root, on_navigate=self._navigate)
        self._side_bar.grid(row=1, column=0, sticky="ns", rowspan=2)

        self._status_bar = StatusBar(self._root)
        self._status_bar.grid(row=2, column=1, sticky="ew")

        self._content_area = ctk.CTkFrame(self._root)
        self._content_area.grid(row=1, column=1, sticky="nsew")
        self._content_area.grid_rowconfigure(0, weight=1)
        self._content_area.grid_columnconfigure(0, weight=1)

        # Panel de notificaciones (inicialmente oculto, overlay flotante)
        self._notif_panel = None

        self._panels: dict[str, ctk.CTkFrame] = {}

        # Login
        self.login_panel = LoginPanel(
            self._content_area,
            auth_controller=self._auth_ctrl,
            on_login=self._on_login_success,
        )
        self._panels["login"] = self.login_panel

        # DHT11 Panel
        self.dht11_panel = DHT11Panel(
            self._content_area,
            on_select_board=self._on_select_board,
        )
        self._panels["dht11"] = self.dht11_panel

        # Arduino Panel
        self.arduino_panel = ArduinoPanel(
            self._content_area,
            on_register=self._on_register_board,
            on_connect=self._on_connect_board,
            on_disconnect=self._on_disconnect_board,
            on_remove=self._on_remove_board,
            on_read_now=self._on_read_now,
            on_scan_bluetooth=self._on_scan_bluetooth,
            on_scan_wifi=self._on_scan_wifi,
            on_firmware_update=self._on_firmware_update,
        )
        self._panels["arduinos"] = self.arduino_panel

        self.help_panel = HelpPanel(self._content_area)
        self._panels["ayuda"] = self.help_panel

        # Admin Panel
        self.admin_panel = AdminPanel(
            self._content_area,
            auth_controller=self._auth_ctrl,
            on_register_user=self._open_register_dialog,
        )
        self.admin_panel.set_delete_callback(self._on_admin_delete_user)
        self.admin_panel.set_toggle_active_callback(self._on_admin_toggle_active)
        self.admin_panel.set_reset_password_callback(self._on_admin_reset_password)
        self._panels["admin"] = self.admin_panel

        # Settings Panel (con auth_controller, user y on_logout)
        self.settings_panel = SettingsPanel(
            self._content_area,
            notification_manager=self._notif_mgr,
            auth_controller=self._auth_ctrl,
            user=self._user,
            on_logout=self._do_logout,
        )
        self._panels["ajustes"] = self.settings_panel

        # Controladores de escaneo
        self._bt_ctrl = BluetoothController()
        self._wifi_ctrl = WiFiController()

    def _show_auth_ui(self) -> None:
        self._side_bar.grid_remove()
        self._top_bar.grid_remove()
        self._status_bar.grid_remove()
        self._navigate("login")

    def _setup_authenticated_ui(self) -> None:
        self._side_bar.grid()
        self._top_bar.grid()
        self._status_bar.grid()

        if self._user.is_admin():
            self._side_bar.add_nav_button("admin", "Admin", "Gestión de usuarios")

        self._load_initial_data()

        self._board_ctrl.set_ui_callback(self._on_board_updated)
        self._event_ctrl.set_ui_callback(self._on_event_logged)

        self._sensor_manager.set_callbacks(
            on_reading=self._on_sensor_reading,
            on_identify=self._on_sensor_identify
        )

        self._current_panel = None
        self._navigate("dht11")
        self._side_bar.set_active("dht11")

        # Notificación de bienvenida
        self._notif_mgr.notify(
            "Sesión iniciada",
            f"Bienvenido, {self._user.username}",
            tipo="success"
        )

    def _on_login_success(self, user) -> None:
        self._user = user
        self._setup_authenticated_ui()

    def _navigate(self, section: str) -> None:
        # Si el panel de notificaciones está visible, ocultarlo
        if self._notif_panel_visible:
            self._hide_notification_panel()

        panel = self._panels.get(section)
        if panel is None:
            return

        if self._current_panel is not None:
            self._current_panel.grid_remove()
        panel.grid(row=0, column=0, sticky="nsew")
        self._current_panel = panel
        self._side_bar.set_active(section)

    def _load_initial_data(self) -> None:
        # DHT11 boards
        dht11_boards = self._board_ctrl.get_boards_by_sketch("dht11")
        self.dht11_panel.set_boards(dht11_boards)

        # Eventos
        history = self._event_ctrl.load_history()
        for event in history:
            self.dht11_panel.add_event(event["text"], event["tipo"])

        # All boards
        boards = self._board_ctrl.get_boards()
        for board in boards:
            self.arduino_panel.update_board(board)

        # Actualizar contadores en barras
        self._top_bar.update_boards_count(len(boards))
        self._status_bar.update_usb_count(
            sum(1 for b in boards if b.conn == "usb")
        )

        if self._user and self._user.is_admin():
            self._refresh_admin_users()

    # --- Callbacks DHT11 Panel ---
    def _on_select_board(self, board_id: str | None):
        self._selected_board_id = board_id
        if board_id:
            readings = self._board_ctrl.get_readings(board_id, limit=100)
            self.dht11_panel.show_history(board_id, readings)

    # --- Callbacks Arduino Panel ---
    def _on_register_board(self, board_id: str):
        logger.info("Solicitud de registro para board: %s", board_id)

    def _on_connect_board(self, board_id: str):
        ok, msg = self._board_ctrl.connect(board_id)
        if ok:
            self._notif_mgr.notify(
                "Placa conectada",
                f"{board_id} está ahora en línea",
                tipo="success"
            )
            self._status_bar.mark_message_received()
        else:
            self._notif_mgr.notify(
                "Error de conexión",
                f"No se pudo conectar {board_id}: {msg}",
                tipo="error"
            )
            logger.error("Error conectando %s: %s", board_id, msg)

    def _on_disconnect_board(self, board_id: str):
        self._board_ctrl.disconnect(board_id)
        self._notif_mgr.notify(
            "Placa desconectada",
            f"{board_id} se desconectó",
            tipo="warning"
        )

    def _on_remove_board(self, board_id: str):
        self._board_ctrl.remove(board_id)
        self._notif_mgr.notify(
            "Placa eliminada",
            f"{board_id} fue removida del sistema",
            tipo="info"
        )

    def _on_read_now(self, board_id: str):
        self._board_ctrl.read_now(board_id)

    def _on_scan_bluetooth(self) -> None:
        BluetoothScanDialog(
            self._root,
            on_register=self._on_register_scanned_device,
        )

    def _on_scan_wifi(self) -> None:
        WiFiScanDialog(
            self._root,
            on_register=self._on_register_scanned_device,
        )

    def _on_firmware_update(self, board_id: str):
        info = self._board_ctrl.get_board(board_id)
        if not info:
            return
        FirmwareDialog(
            self._root,
            board_id=info.id,
            port=info.port or "",
            current_version=info.sketch_version or "Desconocida",
        )

    # --- Callbacks generales ---
    def _on_sensor_reading(self, board_id: str, data: dict):
        self._root.after(0, lambda: self._update_sensor_ui(board_id, data))

    def _update_sensor_ui(self, board_id: str, data: dict):
        board = self._board_ctrl.get_board(board_id)
        if board and board.sketch_id == "dht11":
            self.dht11_panel.update_reading(board_id, data)
        self.arduino_panel.update_reading(board_id, data)
        self._status_bar.mark_message_received()

    def _on_sensor_identify(self, board_id: str, data: dict):
        logger.info("Identificado %s: %s", board_id, data)
        self._notif_mgr.notify(
            "Placa identificada",
            f"{board_id}: {data.get('name', 'Unknown')} v{data.get('version', '?')}",
            tipo="info"
        )

    def _on_board_updated(self, board: Board):
        self._root.after(0, lambda: self.arduino_panel.update_board(board))
        if board.sketch_id == "dht11":
            self._root.after(0, lambda: self.dht11_panel.update_board(board))
        # Actualizar contadores
        boards = self._board_ctrl.get_boards()
        self._top_bar.update_boards_count(len(boards))
        self._status_bar.update_usb_count(
            sum(1 for b in boards if b.conn == "usb")
        )

    def _on_event_logged(self, text: str, tipo: str):
        self._root.after(0, lambda: self.dht11_panel.add_event(text, tipo))
        if "error" in tipo.lower() or "fallo" in tipo.lower():
            self._notif_mgr.notify(
                "Alerta del sistema",
                text,
                tipo="error"
            )
            self._status_bar.update_alerts(1)

    def _on_bell_clicked(self):
        """Abrir/ocultar panel de notificaciones."""
        if self._notif_panel_visible:
            self._hide_notification_panel()
        else:
            self._show_notification_panel()

    def _show_notification_panel(self):
        """Muestra el panel de notificaciones como overlay flotante."""
        if self._notif_panel is not None:
            self._notif_panel.destroy()

        self._notif_panel = NotificationPanel(
            self._root,
            notification_manager=self._notif_mgr,
            on_close=self._hide_notification_panel,
        )
        # Posicionar en la esquina superior derecha, debajo del top bar
        self._notif_panel.place(
            relx=1.0, x=-20, y=TOPBAR_HEIGHT + 10,
            anchor="ne",
            relwidth=0.35, relheight=0.6
        )
        self._notif_panel_visible = True
        logger.info("Panel de notificaciones abierto")

    def _hide_notification_panel(self):
        """Oculta el panel de notificaciones."""
        if self._notif_panel is not None:
            self._notif_panel.destroy()
            self._notif_panel = None
        self._notif_panel_visible = False
        logger.info("Panel de notificaciones cerrado")

    # --- Admin ---
    def _open_register_dialog(self):
        RegisterDialog(self._root, self._auth_ctrl,
                       on_success=lambda _: self._refresh_admin_users(),
                       allow_admin_creation=self._auth_ctrl.can_register(self._user))

    def _on_admin_delete_user(self, user_id: int):
        ok, _ = self._auth_ctrl.delete_user(self._user, user_id)
        if ok:
            self._refresh_admin_users()
            self._notif_mgr.notify(
                "Usuario eliminado",
                f"El usuario ID {user_id} fue eliminado",
                tipo="info"
            )

    def _refresh_admin_users(self):
        ok, users = self._auth_ctrl.list_users(self._user)
        if ok:
            self.admin_panel.refresh_users(users, self._user.id)

    def cleanup(self):
        self._status_bar.stop_clock()
        self._event_ctrl.cleanup()
        self._board_ctrl.cleanup()
        if self._notif_mgr:
            self._notif_mgr.remove_observer(self._top_bar._update_badge)
        if self._notif_panel is not None:
            self._notif_panel.destroy()

    def _on_register_scanned_device(self, board_id: str, address: str, conn_type: str) -> None:
        if conn_type == "bluetooth":
            board = self._board_ctrl.register_bluetooth_board(board_id, address)
        elif conn_type == "wifi":
            board = self._board_ctrl.register_wifi_board(board_id, address)
        else:
            return

        self._notif_mgr.notify(
            "Dispositivo registrado",
            f"{board_id} ({conn_type.upper()})",
            tipo="success"
        )
        self._event_ctrl.append(
            board_id=board_id,
            descripcion=f"Dispositivo {conn_type} registrado: {board_id}",
            tipo="registro"
        )

    def _on_admin_toggle_active(self, user_id: int, active: bool):
        ok, msg = self._auth_ctrl.toggle_user_active(self._user, user_id, active)
        if ok:
            self._refresh_admin_users()
            estado = "activada" if active else "desactivada"
            self._notif_mgr.notify(
                f"Cuenta {estado}",
                f"Usuario ID {user_id} {estado}",
                tipo="info"
            )

    def _on_admin_reset_password(self, user_id: int, username: str):
        ok, result = self._auth_ctrl.reset_password(self._user, user_id)
        if not ok:
            self._notif_mgr.notify(
                "Error",
                f"No se pudo resetear contraseña de {username}",
                tipo="error"
            )
            return

        # Diálogo con password temporal
        dialog = ctk.CTkToplevel(self._root)
        dialog.title("Contraseña temporal generada")
        dialog.geometry("400x200")
        dialog.resizable(False, False)

        ctk.CTkLabel(
            dialog,
            text=f"Nueva contraseña para {username}:",
            font=FONT_NORMAL
        ).pack(pady=(20, 10))

        entry = ctk.CTkEntry(dialog, font=("Courier New", 14), width=280)
        entry.insert(0, result)
        entry.configure(state="readonly")
        entry.pack(padx=20)
        entry.select_range(0, "end")

        ctk.CTkLabel(
            dialog,
            text="⚠️ El usuario deberá cambiarla al iniciar sesión",
            font=FONT_SMALL,
            text_color="orange"
        ).pack(pady=10)

        def _copy_and_close():
            self._root.clipboard_clear()
            self._root.clipboard_append(result)
            dialog.destroy()

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=(0, 20))

        ctk.CTkButton(
            btn_frame,
            text="📋 Copiar y cerrar",
            command=_copy_and_close
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            btn_frame,
            text="Cerrar",
            fg_color="gray",
            command=dialog.destroy
        ).pack(side="left", padx=4)

        dialog.update()
        dialog.after(10, dialog.grab_set)

        self._notif_mgr.notify(
            "Contraseña reseteada",
            f"Contraseña temporal generada para {username}",
            tipo="warning"
        )

    # ================================================================
    # LOGOUT
    # ================================================================
    def _do_logout(self):
        """Cierra la sesión actual y vuelve a la pantalla de login."""
        logger.info("Cerrando sesión de usuario: %s", self._user.username if self._user else "unknown")

        if self._notif_mgr:
            self._notif_mgr.reset()

        # Notificar logout (antes de cleanup para que el toast se muestre)
        self._notif_mgr.notify(
            "Sesión cerrada",
            f"Hasta luego, {self._user.username if self._user else 'usuario'}",
            tipo="info"
        )

        # Limpiar callbacks del sensor manager
        self._sensor_manager.set_callbacks(on_reading=None, on_identify=None)

        # Cleanup centralizado (incluye _event_ctrl, _board_ctrl, timers, etc.)
        self.cleanup()

        # Ocultar panel de notificaciones si está visible
        if self._notif_panel_visible:
            self._hide_notification_panel()

        # Ocultar sidebar, topbar, statusbar
        self._side_bar.grid_remove()
        self._top_bar.grid_remove()
        self._status_bar.grid_remove()

        # Limpiar área de contenido
        if self._current_panel is not None:
            self._current_panel.grid_remove()
            self._current_panel = None

        # Resetear usuario
        self._user = None

        # Volver a mostrar login
        self._navigate("login")

        # Llamar al callback externo si existe
        if self._on_logout:
            self._on_logout()
