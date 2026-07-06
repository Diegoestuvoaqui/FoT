from __future__ import annotations

import logging
import subprocess
from collections.abc import Callable

logger = logging.getLogger(__name__)


class FirmwareUploader:
    """Gestiona la carga de firmware .hex vía avrdude con soporte de cancelación."""

    def __init__(self):
        self._proc: subprocess.Popen | None = None
        self._cancelled = False

    def upload(self, port: str, hex_path: str,
               mcu: str = "atmega328p",
               programmer: str = "arduino",
               baud: int = 115200,
               progress_callback: Callable[[str], None] | None = None
               ) -> tuple[bool, str]:
        """
        Ejecuta avrdude para cargar el firmware.
        Retorna (success, mensaje).
        """
        self._cancelled = False
        cmd = [
            "avrdude",
            "-p", mcu,
            "-c", programmer,
            "-P", port,
            "-b", str(baud),
            "-U", f"flash:w:{hex_path}:i"
        ]
        logger.info("Ejecutando avrdude: %s", " ".join(cmd))

        try:
            self._proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            if self._proc.stdout:
                for line in self._proc.stdout:
                    if self._cancelled:
                        break
                    if progress_callback:
                        progress_callback(line.strip())

            if self._cancelled:
                return False, "Operación cancelada por el usuario."

            self._proc.wait()
            success = self._proc.returncode == 0
            if success:
                msg = "✅ Firmware cargado correctamente."
            else:
                msg = f"❌ Error de avrdude (código {self._proc.returncode})."
            return success, msg

        except FileNotFoundError:
            return False, (
                "No se encontró 'avrdude'. "
                "Asegúrate de que esté instalado y en el PATH."
            )
        except Exception as e:
            return False, f"Error inesperado: {e}"
        finally:
            self._proc = None

    def cancel(self) -> None:
        """Solicita la cancelación del proceso de carga actual."""
        self._cancelled = True
        if self._proc is not None:
            logger.info("Cancelando avrdude (PID: %s)", self._proc.pid)
            self._proc.terminate()
            try:
                self._proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                logger.warning("avrdude no respondió a SIGTERM, forzando kill")
                self._proc.kill()
                self._proc.wait()
