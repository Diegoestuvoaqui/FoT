# domain/boards.py
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