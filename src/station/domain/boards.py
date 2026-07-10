# domain/boards.py
import hashlib

# Ranking de estados de CONEXIÓN (no de propiedad). Más alto = más "avanzado".
# Se usa para que un evento de detección física nunca degrade un estado
# ya más avanzado (ej: no puede pisar "Conectada" con "Detectada").
_CONN_STATE_RANK = {
    "Desconectada": 0,
    "Error de conexión": 0,
    "Detectada": 1,
    "Conectada": 2,
}

class Board:
    def __init__(self,
                 board_id: str,
                 conn: str = "unknown",
                 status: str = "Desconectada",
                 usuario_id: int | None = None,
                 sketch_id: str | None = None,
                 sketch_name: str | None = None,
                 sketch_version: str | None = None,
                 conn_module: str = "",
                 port: str = "",
                 last_seen: str | None = None,
                 # Nuevos campos de fábrica
                 hwid: str | None = None,
                 vid: int | None = None,
                 pid: int | None = None,
                 serial_number: str | None = None,
                 manufacturer: str | None = None,
                 product: str | None = None,
                 location: str | None = None):
        self.id = board_id
        self.conn = conn
        self.status = status
        self.usuario_id = usuario_id
        self.sketch_id = sketch_id
        self.sketch_name = sketch_name
        self.sketch_version = sketch_version
        self.conn_module = conn_module
        self.port = port
        self.last_seen = last_seen

        # Datos de fábrica del chip USB/Bluetooth
        self.hwid = hwid
        self.vid = vid
        self.pid = pid
        self.serial_number = serial_number
        self.manufacturer = manufacturer
        self.product = product
        self.location = location

    def is_claimed(self) -> bool:
        return self.usuario_id is not None

    def get_vendor_name(self) -> str:
        """Retorna nombre legible del vendor basado en VID."""
        vendors = {
            0x0403: "FTDI",
            0x1A86: "WCH (CH340/CH341)",
            0x10C4: "Silicon Labs (CP210x)",
            0x2341: "Arduino",
            0x2A03: "Arduino (Genuino)",
            0x239A: "Adafruit",
            0x0483: "STMicroelectronics",
        }
        return vendors.get(self.vid, f"VID:{self.vid:04X}" if self.vid else "Desconocido")

    def __repr__(self) -> str:
        return (f"Board(id={self.id!r}, conn={self.conn!r}, "
                f"status={self.status!r}, sketch={self.sketch_id!r}, "
                f"usuario_id={self.usuario_id!r}, sn={self.serial_number!r})")

    def on_physical_detected(self) -> bool:
        """
        Transición ante detección física USB/BT/WiFi.
        NUNCA toca usuario_id. Retorna True si el estado cambió.
        """
        if self.usuario_id is None:
            changed = self.status != "Sin asignar"
            self.status = "Sin asignar"
            return changed

        current_rank = _CONN_STATE_RANK.get(self.status, 0)
        if current_rank < _CONN_STATE_RANK["Detectada"]:
            self.status = "Detectada"
            return True
        return False

    def on_physical_lost(self) -> bool:
        """Transición ante pérdida de presencia física. Retorna True si cambió."""
        if self.status in ("Conectada", "Detectada", "Error de conexión"):
            self.status = "Desconectada"
            return True
        return False

    def claim(self, usuario_id: int) -> None:
        """Reclama una placa sin dueño. Falla si ya tiene uno."""
        if self.usuario_id is not None:
            raise PermissionError("La placa ya tiene dueño")
        self.usuario_id = usuario_id
        self.status = "Detectada"

    def release(self) -> None:
        """Libera la placa. Queda disponible para que cualquiera la reclame."""
        self.usuario_id = None
        self.status = "Sin asignar"



def resolve_board_identity(port_data: dict) -> str:
        """
        Resuelve un identificador estable y determinista para una placa física.

        Prioridad:
        1. serial_number del chip, si existe.
        2. Hash corto y determinista de vid+pid+manufacturer+product.
        El path del puerto (/dev/ttyUSB0) NUNCA es identidad, solo dato de conexión.
        """
        serial = (port_data.get("serial_number") or "").strip()
        if serial:
            return f"sn:{serial}"

        vid = port_data.get("vid") or 0
        pid = port_data.get("pid") or 0
        manufacturer = (port_data.get("manufacturer") or "").strip().lower()
        product = (port_data.get("product") or "").strip().lower()

        raw = f"{vid:04x}:{pid:04x}:{manufacturer}:{product}"
        digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]
        return f"hw:{digest}"