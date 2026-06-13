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
# Hoja — representa un sensor o actuador individual
# --------------------------------------------------------------------------
class Dispositivo(IComponente):

    def __init__(self, id: str, name: str, parcela_id: str, tipo: str):
        """
        tipo: "sensor" | "actuador"
        """
        self._id = id
        self._name = name
        self.parcela_id = parcela_id
        self.tipo = tipo
        self.last_reading: dict = {}

    def get_id(self) -> str:
        return self._id

    def get_name(self) -> str:
        return self._name

    def get_children(self) -> list:
        return []  # hoja — sin hijos

    def get_latest_reading(self) -> dict:
        return self.last_reading.copy()

    def update_reading(self, data: dict) -> None:
        """Actualiza la última lectura conocida del dispositivo."""
        self.last_reading = data.copy()

    def __repr__(self) -> str:
        return f"Dispositivo(id={self._id!r}, tipo={self.tipo!r})"


# --------------------------------------------------------------------------
# Nodo intermedio — agrupa dispositivos y refleja el estado del Arduino
# --------------------------------------------------------------------------
class Parcela(IComponente):

    def __init__(self,
                 id: str,
                 name: str,
                 umbral_min: float = 30.0,
                 umbral_max: float = 70.0,
                 modo: str = "manual"):
        """
        modo: "auto" | "manual"
        Nota: la fuente de verdad del modo es el Arduino.
        Este campo solo se usa para mostrar estado en la UI.
        """
        self._id = id
        self._name = name
        self.umbral_min = umbral_min
        self.umbral_max = umbral_max
        self.modo = modo
        self._dispositivos: list[Dispositivo] = []
        self._dispositivos: list[Dispositivo] = []
        self.fsm_state: str = "Idle"  # ← nueva
        self.relay_on: bool = False  # ← nueva

    # --- IComponente ---

    def get_id(self) -> str:
        return self._id

    def get_name(self) -> str:
        return self._name

    def get_children(self) -> list:
        return list(self._dispositivos)

    def get_latest_reading(self) -> dict:
        """Agrega las últimas lecturas de todos los dispositivos hijos."""
        agregado = {"parcela_id": self._id}
        for d in self._dispositivos:
            agregado.update(d.get_latest_reading())
        return agregado

    # --- Gestión de dispositivos ---

    def add_device(self, dispositivo: Dispositivo) -> None:
        if not any(d.get_id() == dispositivo.get_id() for d in self._dispositivos):
            self._dispositivos.append(dispositivo)

    def remove_device(self, device_id: str) -> None:
        self._dispositivos = [
            d for d in self._dispositivos if d.get_id() != device_id
        ]

    def get_device(self, device_id: str) -> Dispositivo | None:
        return next((d for d in self._dispositivos if d.get_id() == device_id), None)

    def __repr__(self) -> str:
        return (f"Parcela(id={self._id!r}, modo={self.modo!r}, "
                f"dispositivos={len(self._dispositivos)})")


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

    def get_all_readings(self) -> list[dict]:
        """Recorre el árbol con apply() y recopila lecturas de todas las parcelas."""
        readings = []

        def _collect(nodo: IComponente) -> None:
            if isinstance(nodo, Parcela):
                readings.append(nodo.get_latest_reading())

        self.apply(_collect)
        return readings

    def __repr__(self) -> str:
        return f"Finca(id={self._id!r}, parcelas={len(self._parcelas)})"
