from __future__ import annotations

import logging
import subprocess
from collections.abc import Callable  # ← importar Callable correctamente

logger = logging.getLogger(__name__)


class FirmwareUploader:

    @staticmethod  # ← static: no usa self
    def upload(port: str, hex_path: str,
               mcu: str = "atmega328p",
               programmer: str = "arduino",
               baud: int = 115200,
               progress_callback: Callable[[str], None] | None = None  # ← tipo correcto
               ) -> tuple[bool, str]:

        cmd = [
            "avrdude",
            "-p", mcu,
            "-c", programmer,
            "-P", port,
            "-b", str(baud),
            "-U", f"flash:w:{hex_path}:i"
        ]
        logger.info(f"Ejecutando avrdude: {' '.join(cmd)}")
        try:
            with subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1
            ) as proc:
                if proc.stdout:  # ← guard para IO[str] | None
                    for line in proc.stdout:
                        if progress_callback:
                            progress_callback(line.strip())
                proc.wait()
                success = proc.returncode == 0
                if success:
                    msg = "Firmware cargado correctamente."
                else:
                    msg = f"Error de avrdude (código {proc.returncode})."
                return success, msg
        except FileNotFoundError:
            return False, "No se encontró 'avrdude'. Asegúrate de que esté instalado y en el PATH."
        except Exception as e:
            return False, f"Error inesperado: {e}"
