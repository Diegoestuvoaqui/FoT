from __future__ import annotations

import logging
import os
import re
import subprocess
import threading
from collections import deque
from collections.abc import Callable, Sequence

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[str], None]

_PERCENT = re.compile(r"(\d{1,3})\s*%")


def extract_percent(line: str) -> int | None:
    """Saca un porcentaje (0-100) de una línea de avrdude o esptool, si lo hay."""
    m = _PERCENT.search(line)
    if not m:
        return None
    value = int(m.group(1))
    return value if 0 <= value <= 100 else None


class ProcessRunner:
    """Ejecuta un comando externo, transmite su salida y permite cancelarlo."""

    def __init__(self) -> None:
        self._proc: subprocess.Popen | None = None
        self._cancelled = False
        self._lock = threading.Lock()

    def run(self, cmd: Sequence[str], progress_callback: ProgressCallback | None = None,
            *, tool: str = "proceso",
            ok_msg: str = "✅ Firmware cargado correctamente.") -> tuple[bool, str]:
        self._cancelled = False
        logger.info("Ejecutando %s: %s", tool, " ".join(cmd))

        env = {**os.environ, "PYTHONUNBUFFERED": "1"}
        try:
            proc = subprocess.Popen(
                list(cmd),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                text=True,
                errors="replace",
                bufsize=1,
                env=env,
            )
        except OSError as e:
            return False, f"❌ No se pudo ejecutar {tool}: {e}"

        with self._lock:
            self._proc = proc

        tail: deque[str] = deque(maxlen=4)
        try:
            if proc.stdout:
                for raw in proc.stdout:
                    if self._cancelled:
                        break
                    line = raw.strip()
                    if not line:
                        continue
                    tail.append(line)
                    if progress_callback:
                        try:
                            progress_callback(line)
                        except Exception:
                            logger.exception("Error en progress_callback")

            if self._cancelled:
                self._terminate(proc)
                return False, "Operación cancelada por el usuario."

            proc.wait()
            if proc.returncode == 0:
                return True, ok_msg
            detail = tail[-1] if tail else ""
            return False, f"❌ Error de {tool} (código {proc.returncode}). {detail}".strip()
        except Exception as e:
            self._terminate(proc)
            return False, f"❌ Error inesperado: {e}"
        finally:
            with self._lock:
                self._proc = None

    def cancel(self) -> None:
        """Pide cancelar la operación en curso (seguro llamarlo desde otro hilo)."""
        self._cancelled = True
        with self._lock:
            proc = self._proc
        if proc is not None:
            logger.info("Cancelando proceso (PID: %s)", proc.pid)
            self._terminate(proc)

    @staticmethod
    def _terminate(proc: subprocess.Popen) -> None:
        if proc.poll() is not None:
            return
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            logger.warning("El proceso no respondió a SIGTERM, forzando kill")
            proc.kill()
            proc.wait()
