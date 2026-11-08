from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path

from .runner import ProcessRunner, ProgressCallback

# Flag con el que la app se re-invoca a sí misma cuando está empaquetada
ESPTOOL_FLAG = "--run-esptool"


def maybe_run_esptool() -> None:
    """Llamar al INICIO de main.py, antes de importar la GUI.

    Si la app fue lanzada con --run-esptool, ejecuta esptool y termina.
    """
    if len(sys.argv) > 1 and sys.argv[1] == ESPTOOL_FLAG:
        import esptool
        esptool.main(sys.argv[2:])
        sys.exit(0)


def _esptool_cmd() -> list[str]:
    if getattr(sys, "frozen", False):
        # Empaquetado: sys.executable es la propia app, no un intérprete de Python
        return [sys.executable, ESPTOOL_FLAG]
    return [sys.executable, "-m", "esptool"]


class EspFlasher:
    """Carga firmware .bin a ESP32 usando el esptool incluido (sintaxis de esptool 5.x)."""

    def __init__(self) -> None:
        self._runner = ProcessRunner()

    def upload(self, port: str, bin_path: str,
               offset: str = "0x10000",
               baud: int = 460800,
               chip: str = "auto",
               progress_callback: ProgressCallback | None = None
               ) -> tuple[bool, str]:
        """Carga una sola app .bin (por defecto en 0x10000, el offset de la app en ESP32)."""
        return self.upload_images(port, [(offset, bin_path)], baud, chip, progress_callback)

    def upload_images(self, port: str, images: Sequence[tuple[str, str]],
                      baud: int = 460800,
                      chip: str = "auto",
                      progress_callback: ProgressCallback | None = None
                      ) -> tuple[bool, str]:
        """Carga varias imágenes: [(offset, ruta), ...].

        Ejemplo ESP32 de PlatformIO:
        [("0x1000", "bootloader.bin"), ("0x8000", "partitions.bin"),
         ("0xe000", "boot_app0.bin"), ("0x10000", "firmware.bin")]
        (en ESP32-S3/C3 el bootloader va en 0x0)
        """
        if not images:
            return False, "No hay imágenes para cargar."
        for _, path in images:
            if not Path(path).is_file():
                return False, f"No existe el archivo: {path}"

        cmd = [*_esptool_cmd(), "--port", port, "--baud", str(baud)]
        if chip != "auto":
            cmd += ["--chip", chip]
        cmd.append("write-flash")
        for offset, path in images:
            cmd += [offset, str(path)]
        return self._runner.run(cmd, progress_callback, tool="esptool")

    def erase(self, port: str, baud: int = 460800,
              progress_callback: ProgressCallback | None = None
              ) -> tuple[bool, str]:
        """Borra toda la flash."""
        cmd = [*_esptool_cmd(), "--port", port, "--baud", str(baud), "erase-flash"]
        return self._runner.run(cmd, progress_callback, tool="esptool",
                                ok_msg="✅ Flash borrada correctamente.")

    def cancel(self) -> None:
        self._runner.cancel()
