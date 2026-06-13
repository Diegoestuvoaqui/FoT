import logging
from tkinter import messagebox

import customtkinter as ctk

from connection.mqtt_client import MQTTEventBus
from data.database import Database
from domain.components import Finca, Parcela
from domain.memento import ConfigManager
from ui.theme import FSM_COLORS, FONT_TITLE, FONT_NORMAL, FONT_SMALL, FONT_MONO

logger = logging.getLogger(__name__)


class MainWindow:
    """
    Vista principal — Observer concreto.
    Recibe eventos MQTT y actualiza la UI de forma segura vía root.after().
    """

    def __init__(self,
                 root: ctk.CTk,
                 finca: Finca,
                 mqtt_bus: MQTTEventBus,
                 db: Database,
                 config_manager: ConfigManager):
        self._root = root
        self._finca = finca
        self._mqtt_bus = mqtt_bus
        self._db = db
        self._config_manager = config_manager

        self._selected_parcela_id: str | None = None
        self._parcela_row_frames: dict[str, ctk.CTkFrame] = {}

        self._root.title("FoT — Estación Base")
        self._root.minsize(960, 640)

        self._build_layout()
        self._populate_list()
        self._load_event_log()

    # --------------------------------------------------------------------------
    # Construcción del layout
    # --------------------------------------------------------------------------
    def _build_layout(self) -> None:
        self._root.grid_columnconfigure(0, weight=1, minsize=240)
        self._root.grid_columnconfigure(1, weight=3)
        self._root.grid_rowconfigure(0, weight=3)
        self._root.grid_rowconfigure(1, weight=1, minsize=150)

        self._build_left_panel()
        self._build_center_panel()
        self._build_bottom_panel()

    # ---- Panel izquierdo ----
    def _build_left_panel(self) -> None:
        frame = ctk.CTkFrame(self._root)
        frame.grid(row=0, column=0, sticky="nsew", padx=(8, 4), pady=8)
        frame.grid_rowconfigure(1, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(frame, text="Parcelas",
                     font=FONT_TITLE).grid(
            row=0, column=0, pady=(10, 4), padx=10, sticky="w")

        # Lista scrollable de parcelas
        self._list_frame = ctk.CTkScrollableFrame(frame, label_text="")
        self._list_frame.grid(row=1, column=0, sticky="nsew", padx=6, pady=4)
        self._list_frame.grid_columnconfigure(0, weight=1)

        # Botones
        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.grid(row=2, column=0, pady=6, padx=6, sticky="ew")
        btn_frame.grid_columnconfigure((0, 1, 2), weight=1)

        ctk.CTkButton(btn_frame, text="+ Añadir",
                      font=FONT_SMALL,
                      command=self._add_parcela).grid(
            row=0, column=0, padx=2, sticky="ew")

        ctk.CTkButton(btn_frame, text="Eliminar",
                      font=FONT_SMALL,
                      fg_color="#EF4444", hover_color="#B91C1C",
                      command=self._delete_parcela).grid(
            row=0, column=1, padx=2, sticky="ew")

        ctk.CTkButton(btn_frame, text="Snapshot",
                      font=FONT_SMALL,
                      fg_color="#6B7280", hover_color="#4B5563",
                      command=self._save_snapshot_manual).grid(
            row=0, column=2, padx=2, sticky="ew")

    # ---- Panel central ----
    def _build_center_panel(self) -> None:
        frame = ctk.CTkFrame(self._root)
        frame.grid(row=0, column=1, sticky="nsew", padx=(4, 8), pady=8)
        frame.grid_columnconfigure(1, weight=1)

        row = 0

        # Título de parcela seleccionada
        self._lbl_parcela_title = ctk.CTkLabel(
            frame, text="— Ninguna parcela seleccionada —",
            font=FONT_TITLE)
        self._lbl_parcela_title.grid(
            row=row, column=0, columnspan=2,
            padx=12, pady=(12, 4), sticky="w")
        row += 1

        # Indicador de estado FSM
        ctk.CTkLabel(frame, text="Estado:",
                     font=FONT_NORMAL).grid(
            row=row, column=0, padx=12, pady=4, sticky="w")

        self._lbl_fsm = ctk.CTkLabel(
            frame, text="—", width=130,
            font=("Roboto", 12, "bold"),
            corner_radius=6,
            fg_color="#6B7280",
            text_color="white")
        self._lbl_fsm.grid(row=row, column=1, padx=12, pady=4, sticky="w")
        row += 1

        # Lecturas de sensores
        sensor_data = [
            ("Humedad suelo (%):", "_lbl_hum_suelo"),
            ("Humedad aire (%):", "_lbl_hum_aire"),
            ("Temperatura (°C):", "_lbl_temp"),
        ]
        for label_text, attr in sensor_data:
            ctk.CTkLabel(frame, text=label_text,
                         font=FONT_NORMAL).grid(
                row=row, column=0, padx=12, pady=3, sticky="w")
            lbl = ctk.CTkLabel(frame, text="—", font=FONT_NORMAL)
            lbl.grid(row=row, column=1, padx=12, pady=3, sticky="w")
            setattr(self, attr, lbl)
            row += 1

        # Separador
        ctk.CTkFrame(frame, height=2, fg_color="#3F3F3F").grid(
            row=row, column=0, columnspan=2,
            sticky="ew", padx=12, pady=8)
        row += 1

        # Umbrales
        ctk.CTkLabel(frame, text="Umbral mín (%):",
                     font=FONT_NORMAL).grid(
            row=row, column=0, padx=12, pady=3, sticky="w")
        self._entry_min = ctk.CTkEntry(frame, width=80, font=FONT_NORMAL)
        self._entry_min.grid(row=row, column=1, padx=12, pady=3, sticky="w")
        row += 1

        ctk.CTkLabel(frame, text="Umbral máx (%):",
                     font=FONT_NORMAL).grid(
            row=row, column=0, padx=12, pady=3, sticky="w")
        self._entry_max = ctk.CTkEntry(frame, width=80, font=FONT_NORMAL)
        self._entry_max.grid(row=row, column=1, padx=12, pady=3, sticky="w")
        row += 1

        ctk.CTkButton(frame, text="Aplicar umbrales",
                      font=FONT_NORMAL,
                      command=self._apply_thresholds).grid(
            row=row, column=0, columnspan=2, pady=6)
        row += 1

        # Separador
        ctk.CTkFrame(frame, height=2, fg_color="#3F3F3F").grid(
            row=row, column=0, columnspan=2,
            sticky="ew", padx=12, pady=8)
        row += 1

        # Selector de modo
        ctk.CTkLabel(frame, text="Modo:",
                     font=FONT_NORMAL).grid(
            row=row, column=0, padx=12, pady=3, sticky="w")
        self._option_modo = ctk.CTkOptionMenu(
            frame,
            values=["manual", "auto"],
            font=FONT_NORMAL,
            command=self._on_mode_change)
        self._option_modo.set("manual")
        self._option_modo.grid(row=row, column=1, padx=12, pady=3, sticky="w")
        row += 1

        # Separador
        ctk.CTkFrame(frame, height=2, fg_color="#3F3F3F").grid(
            row=row, column=0, columnspan=2,
            sticky="ew", padx=12, pady=8)
        row += 1

        # Botones de control manual
        ctrl_frame = ctk.CTkFrame(frame, fg_color="transparent")
        ctrl_frame.grid(row=row, column=0, columnspan=2, pady=4)

        self._btn_irrigate = ctk.CTkButton(
            ctrl_frame, text="▶ Activar riego",
            font=FONT_NORMAL,
            fg_color="#3B82F6", hover_color="#1D4ED8",
            state="disabled",
            command=self._cmd_irrigate)
        self._btn_irrigate.pack(side="left", padx=8)

        self._btn_stop = ctk.CTkButton(
            ctrl_frame, text="■ Detener riego",
            font=FONT_NORMAL,
            fg_color="#EF4444", hover_color="#B91C1C",
            state="disabled",
            command=self._cmd_stop)
        self._btn_stop.pack(side="left", padx=8)

    # ---- Panel inferior — log ----
    def _build_bottom_panel(self) -> None:
        frame = ctk.CTkFrame(self._root)
        frame.grid(row=1, column=0, columnspan=2,
                   sticky="nsew", padx=8, pady=(0, 8))
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(frame, text="Registro de eventos",
                     font=FONT_NORMAL).grid(
            row=0, column=0, padx=10, pady=(6, 0), sticky="w")

        self._log_text = ctk.CTkTextbox(
            frame, font=FONT_MONO,
            state="disabled", wrap="word")
        self._log_text.grid(row=1, column=0, sticky="nsew", padx=6, pady=6)

    # --------------------------------------------------------------------------
    # Lista de parcelas
    # --------------------------------------------------------------------------
    def _populate_list(self) -> None:
        # Limpiar filas anteriores
        for widget in self._list_frame.winfo_children():
            widget.destroy()
        self._parcela_row_frames.clear()

        for i, parcela in enumerate(self._finca.get_children()):
            self._add_parcela_row(parcela, i)

    def _add_parcela_row(self, parcela: Parcela, index: int) -> None:
        pid = parcela.get_id()
        fsm = getattr(parcela, "fsm_state", "Idle")
        color = FSM_COLORS.get(fsm, "#6B7280")

        row_frame = ctk.CTkFrame(
            self._list_frame,
            corner_radius=6,
            border_width=2,
            border_color="#3F3F3F")
        row_frame.grid(row=index, column=0, sticky="ew", pady=3, padx=2)
        row_frame.grid_columnconfigure(0, weight=1)

        # Nombre
        name_lbl = ctk.CTkLabel(
            row_frame,
            text=parcela.get_name(),
            font=FONT_NORMAL,
            anchor="w")
        name_lbl.grid(row=0, column=0, padx=10, pady=(6, 2), sticky="w")

        # Estado + ID
        info_lbl = ctk.CTkLabel(
            row_frame,
            text=f"{fsm}  •  {pid}",
            font=FONT_SMALL,
            text_color=color,
            anchor="w")
        info_lbl.grid(row=1, column=0, padx=10, pady=(0, 6), sticky="w")

        # Clic en la fila
        for widget in (row_frame, name_lbl, info_lbl):
            widget.bind("<Button-1>",
                        lambda e, p=pid: self._on_parcela_click(p))

        self._parcela_row_frames[pid] = row_frame

    def _on_parcela_click(self, parcela_id: str) -> None:
        # Quitar selección visual anterior
        if self._selected_parcela_id in self._parcela_row_frames:
            self._parcela_row_frames[self._selected_parcela_id].configure(
                border_color="#3F3F3F")

        self._selected_parcela_id = parcela_id

        # Marcar fila seleccionada
        if parcela_id in self._parcela_row_frames:
            self._parcela_row_frames[parcela_id].configure(
                border_color="#22C55E")

        parcela = self._finca.get_parcela(parcela_id)
        if parcela:
            self._refresh_center_panel(parcela)

    # --------------------------------------------------------------------------
    # Panel central — refresco
    # --------------------------------------------------------------------------
    def _refresh_center_panel(self, parcela: Parcela) -> None:
        self._lbl_parcela_title.configure(text=parcela.get_name())

        # Umbrales
        self._entry_min.delete(0, "end")
        self._entry_min.insert(0, str(parcela.umbral_min))
        self._entry_max.delete(0, "end")
        self._entry_max.insert(0, str(parcela.umbral_max))

        # Modo
        self._option_modo.set(parcela.modo)

        # Estado FSM
        fsm = getattr(parcela, "fsm_state", "Idle")
        self._update_fsm_indicator(fsm)

        # Lecturas
        reading = parcela.get_latest_reading()
        self._lbl_hum_suelo.configure(text=_fmt(reading.get("hum_suelo")))
        self._lbl_hum_aire.configure(text=_fmt(reading.get("hum_aire")))
        self._lbl_temp.configure(text=_fmt(reading.get("temp")))

        # Botones manuales
        self._update_control_buttons(fsm)

    def _update_fsm_indicator(self, fsm_state: str) -> None:
        color = FSM_COLORS.get(fsm_state, "#6B7280")
        self._lbl_fsm.configure(text=fsm_state, fg_color=color)

    def _update_control_buttons(self, fsm_state: str) -> None:
        state = "normal" if fsm_state == "Idle" else "disabled"
        self._btn_irrigate.configure(state=state)
        self._btn_stop.configure(state=state)

    # --------------------------------------------------------------------------
    # Observer — entrada desde hilo MQTT
    # --------------------------------------------------------------------------
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
            reading = parcela.get_latest_reading()
            if parcela_id == self._selected_parcela_id:
                self._lbl_hum_suelo.configure(
                    text=_fmt(reading.get("hum_suelo")))
                self._lbl_hum_aire.configure(
                    text=_fmt(reading.get("hum_aire")))
                self._lbl_temp.configure(
                    text=_fmt(reading.get("temp")))

        elif topic.endswith("/estado"):
            fsm_state = data.get("state", "Idle")
            # Actualizar fila en la lista
            self._populate_list()
            if parcela_id == self._selected_parcela_id:
                self._update_fsm_indicator(fsm_state)
                self._update_control_buttons(fsm_state)
            if fsm_state == "Fault":
                self._append_log(f"[FALLO] {parcela_id}: {data}")

    # --------------------------------------------------------------------------
    # Acciones
    # --------------------------------------------------------------------------
    def _apply_thresholds(self) -> None:
        if not self._selected_parcela_id:
            return
        parcela = self._finca.get_parcela(self._selected_parcela_id)
        if not parcela:
            return
        try:
            min_val = float(self._entry_min.get())
            max_val = float(self._entry_max.get())
        except ValueError:
            _show_error("Los umbrales deben ser números entre 0 y 100.")
            return
        if not (0 <= min_val < max_val <= 100):
            _show_error("El umbral mínimo debe ser menor que el máximo\n"
                        "y ambos entre 0 y 100.")
            return

        self._config_manager.save_snapshot(
            self._finca,
            f"Antes de cambiar umbrales en {self._selected_parcela_id}",
            self._db)

        parcela.umbral_min = min_val
        parcela.umbral_max = max_val

        self._db.save_parcela({
            "id": parcela.get_id(),
            "name": parcela.get_name(),
            "umbral_min": min_val,
            "umbral_max": max_val,
            "modo": parcela.modo,
        })

        self._mqtt_bus.publish(
            f"fot/{self._selected_parcela_id}/control",
            {"cmd": "set_thresholds", "min": min_val, "max": max_val})

        self._append_log(
            f"Umbrales actualizados en {self._selected_parcela_id}: "
            f"mín={min_val}% máx={max_val}%")

    def _on_mode_change(self, value: str) -> None:
        if not self._selected_parcela_id:
            return
        cmd = "set_mode_auto" if value == "auto" else "set_mode_manual"
        self._mqtt_bus.publish(
            f"fot/{self._selected_parcela_id}/control",
            {"cmd": cmd})
        self._append_log(
            f"Modo cambiado a '{value}' en {self._selected_parcela_id}")

    def _cmd_irrigate(self) -> None:
        if self._selected_parcela_id:
            self._mqtt_bus.publish(
                f"fot/{self._selected_parcela_id}/control",
                {"cmd": "irrigate"})
            self._append_log(
                f"Riego activado en {self._selected_parcela_id}")

    def _cmd_stop(self) -> None:
        if self._selected_parcela_id:
            self._mqtt_bus.publish(
                f"fot/{self._selected_parcela_id}/control",
                {"cmd": "stop"})
            self._append_log(
                f"Riego detenido en {self._selected_parcela_id}")

    def _add_parcela(self) -> None:
        dialog = _InputDialog(self._root, "Nueva parcela",
                              ["ID:", "Nombre:"])
        if not dialog.result:
            return
        pid = dialog.result[0].strip()
        name = dialog.result[1].strip()

        if not pid or not name:
            _show_error("El ID y el nombre son obligatorios.")
            return
        if self._finca.get_parcela(pid):
            _show_error(f"Ya existe una parcela con el ID '{pid}'.")
            return

        self._config_manager.save_snapshot(
            self._finca, f"Antes de añadir parcela {pid}", self._db)

        parcela = Parcela(pid, name)
        self._finca.add_parcela(parcela)
        self._db.save_parcela({
            "id": pid, "name": name,
            "umbral_min": 30.0, "umbral_max": 70.0, "modo": "manual"})

        self._populate_list()
        self._append_log(f"Parcela '{name}' ({pid}) añadida.")

    def _delete_parcela(self) -> None:
        if not self._selected_parcela_id:
            _show_error("Selecciona una parcela antes de eliminar.")
            return

        confirm = messagebox.askyesno(
            "Confirmar eliminación",
            f"¿Eliminar la parcela '{self._selected_parcela_id}'?\n"
            "Esta acción no se puede deshacer.")
        if not confirm:
            return

        self._config_manager.save_snapshot(
            self._finca,
            f"Antes de eliminar parcela {self._selected_parcela_id}",
            self._db)

        self._db.delete_parcela(self._selected_parcela_id)
        self._finca.remove_parcela(self._selected_parcela_id)
        self._append_log(
            f"Parcela '{self._selected_parcela_id}' eliminada.")
        self._selected_parcela_id = None
        self._lbl_parcela_title.configure(
            text="— Ninguna parcela seleccionada —")
        self._populate_list()

    def _save_snapshot_manual(self) -> None:
        self._config_manager.save_snapshot(
            self._finca, "Instantánea manual", self._db)
        self._append_log("Instantánea de configuración guardada.")

    # --------------------------------------------------------------------------
    # Log de eventos
    # --------------------------------------------------------------------------
    def _load_event_log(self) -> None:
        for parcela in self._finca.get_children():
            for e in reversed(self._db.get_events(parcela.get_id(), limit=20)):
                self._append_log(
                    f"[{e.get('ts', '')}] {e.get('tipo', '')} — "
                    f"{e.get('descripcion', '')}")

    def _append_log(self, text: str) -> None:
        self._log_text.configure(state="normal")
        self._log_text.insert("end", text + "\n")
        self._log_text.see("end")
        self._log_text.configure(state="disabled")


# --------------------------------------------------------------------------
# Diálogo de entrada
# --------------------------------------------------------------------------
class _InputDialog(ctk.CTkToplevel):

    def __init__(self, parent, title: str, fields: list[str]):
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        self.grab_set()
        self.result = None

        self._entries = []
        for i, label in enumerate(fields):
            ctk.CTkLabel(self, text=label,
                         font=FONT_NORMAL).grid(
                row=i, column=0, padx=14, pady=6, sticky="e")
            entry = ctk.CTkEntry(self, width=200, font=FONT_NORMAL)
            entry.grid(row=i, column=1, padx=14, pady=6)
            self._entries.append(entry)

        ctk.CTkButton(self, text="Aceptar",
                      font=FONT_NORMAL,
                      command=self._accept).grid(
            row=len(fields), column=0, columnspan=2, pady=12)

        self._entries[0].focus()
        self.wait_window()

    def _accept(self) -> None:
        self.result = [e.get() for e in self._entries]
        self.destroy()


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def _fmt(value) -> str:
    if value is None:
        return "—"
    try:
        return f"{float(value):.1f}"
    except (TypeError, ValueError):
        return "—"


def _show_error(msg: str) -> None:
    messagebox.showerror("Error", msg)
