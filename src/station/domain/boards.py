# domain/boards.py


class Board:
    def __init__(self,
                 board_id: str,
                 conn: str = "unknown",
                 status: str = "Desconectada",
                 parcela: str | None = None,
                 usuario_id: int | None = None,
                 firmware_version: str | None = None,
                 conn_module: str = "",
                 port: str = "",
                 last_seen: str | None = None):
        self.id = board_id
        self.conn = conn  # usb, wifi, bluetooth
        self.status = status  # Conectada, Sin asignar, Desconectada
        self.parcela = parcela  # ID de parcela o None
        self.usuario_id = usuario_id  # ID del dueño o None
        self.firmware_version = firmware_version
        self.conn_module = conn_module  # W5100, ESP-01, HC-05, etc.
        self.port = port  # /dev/ttyUSB0, etc.
        self.last_seen = last_seen  # ISO 8601 timestamp

    def is_claimed(self) -> bool:
        """True si tiene un usuario asignado."""
        return self.usuario_id is not None

    def is_assigned(self) -> bool:
        """True si está asignado a una parcela."""
        return self.parcela is not None

    def __repr__(self) -> str:
        return (f"Board(id={self.id!r}, conn={self.conn!r}, "
                f"status={self.status!r}, parcela={self.parcela!r}, "
                f"usuario_id={self.usuario_id!r})")
