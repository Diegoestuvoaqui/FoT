"""
ui/panels/parcela_detail_panel.py
Ventana independiente con el detalle completo de una parcela:
info general, variables en tiempo real, gráfico histórico,
controles avanzados y registro de eventos.

Uso (desde MainWindow o MainPanel):
    ParcelaDetailPanel(
        parent,
        parcela=parcela,          # objeto Parcela
        db=Database(),
        mqtt_bus=MQTTEventBus(),
        on_command=lambda cmd, parcela_id: ...
    )
"""
from __future__ import annotations

import csv
import json
from datetime import datetime
from tkinter import filedialog

import customtkinter as ctk

from ui.theme import FSM_COLORS, FONT_TITLE, FONT_NORMAL, FONT_SMALL, FONT_MONO, COLORS
from ui.widgets.sensor_chart import SensorChart


class ParcelaDetailPanel(ctk.CTkToplevel):
    def __init__(self, parent, parcela, db, mqtt_bus, on_command=None):
        super().__init__(parent)
        self.title(f"Parcela {parcela.get_name()} ({parcela.get_id()})")
        self.geometry("960x720")
        self.minsize(800, 600)
        self.resizable(True, True)

        self._parcela = parcela
        self._db = db
        self._mqtt_bus = mqtt_bus
        self._on_command = on_command  # callback para comandos manuales

        self.grab_set()  # hace que la ventana sea modal respecto a la principal

        # Contenido
        self._build()
        self._refresh()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # ---------- Cabecera: información general ----------
        header = ctk.CTkFrame(self, corner_radius=8, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=12, pady=12)
        header.grid_columnconfigure(1, weight=1)

        self._lbl_title = ctk.CTkLabel(header, text="", font=FONT_TITLE, anchor="w")
        self._lbl_title.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))

        # Rejilla de datos: ID, Placa, Modo, Estado, Uptime
        info_data = [
            ("ID:", "id"),
            ("Placa asignada:", "placa"),
            ("Modo:", "modo"),
            ("Estado:", "estado"),
            ("Tiempo encendida:", "uptime"),
        ]
        self._info_labels = {}
        for i, (label, key) in enumerate(info_data):
            ctk.CTkLabel(header, text=label, font=FONT_NORMAL).grid(
                row=1 + i // 3, column=(i % 3) * 2, padx=(0, 4), pady=2, sticky="e")
            lbl = ctk.CTkLabel(header, text="—", font=FONT_NORMAL, anchor="w")
            lbl.grid(row=1 + i // 3, column=(i % 3) * 2 + 1, padx=4, pady=2, sticky="w")
            self._info_labels[key] = lbl

        # ---------- Pestañas: Variables + Controles y Eventos ----------
        self._tabview = ctk.CTkTabview(self, corner_radius=8)
        self._tabview.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self._tabview.add("Variables y controles")
        self._tabview.add("Historial de eventos")
        self._tabview.tab("Variables y controles").grid_columnconfigure(0, weight=1)
        self._tabview.tab("Variables y controles").grid_rowconfigure(1, weight=1)
        self._tabview.tab("Historial de eventos").grid_columnconfigure(0, weight=1)
        self._tabview.tab("Historial de eventos").grid_rowconfigure(0, weight=1)

        self._build_sensors_tab()
        self._build_events_tab()

    def _build_sensors_tab(self):
        tab = self._tabview.tab("Variables y controles")
        # Fila 0: tarjetas de variables
        cards = ctk.CTkFrame(tab, fg_color="transparent")
        cards.grid(row=0, column=0, sticky="ew", padx=8, pady=8)
        cards.grid_columnconfigure((0, 1, 2), weight=1)

        sensor_info = [
            ("Humedad suelo", "hum_suelo", "%", True),  # con barra
            ("Humedad aire", "hum_aire", "%", False),
            ("Temperatura", "temp", "°C", False),
        ]
        self._sensor_widgets = {}
        for col, (name, key, unit, show_bar) in enumerate(sensor_info):
            card = ctk.CTkFrame(cards, corner_radius=8, border_width=1,
                                border_color=COLORS["border"])
            card.grid(row=0, column=col, padx=6, pady=6, sticky="nsew")
            card.grid_columnconfigure(0, weight=1)

            ctk.CTkLabel(card, text=name, font=FONT_NORMAL).grid(row=0, column=0, pady=(8, 0), padx=8, sticky="w")
            lbl_val = ctk.CTkLabel(card, text="—", font=("Roboto", 24, "bold"))
            lbl_val.grid(row=1, column=0, padx=8, pady=(4, 0), sticky="w")
            lbl_unit = ctk.CTkLabel(card, text=unit, font=FONT_SMALL, text_color="gray")
            lbl_unit.grid(row=2, column=0, padx=8, pady=(0, 4), sticky="w")

            if show_bar:
                bar = ctk.CTkProgressBar(card, height=12)
                bar.grid(row=3, column=0, padx=8, pady=(0, 8), sticky="ew")
                bar.set(0)
                self._sensor_widgets[key] = (lbl_val, bar)
            else:
                self._sensor_widgets[key] = (lbl_val, None)

        # Fila 1: gráfico histórico
        chart_frame = ctk.CTkFrame(tab, corner_radius=8, border_width=1,
                                   border_color=COLORS["border"])
        chart_frame.grid(row=1, column=0, sticky="nsew", padx=8, pady=8)
        chart_frame.grid_columnconfigure(0, weight=1)
        chart_frame.grid_rowconfigure(0, weight=1)
        self._chart = SensorChart(chart_frame)
        self._chart.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)

        # Fila 2: controles (modo, umbrales, riego, fallo)
        ctrl = ctk.CTkFrame(tab, fg_color="transparent")
        ctrl.grid(row=2, column=0, sticky="ew", padx=8, pady=8)
        ctrl.grid_columnconfigure(1, weight=1)

        row = 0
        ctk.CTkLabel(ctrl, text="Modo:", font=FONT_NORMAL).grid(row=row, column=0, padx=4, pady=4, sticky="e")
        self._opt_mode = ctk.CTkSegmentedButton(
            ctrl, values=["Reposo", "Automático"], font=FONT_NORMAL,
            command=self._on_mode_change
        )
        self._opt_mode.grid(row=row, column=1, padx=4, pady=4, sticky="w")
        row += 1

        ctk.CTkLabel(ctrl, text="Umbral mín (%):", font=FONT_NORMAL).grid(row=row, column=0, padx=4, pady=4, sticky="e")
        self._entry_min = ctk.CTkEntry(ctrl, width=80, font=FONT_NORMAL)
        self._entry_min.grid(row=row, column=1, padx=4, pady=4, sticky="w")
        row += 1

        ctk.CTkLabel(ctrl, text="Umbral máx (%):", font=FONT_NORMAL).grid(row=row, column=0, padx=4, pady=4, sticky="e")
        self._entry_max = ctk.CTkEntry(ctrl, width=80, font=FONT_NORMAL)
        self._entry_max.grid(row=row, column=1, padx=4, pady=4, sticky="w")
        row += 1

        btn_frame = ctk.CTkFrame(ctrl, fg_color="transparent")
        btn_frame.grid(row=row, column=1, sticky="w", pady=4)
        ctk.CTkButton(btn_frame, text="Aplicar umbrales", font=FONT_SMALL,
                      command=self._apply_thresholds).pack(side="left", padx=2)

        self._btn_irrigate = ctk.CTkButton(  # ← guardar referencia
            btn_frame, text="Activar riego", font=FONT_SMALL,
            fg_color="#3B82F6", hover_color="#1D4ED8",
            command=self._cmd_irrigate)
        self._btn_irrigate.pack(side="left", padx=2)

        self._btn_stop = ctk.CTkButton(  # ← guardar referencia
            btn_frame, text="Detener riego", font=FONT_SMALL,
            fg_color="#EF4444", hover_color="#B91C1C",
            command=self._cmd_stop)
        self._btn_stop.pack(side="left", padx=2)
        row += 1

        # Botón reiniciar fallo (visible solo en estado Fallo)
        self._btn_reset_fault = ctk.CTkButton(
            ctrl, text="Reiniciar fallo", font=FONT_SMALL,
            fg_color=COLORS["warning"], hover_color="#D97706",
            command=self._cmd_reset_fault
        )
        self._btn_reset_fault.grid(row=row, column=1, pady=4, sticky="w")
        self._btn_reset_fault.grid_remove()  # oculto por defecto
        row += 1

        # Habilitar/deshabilitar sensores
        sensor_ctrl = ctk.CTkFrame(ctrl, fg_color="transparent")
        sensor_ctrl.grid(row=row, column=1, sticky="w", pady=4)
        self._chk_hum_suelo = ctk.CTkCheckBox(sensor_ctrl, text="Sensor suelo",
                                              font=FONT_SMALL, command=self._toggle_sensor)
        self._chk_hum_suelo.pack(side="left", padx=4)
        self._chk_temp = ctk.CTkCheckBox(sensor_ctrl, text="DHT22",
                                         font=FONT_SMALL, command=self._toggle_sensor)
        self._chk_temp.pack(side="left", padx=4)

    def _build_events_tab(self):
        tab = self._tabview.tab("Historial de eventos")
        # Filtros
        filt_frame = ctk.CTkFrame(tab, fg_color="transparent")
        filt_frame.grid(row=0, column=0, sticky="ew", padx=8, pady=4)
        self._event_filter = ctk.StringVar(value="todos")
        for i, (text, val) in enumerate([
            ("Todo", "todos"), ("Riegos", "riego"),
            ("Cambios modo", "modo"), ("Errores", "error")
        ]):
            ctk.CTkRadioButton(filt_frame, text=text, variable=self._event_filter,
                               value=val, font=FONT_SMALL,
                               command=self._apply_event_filter).grid(row=0, column=i, padx=4)

        # Botón exportar
        ctk.CTkButton(filt_frame, text="Exportar", font=FONT_SMALL,
                      command=self._export_events).grid(row=0, column=4, padx=8, sticky="e")
        filt_frame.grid_columnconfigure(4, weight=1)

        # Cuadro de texto de eventos
        self._event_text = ctk.CTkTextbox(tab, font=FONT_MONO, wrap="word", state="disabled")
        self._event_text.grid(row=1, column=0, sticky="nsew", padx=8, pady=8)
        self._events_raw = []  # lista de dicts: timestamp, tipo, descripcion

    def _refresh(self):
        """Carga todos los datos actuales de la parcela."""
        p = self._parcela
        self._lbl_title.configure(text=f"{p.get_name()} ({p.get_id()})")
        self._info_labels["id"].configure(text=p.get_id())
        placa_id = getattr(p, "placa_id", None) or "—"
        conn = getattr(p, "connection", "") or "—"
        self._info_labels["placa"].configure(text=f"{placa_id} ({conn})" if placa_id != "—" else "—")
        modo = "Automático" if p.modo == "auto" else "Reposo"
        self._info_labels["modo"].configure(text=modo)
        self._opt_mode.set(modo)

        fsm = getattr(p, "fsm_state", "Idle")
        color = FSM_COLORS.get(fsm, "#6B7280")
        self._info_labels["estado"].configure(text=fsm, text_color=color)

        # Uptime (simplificado; se puede obtener de la placa si hay dato)
        self._info_labels["uptime"].configure(text="—")  # actualizaremos si llega por evento

        # Sensores
        reading = p.get_latest_reading()
        for key, (lbl, bar) in self._sensor_widgets.items():
            val = reading.get(key)
            if val is not None:
                lbl.configure(text=f"{float(val):.1f}")
                if bar and key == "hum_suelo":
                    bar.set(float(val) / 100)
            else:
                lbl.configure(text="—")

        # Umbrales
        self._entry_min.delete(0, "end")
        self._entry_min.insert(0, str(p.umbral_min))
        self._entry_max.delete(0, "end")
        self._entry_max.insert(0, str(p.umbral_max))

        # Botones según estado FSM
        if fsm == "Idle":
            state = "normal"
        else:
            state = "disabled"
        # (reemplazar con atributos de los botones si los guardamos; pero podemos habilitar/deshabilitar así)
        for btn in self._btn_irrigate, self._btn_stop:
            btn.configure(state=state)

        # Botón reset fallo
        if fsm == "Fault":
            self._btn_reset_fault.grid()
        else:
            self._btn_reset_fault.grid_remove()

        # Gráfico: cargar datos históricos (últimos 7 días)
        self._load_chart_data()

        # Eventos
        self._load_events()

    def _load_chart_data(self):
        """Consulta la BD y prepara los datos para el gráfico."""
        try:
            rows = self._db.get_readings(self._parcela.get_id(), limit=200, order="DESC")
        except AttributeError:
            rows = []
        if not rows:
            self._chart.update_data([], [], [], [], self._parcela.umbral_min, self._parcela.umbral_max)
            return

        timestamps = []
        hum_s = []
        hum_a = []
        temp = []
        for r in reversed(rows):
            timestamps.append(r.get("ts") if isinstance(r.get("ts"), datetime) else datetime.fromisoformat(r["ts"]))
            hum_s.append(r.get("hum_suelo"))
            hum_a.append(r.get("hum_aire"))
            temp.append(r.get("temp"))
        self._chart.update_data(timestamps, hum_s, hum_a, temp,
                                self._parcela.umbral_min, self._parcela.umbral_max)

    def _load_events(self):
        self._events_raw = self._db.get_events(self._parcela.get_id(), limit=100) or []
        self._apply_event_filter()

    def _apply_event_filter(self, *args):
        filtro = self._event_filter.get()
        self._event_text.configure(state="normal")
        self._event_text.delete("1.0", "end")
        for ev in self._events_raw:
            ts = ev.get("ts", "")
            tipo = ev.get("tipo", "").lower()
            desc = ev.get("descripcion", "")
            if filtro == "todos" or (filtro == "riego" and "riego" in tipo) or \
                    (filtro == "modo" and "modo" in tipo) or (
                    filtro == "error" and ("error" in tipo or "fallo" in tipo)):
                self._event_text.insert("end", f"[{ts}] {tipo}: {desc}\n")
        self._event_text.see("end")
        self._event_text.configure(state="disabled")

    # ---------- Acciones ----------
    def _on_mode_change(self, value):
        modo = "auto" if value == "Automático" else "manual"
        self._send_command({"cmd": "set_mode_auto"} if modo == "auto" else {"cmd": "set_mode_manual"})

    def _apply_thresholds(self):
        try:
            min_v = float(self._entry_min.get())
            max_v = float(self._entry_max.get())
        except ValueError:
            return
        self._parcela.umbral_min = min_v
        self._parcela.umbral_max = max_v
        self._db.save_parcela({
            "id": self._parcela.get_id(),
            "name": self._parcela.get_name(),
            "umbral_min": min_v,
            "umbral_max": max_v,
            "modo": self._parcela.modo,
        })
        self._send_command({"cmd": "set_thresholds", "min": min_v, "max": max_v})

    def _cmd_irrigate(self):
        self._send_command({"cmd": "irrigate"})

    def _cmd_stop(self):
        self._send_command({"cmd": "stop"})

    def _cmd_reset_fault(self):
        self._send_command({"cmd": "reset_fault"})

    def _toggle_sensor(self):
        # Enviar comandos para habilitar/deshabilitar sensores según checkboxes
        # (depende del protocolo; aquí solo mostramos la idea)
        pass

    def _send_command(self, cmd_dict):
        if self._on_command:
            self._on_command(cmd_dict, self._parcela.get_id())
        else:
            # fallback: publicar directamente si tenemos mqtt_bus
            if self._mqtt_bus:
                self._mqtt_bus.publish(f"fot/{self._parcela.get_id()}/control", cmd_dict)

    def _export_events(self):
        """Exporta el historial filtrado a CSV o JSON."""
        file_types = [("CSV", "*.csv"), ("JSON", "*.json")]
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=file_types)
        if not path:
            return
        if path.endswith(".json"):
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._events_raw, f, default=str, indent=2)
        else:  # CSV
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["timestamp", "tipo", "descripcion"])
                for ev in self._events_raw:
                    writer.writerow([ev.get("ts"), ev.get("tipo"), ev.get("descripcion")])
