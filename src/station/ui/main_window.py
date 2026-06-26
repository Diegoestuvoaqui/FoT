# ui/main_window.py
import logging
import tkinter as tk

import customtkinter as ctk

from ui.dialogs.assign_arduino_dialog import AssignArduinoDialog
from ui.dialogs.export_dialog import ExportDialog
from ui.dialogs.firmware_dialog import FirmwareDialog
from ui.dialogs.register_dialog import RegisterDialog
from ui.panels.admin_panel import AdminPanel
from ui.panels.arduino_panel import ArduinoPanel
from ui.panels.help_panel import HelpPanel
from ui.panels.login_panel import LoginPanel
from ui.panels.main_panel import MainPanel
from ui.theme import FONT_NORMAL
from ui.widgets.side_bar import SideBar
from ui.widgets.status_bar import StatusBar
from ui.widgets.top_bar import TopBar

logger = logging.getLogger(__name__)


class MainWindow:
    """
    Vista principal — orquestación de UI.
    Integra SensorManager para conexiones USB/Bluetooth/WiFi.
    """

    def __init__(self,
                 root: ctk.CTk,
                 finca,
                 mqtt_bus,
                 parcela_ctrl,
                 board_ctrl,
                 snap_ctrl,
                 export_ctrl,
                 event_ctrl,
                 auth_ctrl,
                 sensor_manager,  # NUEVO
                 user=None):
        self._root = root
        self._finca = finca
        self._mqtt_bus = mqtt_bus
        self._sensor_manager = sensor_manager  # NUEVO

        # Controllers
        self._parcela_ctrl = parcela_ctrl
        self._board_ctrl = board_ctrl
        self._snap_ctrl = snap_ctrl
        self._export_ctrl = export_ctrl
        self._event_ctrl = event_ctrl
        self._auth_ctrl = auth_ctrl
        self._user = user

        self._selected_parcela_id: str | None = None
        self._current_panel: ctk.CTkFrame | None = None

        # Configuración ventana
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

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------
    def _build_layout(self) -> None:
        # Top bar
        self._top_bar = TopBar(self._root, on_bell_click=None)
        self._top_bar.grid(row=0, column=0, columnspan=2, sticky="ew")

        # Side bar
        self._side_bar = SideBar(self._root, on_navigate=self._navigate)
        self._side_bar.grid(row=1, column=0, sticky="ns", rowspan=2)

        # Status bar
        self._status_bar = StatusBar(self._root)
        self._status_bar.grid(row=2, column=1, sticky="ew")

        # Contenedor de paneles
        self._content_area = ctk.CTkFrame(self._root)
        self._content_area.grid(row=1, column=1, sticky="nsew")
        self._content_area.grid_rowconfigure(0, weight=1)
        self._content_area.grid_columnconfigure(0, weight=1)

        self._panels: dict[str, ctk.CTkFrame] = {}

        # Panel de autenticación
        self.login_panel = LoginPanel(
            self._content_area,
            auth_controller=self._auth_ctrl,
            on_login=self._on_login_success,
        )
        self._panels["login"] = self.login_panel

        # Panel principal de parcelas
        self.main_panel = MainPanel(
            self._content_area,
            on_add_parcela=self._on_add_parcela,
            on_delete_parcela=self._on_delete_parcela,
            on_select_parcela=self._on_select_parcela,
            on_apply_thresholds=self._on_apply_thresholds,
            on_mode_change=self._on_mode_change,
            # Eliminados: on_irrigate, on_stop
        )
        self._panels["parcelas"] = self.main_panel

        # Panel Arduino — NUEVO con sensor_manager
        self.arduino_panel = ArduinoPanel(
            self._content_area,
            on_assign=self._on_assign_board,
            on_unassign=self._on_unassign_board,
            on_read_now=self._on_read_now,  # NUEVO
            on_scan_bluetooth=self._on_scan_bluetooth,  # NUEVO
            on_scan_wifi=self._on_scan_wifi,  # NUEVO
        )
        self._panels["arduinos"] = self.arduino_panel

        # Help panel
        self.help_panel = HelpPanel(self._content_area)
        self._panels["ayuda"] = self.help_panel

        # Admin panel
        self.admin_panel = AdminPanel(
            self._content_area,
            auth_controller=self._auth_ctrl,
            on_register_user=self._open_register_dialog,
        )
        self.admin_panel.set_delete_callback(self._on_admin_delete_user)
        self._panels["admin"] = self.admin_panel

    # ------------------------------------------------------------------
    # Autenticación
    # ------------------------------------------------------------------
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
            self._side_bar.add_nav_button(
                "admin", "Admin", "Gestión de usuarios"
            )

        self._load_initial_data()

        # Callbacks de controllers
        self._parcela_ctrl.set_ui_callback(
            on_refresh=self._refresh_parcela_list,
            on_select=self._on_select_parcela
        )
        self._event_ctrl.set_ui_callback(self._on_event_logged)
        self._board_ctrl.set_ui_callback(self._on_board_updated)

        # Callback de sensor_manager para lecturas en tiempo real
        self._sensor_manager.set_callbacks(
            on_reading=self._on_sensor_reading,
            on_identify=self._on_sensor_identify
        )

        self._current_panel = None
        self._navigate("parcelas")
        self._side_bar.set_active("parcelas")

    def _on_login_success(self, user) -> None:
        self._user = user
        logger.info("Login: %s", user.username)
        self._setup_authenticated_ui()

    # ------------------------------------------------------------------
    # Navegación
    # ------------------------------------------------------------------
    def _navigate(self, section: str) -> None:
        if section == "exportar":
            self._on_export()
            return

        panel = self._panels.get(section)
        if panel is None:
            return

        if self._current_panel is not None:
            self._current_panel.grid_remove()
        panel.grid(row=0, column=0, sticky="nsew")
        self._current_panel = panel
        self._side_bar.set_active(section)

    # ------------------------------------------------------------------
    # Carga inicial
    # ------------------------------------------------------------------
    def _load_initial_data(self) -> None:
        # Parcelas
        parcelas = self._parcela_ctrl.list_parcelas()
        self.main_panel.set_parcelas(parcelas)

        # Eventos históricos
        history = self._event_ctrl.load_history(self._finca)
        for event in history:
            self.main_panel.add_event(event["text"], event["tipo"])

        # Boards
        boards = self._board_ctrl.get_boards()
        for board in boards:
            self.arduino_panel.update_board(board)

        # Admin
        if self._user and self._user.is_admin():
            self._refresh_admin_users()

    # ------------------------------------------------------------------
    # Admin callbacks
    # ------------------------------------------------------------------
    def _open_register_dialog(self) -> None:
        allow_admin = self._auth_ctrl.can_register(self._user)
        RegisterDialog(
            self._root,
            self._auth_ctrl,
            on_success=lambda username: self._refresh_admin_users(),
            allow_admin_creation=allow_admin,
        )

    def _on_admin_delete_user(self, user_id: int) -> None:
        ok, error = self._auth_ctrl.delete_user(self._user, user_id)
        if ok:
            self._refresh_admin_users()
        else:
            from ui.error_handler import ErrorCode, ErrorHandler
            ErrorHandler.show(ErrorCode.ERR_DB_WRITE, self._root)

    def _refresh_admin_users(self) -> None:
        ok, users = self._auth_ctrl.list_users(self._user)
        if ok:
            self.admin_panel.refresh_users(users, self._user.id)

    # ------------------------------------------------------------------
    # Callbacks de SensorManager (NUEVOS)
    # ------------------------------------------------------------------
    def _on_sensor_reading(self, parcela_id: str, data: dict) -> None:
        """Llegó lectura de sensor — actualizar UI."""
        self._root.after(0, lambda: self.arduino_panel.update_reading(parcela_id, data))

    def _on_sensor_identify(self, parcela_id: str, data: dict) -> None:
        """Placa se identificó."""
        logger.info("Identificado %s: %s", parcela_id, data)

    # ------------------------------------------------------------------
    # Callbacks de UI → Controller (Parcelas)
    # ------------------------------------------------------------------
    def _on_add_parcela(self) -> None:
        dialog = _InputDialog(self._root, "Nueva parcela", ["ID:", "Nombre:"])
        if not dialog.result:
            return
        pid = dialog.result[0].strip()
        name = dialog.result[1].strip()

        ok, error = self._parcela_ctrl.add_parcela(pid, name)
        if not ok:
            from ui.error_handler import ErrorCode, ErrorHandler
            ErrorHandler.show(ErrorCode.ERR_ADD_PARCELA, self._root)

    def _on_delete_parcela(self, parcela_id: str | None = None) -> None:
        target = parcela_id or self._selected_parcela_id
        if not target:
            from ui.error_handler import ErrorCode, ErrorHandler
            ErrorHandler.show(ErrorCode.ERR_DELETE_PARCELA, self._root)
            return

        from tkinter.messagebox import askyesno
        confirm = askyesno(
            "Confirmar eliminación",
            f"¿Eliminar la parcela '{target}'?\nEsta acción no se puede deshacer."
        )
        if not confirm:
            return

        ok, error = self._parcela_ctrl.delete_parcela(target)
        if not ok:
            from ui.error_handler import ErrorCode, ErrorHandler
            if "no encontrada" in error:
                ErrorHandler.show(ErrorCode.ERR_DELETE_PARCELA, self._root)
            else:
                ErrorHandler.show(ErrorCode.ERR_DB_WRITE, self._root)
            return

        if self._selected_parcela_id == target:
            self._selected_parcela_id = None
            self.main_panel.lbl_title.configure(
                text="— Ninguna parcela seleccionada —")

    def _on_select_parcela(self, parcela_id: str | None) -> None:
        self._selected_parcela_id = parcela_id
        parcela = self._parcela_ctrl.select_parcela(parcela_id)
        if parcela:
            self.main_panel.update_detail(parcela)
        else:
            self.main_panel.lbl_title.configure(
                text="— Ninguna parcela seleccionada —")

    def _on_apply_thresholds(self, min_str: str, max_str: str) -> None:
        ok, error = self._parcela_ctrl.apply_thresholds(
            self._selected_parcela_id, min_str, max_str
        )
        if not ok:
            from ui.error_handler import ErrorCode, ErrorHandler
            if "Umbrales inválidos" in error or "números" in error:
                ErrorHandler.show(ErrorCode.ERR_THRESHOLDS, self._root)
            else:
                ErrorHandler.show(ErrorCode.ERR_DB_WRITE, self._root)

    def _on_mode_change(self, value: str) -> None:
        self._parcela_ctrl.change_mode(self._selected_parcela_id, value)

    # ------------------------------------------------------------------
    # Callbacks de UI → Controller (Arduino) — ACTUALIZADOS
    # ------------------------------------------------------------------
    def _on_assign_board(self, board_id: str) -> None:
        parcelas = self._parcela_ctrl.list_parcelas()
        dialog_data = [{"id": p.get_id(), "name": p.get_name()} for p in parcelas]
        AssignArduinoDialog(
            self._root,
            board_id,
            dialog_data,
            on_confirm=lambda bid, pid: self._board_ctrl.connect_to_parcela(bid, pid)
        )

    def _on_unassign_board(self, board_id: str) -> None:
        self._board_ctrl.disconnect(board_id)

    def _on_read_now(self, board_id: str) -> None:
        """NUEVO: Solicitar lectura inmediata."""
        self._board_ctrl.read_now(board_id)

    def _on_scan_bluetooth(self) -> None:
        """NUEVO: Escanear dispositivos Bluetooth."""
        # TODO: Integrar con device_scanner para BT
        logger.info("Escanear Bluetooth — no implementado")

    def _on_scan_wifi(self) -> None:
        """NUEVO: Escanear dispositivos WiFi (UNO R4)."""
        # TODO: Detectar placas R4 en red local (mDNS, IP fija, etc.)
        logger.info("Escanear WiFi — no implementado")

    def _on_firmware_update(self, board_id: str) -> None:
        info = self._board_ctrl.get_board_info(board_id)
        if not info:
            return
        FirmwareDialog(
            self._root,
            board_id=info["board_id"],
            port=info.get("port", ""),
            current_version=info.get("current_version", "Desconocida"),
        )

    # ------------------------------------------------------------------
    # Exportar
    # ------------------------------------------------------------------
    def _on_export(self) -> None:
        parcelas = self._parcela_ctrl.list_parcelas()
        dialog_data = [{"id": p.get_id(), "name": p.get_name()} for p in parcelas]
        from ui.error_handler import ErrorHandler
        ExportDialog(self._root, dialog_data, self._export_ctrl, ErrorHandler())

    # ------------------------------------------------------------------
    # Callbacks de Controller → UI
    # ------------------------------------------------------------------
    def _refresh_parcela_list(self) -> None:
        parcelas = self._parcela_ctrl.list_parcelas()
        self.main_panel.set_parcelas(parcelas)

    def _on_event_logged(self, text: str, tipo: str) -> None:
        self._root.after(0, lambda: self.main_panel.add_event(text, tipo))

    def _on_board_updated(self, board) -> None:
        self._root.after(0, lambda: self.arduino_panel.update_board(board))

    # ------------------------------------------------------------------
    # Observer MQTT (para placas WiFi)
    # ------------------------------------------------------------------
    def on_event(self, topic: str, data: dict) -> None:
        self._root.after(0, self._update_ui, topic, data)

    def _update_ui(self, topic: str, data: dict) -> None:
        try:
            parcela_id = topic.split("/")[1]
        except IndexError:
            return

        parcela = self._finca.get_parcela(parcela_id)
        if parcela is None:
            return

        if topic.endswith("/sensores"):
            # Placa WiFi envió lectura por MQTT
            self._on_sensor_reading(parcela_id, data)

    # ------------------------------------------------------------------
    # Cierre limpio
    # ------------------------------------------------------------------
    def cleanup(self) -> None:
        self._event_ctrl.cleanup()
        self._board_ctrl.cleanup()


# --------------------------------------------------------------------------
# Diálogo de entrada genérico
# --------------------------------------------------------------------------
class _InputDialog(ctk.CTkToplevel):
    def __init__(self, parent, title: str, fields: list[str]):
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)

        self.result = None
        self._entries = []

        for i, label in enumerate(fields):
            ctk.CTkLabel(self, text=label, font=FONT_NORMAL).grid(
                row=i, column=0, padx=14, pady=6, sticky="e")
            entry = ctk.CTkEntry(self, width=200, font=FONT_NORMAL)
            entry.grid(row=i, column=1, padx=14, pady=6)
            self._entries.append(entry)

        ctk.CTkButton(
            self, text="Aceptar",
            font=FONT_NORMAL,
            command=self._accept,
        ).grid(row=len(fields), column=0, columnspan=2, pady=12)

        self._entries[0].focus()

        self.update()
        self.after(10, lambda: self._set_grab())
        self.wait_window()

    def _set_grab(self) -> None:
        try:
            self.grab_set()
        except tk.TclError:
            pass

    def _accept(self) -> None:
        self.result = [e.get() for e in self._entries]
        self.destroy()
