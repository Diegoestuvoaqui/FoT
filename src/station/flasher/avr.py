from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .paths import AVRDUDE, AVRDUDE_CONF, ensure_executable
from .runner import ProcessRunner, ProgressCallback


@dataclass(frozen=True)
class AvrProfile:
    mcu: str
    programmer: str
    baud: int


# Perfiles habituales. Ajusta el baud si tu bootloader es distinto.
AVR_PROFILES: dict[str, AvrProfile] = {
    "uno_r3": AvrProfile("atmega328p", "arduino", 115200),
    "nano_old_bootloader": AvrProfile("atmega328p", "arduino", 57600),
}


class AvrFlasher:
    """Carga archivos .hex a placas AVR (Uno R3, LAFVIN R3, Nano...) con el avrdude incluido."""

    def __init__(self) -> None:
        self._runner = ProcessRunner()

    @staticmethod
    def check_tools() -> tuple[bool, str]:
        if not AVRDUDE.is_file():
            return False, f"No se encontró avrdude incluido en {AVRDUDE}."
        if not AVRDUDE_CONF.is_file():
            return False, f"No se encontró avrdude.conf en {AVRDUDE_CONF}."
        if not ensure_executable(AVRDUDE):
            return False, "avrdude no tiene permiso de ejecución."
        return True, ""

    def upload(self, port: str, hex_path: str,
               mcu: str = "atmega328p",
               programmer: str = "arduino",
               baud: int = 115200,
               progress_callback: ProgressCallback | None = None
               ) -> tuple[bool, str]:
        """Carga el .hex. Devuelve (éxito, mensaje)."""
        ok, msg = self.check_tools()
        if not ok:
            return False, msg

        hex_file = Path(hex_path)
        if not hex_file.is_file():
            return False, f"No existe el archivo: {hex_file}"

        cmd = [
            str(AVRDUDE),
            "-C", str(AVRDUDE_CONF),   # fuerza el conf incluido, no el del sistema
            "-p", mcu,
            "-c", programmer,
            "-P", port,
            "-b", str(baud),
            "-D",                      # sin borrado de chip, como hace el IDE de Arduino
            "-U", f"flash:w:{hex_file}:i",
        ]
        return self._runner.run(cmd, progress_callback, tool="avrdude")

    def upload_profile(self, port: str, hex_path: str, profile: str = "uno_r3",
                       progress_callback: ProgressCallback | None = None
                       ) -> tuple[bool, str]:
        p = AVR_PROFILES[profile]
        return self.upload(port, hex_path, p.mcu, p.programmer, p.baud, progress_callback)

    def cancel(self) -> None:
        self._runner.cancel()


# Compatibilidad con el nombre anterior (logic/firmware_uploader.py)
FirmwareUploader = AvrFlasher
