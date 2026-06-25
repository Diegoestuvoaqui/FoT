from abc import ABC, abstractmethod
from typing import Callable


# --------------------------------------------------------------------------
# Clase abstracta — interfaz del Composite
# --------------------------------------------------------------------------
class IComponente(ABC):

    @abstractmethod
    def get_id(self) -> str:
        pass

    @abstractmethod
    def get_name(self) -> str:
        pass

    @abstractmethod
    def get_latest_reading(self) -> dict:
        pass

    @abstractmethod
    def get_children(self) -> list:
        pass

    def apply(self, operation: Callable) -> None:
        """Aplica operation a este nodo y recursivamente a todos sus hijos."""
        operation(self)
        for child in self.get_children():
            child.apply(operation)


# --------------------------------------------------------------------------
# Nodo intermedio — Parcela (ya no tiene dispositivos hijos)
# --------------------------------------------------------------------------
class Parcela(IComponente):

    def __init__(self,
                 id: str,
                 name: str,
                 usuario_id: int,
                 umbral_min: float = 30.0,
                 umbral_max: float = 70.0,
                 modo: str = "manual",
                 board_id: str | None = None):
        """
        modo: "auto" | "manual"
        board_id: ID del Arduino asignado (puede ser None)
        """
        self._id = id
        self._name = name
        self.usuario_id = usuario_id
        self.umbral_min = umbral_min
        self.umbral_max = umbral_max
        self.modo = modo
        self.board_id = board_id
        self.fsm_state: str = "Idle"
        self.relay_on: bool = False
        self.last_reading: dict = {}  # lecturas cacheadas del último mensaje

    # --- IComponente ---

    def get_id(self) -> str:
        return self._id

    def get_name(self) -> str:
        return self._name

    def get_children(self) -> list:
        return []  # ya no tiene hijos, es "hoja" del composite

    def get_latest_reading(self) -> dict:
        """Retorna la última lectura recibida (cacheada)."""
        return self.last_reading.copy()

    # --- Lecturas ---

    def update_reading(self, data: dict) -> None:
        """Actualiza la última lectura recibida (llamado por DataReceiver)."""
        self.last_reading = data.copy()

    def __repr__(self) -> str:
        return (f"Parcela(id={self._id!r}, usuario_id={self.usuario_id}, "
                f"board_id={self.board_id!r}, modo={self.modo!r})")


# --------------------------------------------------------------------------
# Raíz — contiene todas las parcelas de la finca
# --------------------------------------------------------------------------
class Finca(IComponente):

    def __init__(self, id: str, name: str):
        self._id = id
        self._name = name
        self._parcelas: list[Parcela] = []

    # --- IComponente ---

    def get_id(self) -> str:
        return self._id

    def get_name(self) -> str:
        return self._name

    def get_children(self) -> list:
        return list(self._parcelas)

    def get_latest_reading(self) -> dict:
        return {"finca_id": self._id, "parcelas": self.get_all_readings()}

    # --- Gestión de parcelas ---

    def add_parcela(self, parcela: Parcela) -> None:
        if not any(p.get_id() == parcela.get_id() for p in self._parcelas):
            self._parcelas.append(parcela)

    def remove_parcela(self, parcela_id: str) -> None:
        self._parcelas = [
            p for p in self._parcelas if p.get_id() != parcela_id
        ]

    def get_parcela(self, parcela_id: str) -> Parcela | None:
        return next((p for p in self._parcelas if p.get_id() == parcela_id), None)

    def get_parcelas_by_user(self, usuario_id: int) -> list[Parcela]:
        """Retorna solo las parcelas de un usuario."""
        return [p for p in self._parcelas if p.usuario_id == usuario_id]

    def get_all_readings(self) -> list[dict]:
        """Recopila lecturas de todas las parcelas."""
        readings = []

        def _collect(nodo: IComponente) -> None:
            if isinstance(nodo, Parcela):
                readings.append(nodo.get_latest_reading())

        self.apply(_collect)
        return readings

    def __repr__(self) -> str:
        return f"Finca(id={self._id!r}, parcelas={len(self._parcelas)})"
