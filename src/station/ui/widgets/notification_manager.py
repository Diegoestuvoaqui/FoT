# ui/widgets/notification_manager.py
"""
Sistema centralizado de notificaciones con sonido.
Soporta: toast notifications, historial persistente, configuración de sonido.

Uso:
    from ui.widgets.notification_manager import NotificationManager

    mgr = NotificationManager(root)
    mgr.notify("Placa conectada", "Board-01 se conectó por USB", tipo="info")
    mgr.notify("Error de sensor", "DHT11 no responde", tipo="error")

    # Configuración
    mgr.set_sound_enabled(True)
    mgr.set_volume(0.7)

    # Al destruir la ventana (logout):
    mgr.reset()  # Limpia toasts activos y referencias al root viejo
"""
from __future__ import annotations

import logging
import os
import platform
import subprocess
import threading
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Callable, Optional

import customtkinter as ctk

from ui.theme import FONT_NORMAL, FONT_SMALL, COLORS

logger = logging.getLogger(__name__)


class NotifType(Enum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


NOTIF_COLORS = {
    NotifType.INFO: ("#3B82F6", "#1E3A5F"),  # azul
    NotifType.SUCCESS: ("#22C55E", "#14532D"),  # verde
    NotifType.WARNING: ("#F59E0B", "#78350F"),  # ámbar
    NotifType.ERROR: ("#EF4444", "#7F1D1D"),  # rojo
}

NOTIF_ICONS = {
    NotifType.INFO: "ℹ️",
    NotifType.SUCCESS: "✅",
    NotifType.WARNING: "⚠️",
    NotifType.ERROR: "❌",
}


@dataclass
class Notification:
    id: int
    title: str
    message: str
    tipo: NotifType
    timestamp: datetime
    read: bool = False


class NotificationManager:
    """
    Gestiona notificaciones toast, historial y sonidos.
    Singleton por aplicación.
    """
    _instance: Optional["NotificationManager"] = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, root: Optional[ctk.CTk] = None):
        if hasattr(self, "_initialized"):
            # Si ya está inicializado pero el root cambió (logout/login), actualizar root
            if root is not None and root != self._root:
                self._cleanup_toasts()
                self._root = root
            return
        self._initialized = True

        self._root = root
        self._notifications: deque[Notification] = deque(maxlen=100)
        self._counter = 0
        self._sound_enabled = True
        self._volume = 0.5
        self._toast_enabled = True
        self._active_toasts: list[ctk.CTkToplevel] = []
        self._observers: list[Callable] = []

        # Intentar cargar configuración guardada
        self._load_settings()

    # ------------------------------------------------------------------
    # Reset / Cleanup
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """
        Limpia todos los toasts activos y referencias al root.
        Llamar al hacer logout antes de destruir la ventana.
        """
        self._cleanup_toasts()
        self._root = None
        logger.info("NotificationManager reseteado")

    def _cleanup_toasts(self) -> None:
        """Destruye todos los toasts activos y limpia la lista."""
        for toast in self._active_toasts:
            try:
                if toast.winfo_exists():
                    toast.destroy()
            except Exception:
                pass
        self._active_toasts.clear()

    def _purge_dead_toasts(self) -> None:
        """Elimina de la lista los toasts que ya fueron destruidos."""
        alive = []
        for toast in self._active_toasts:
            try:
                if toast.winfo_exists():
                    alive.append(toast)
            except Exception:
                pass
        self._active_toasts = alive

    # ------------------------------------------------------------------
    # Configuración
    # ------------------------------------------------------------------

    def set_sound_enabled(self, enabled: bool) -> None:
        self._sound_enabled = enabled
        self._save_settings()

    def is_sound_enabled(self) -> bool:
        return self._sound_enabled

    def set_volume(self, volume: float) -> None:
        self._volume = max(0.0, min(1.0, volume))
        self._save_settings()

    def get_volume(self) -> float:
        return self._volume

    def set_toast_enabled(self, enabled: bool) -> None:
        self._toast_enabled = enabled
        self._save_settings()

    def is_toast_enabled(self) -> bool:
        return self._toast_enabled

    # ------------------------------------------------------------------
    # Notificaciones
    # ------------------------------------------------------------------

    def notify(self, title: str, message: str, tipo: str = "info") -> None:
        """Crear una nueva notificación."""
        try:
            notif_type = NotifType(tipo)
        except ValueError:
            notif_type = NotifType.INFO

        self._counter += 1
        notif = Notification(
            id=self._counter,
            title=title,
            message=message,
            tipo=notif_type,
            timestamp=datetime.now(),
        )
        self._notifications.appendleft(notif)

        # Sonido
        if self._sound_enabled:
            threading.Thread(target=self._play_sound, args=(notif_type,), daemon=True).start()

        # Toast
        if self._toast_enabled and self._root and self._root.winfo_exists():
            self._root.after(0, lambda: self._show_toast(notif))

        # Notificar observers (badge count, etc.)
        self._notify_observers()

        logger.info("Notificación [%s]: %s — %s", tipo, title, message)

    def get_unread_count(self) -> int:
        return sum(1 for n in self._notifications if not n.read)

    def get_all(self) -> list[Notification]:
        return list(self._notifications)

    def mark_all_read(self) -> None:
        for n in self._notifications:
            n.read = True
        self._notify_observers()

    def mark_read(self, notif_id: int) -> None:
        for n in self._notifications:
            if n.id == notif_id:
                n.read = True
                break
        self._notify_observers()

    def clear_all(self) -> None:
        self._notifications.clear()
        self._notify_observers()

    # ------------------------------------------------------------------
    # Observer pattern
    # ------------------------------------------------------------------

    def add_observer(self, callback: Callable[[], None]) -> None:
        if callback not in self._observers:
            self._observers.append(callback)

    def remove_observer(self, callback: Callable[[], None]) -> None:
        if callback in self._observers:
            self._observers.remove(callback)

    def _notify_observers(self) -> None:
        for obs in self._observers:
            try:
                obs()
            except Exception as e:
                logger.error("Error en observer de notificaciones: %s", e)

    # ------------------------------------------------------------------
    # Sonido
    # ------------------------------------------------------------------

    def _play_sound(self, tipo: NotifType) -> None:
        """Reproduce un sonido según el tipo de notificación."""
        system = platform.system()

        # Frecuencias por tipo (Hz, duración_ms)
        sounds = {
            NotifType.INFO: (800, 150),
            NotifType.SUCCESS: (1000, 200),
            NotifType.WARNING: (600, 300),
            NotifType.ERROR: (400, 400),
        }
        freq, duration = sounds.get(tipo, (800, 150))

        try:
            if system == "Windows":
                import winsound
                winsound.Beep(freq, duration)
            elif system == "Linux":
                # Intentar paplay, aplay, o beep
                self._play_linux_sound(freq, duration)
            elif system == "Darwin":  # macOS
                subprocess.run(["afplay", "/System/Library/Sounds/Glass.aiff"],
                               capture_output=True, timeout=2)
        except Exception as e:
            logger.debug("No se pudo reproducir sonido: %s", e)

    def _play_linux_sound(self, freq: int, duration: int) -> None:
        """Intenta varios métodos para reproducir sonido en Linux."""
        # Método 1: beep (requiere permisos PC speaker)
        try:
            with open("/dev/tty10", "w") as console:
                console.write(f"\033[10;{freq}]\033[11;{duration}]\007")
            return
        except Exception:
            pass

        # Método 2: aplay con tono generado
        try:
            # Generar un pequeño WAV en memoria vía sox o similar no es trivial,
            # así que usamos el speaker del sistema si está disponible
            subprocess.run(["beep", "-f", str(freq), "-l", str(duration)],
                           capture_output=True, timeout=2)
            return
        except Exception:
            pass

        # Método 3: canberra-gtk-play (sonidos del sistema)
        try:
            sound_names = {
                NotifType.INFO: "message",
                NotifType.SUCCESS: "complete",
                NotifType.WARNING: "dialog-warning",
                NotifType.ERROR: "dialog-error",
            }
            name = sound_names.get(NotifType.INFO, "message")
            subprocess.run(["canberra-gtk-play", "--id", name],
                           capture_output=True, timeout=2)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Toast notifications
    # ------------------------------------------------------------------

    def _show_toast(self, notif: Notification) -> None:
        """Muestra un toast flotante en la esquina inferior derecha."""
        if not self._root or not self._root.winfo_exists():
            return

        # Limpiar toasts muertos antes de crear uno nuevo
        self._purge_dead_toasts()

        toast = ctk.CTkToplevel(self._root)
        toast.overrideredirect(True)
        toast.attributes("-topmost", True)
        toast.attributes("-alpha", 0.95)

        # Frame principal
        border_color, bg_color = NOTIF_COLORS[notif.tipo]
        frame = ctk.CTkFrame(toast, corner_radius=10, border_width=2,
                             border_color=border_color, fg_color=bg_color)
        frame.pack(padx=2, pady=2, fill="both", expand=True)

        # Icono + título
        header = ctk.CTkFrame(frame, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=(10, 4))

        ctk.CTkLabel(header, text=NOTIF_ICONS[notif.tipo],
                     font=("Roboto", 16)).pack(side="left")
        ctk.CTkLabel(header, text=notif.title, font=("Roboto", 12, "bold"),
                     text_color="white").pack(side="left", padx=(6, 0))

        # Mensaje
        ctk.CTkLabel(frame, text=notif.message, font=FONT_SMALL,
                     text_color=("gray90", "gray80"), wraplength=280,
                     justify="left").pack(padx=12, pady=(0, 10), anchor="w")

        # Posicionar en esquina inferior derecha
        toast.update_idletasks()
        width = 320
        height = toast.winfo_reqheight()
        screen_w = self._root.winfo_screenwidth()
        screen_h = self._root.winfo_screenheight()

        # Apilar toasts (solo contar los que están vivos)
        offset_y = sum(t.winfo_height() + 10 for t in self._active_toasts if t.winfo_exists())
        x = screen_w - width - 20
        y = screen_h - height - 40 - offset_y
        toast.geometry(f"{width}x{height}+{x}+{y}")

        self._active_toasts.append(toast)

        # Auto-cerrar después de 4 segundos
        def _close():
            try:
                if toast.winfo_exists():
                    toast.destroy()
            except Exception:
                pass
            if toast in self._active_toasts:
                self._active_toasts.remove(toast)

        toast.after(4000, _close)

        # Cerrar al hacer clic
        for widget in [frame, toast]:
            widget.bind("<Button-1>", lambda e: _close())

    # ------------------------------------------------------------------
    # Persistencia de settings
    # ------------------------------------------------------------------

    def _settings_path(self) -> str:
        config_dir = os.path.expanduser("~/.config/fot")
        os.makedirs(config_dir, exist_ok=True)
        return os.path.join(config_dir, "notifications.json")

    def _save_settings(self) -> None:
        try:
            import json
            settings = {
                "sound_enabled": self._sound_enabled,
                "volume": self._volume,
                "toast_enabled": self._toast_enabled,
            }
            with open(self._settings_path(), "w") as f:
                json.dump(settings, f)
        except Exception as e:
            logger.warning("No se pudieron guardar settings de notificaciones: %s", e)

    def _load_settings(self) -> None:
        try:
            import json
            path = self._settings_path()
            if os.path.exists(path):
                with open(path, "r") as f:
                    settings = json.load(f)
                self._sound_enabled = settings.get("sound_enabled", True)
                self._volume = settings.get("volume", 0.5)
                self._toast_enabled = settings.get("toast_enabled", True)
        except Exception as e:
            logger.debug("No se pudieron cargar settings de notificaciones: %s", e)