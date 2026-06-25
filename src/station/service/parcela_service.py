# service/parcela_service.py
import logging

from data.database import Database
from domain.components import Finca, Parcela
from domain.memento import ConfigManager
from logic.db_verifier import verify_parcela_saved

logger = logging.getLogger(__name__)


class ParcelaService:
    """
    Gestiona el ciclo de vida de las parcelas:
    - CRUD (crear, leer, actualizar, eliminar)
    - Validaciones de negocio
    - Persistencia en BD con verificación
    - Snapshots antes de modificaciones
    - Umbrales y modo de operación
    """

    def __init__(self,
                 finca: Finca,
                 db: Database,
                 config_manager: ConfigManager,
                 irrigation_service,
                 usuario_id: int):
        self._finca = finca
        self._db = db
        self._config_manager = config_manager
        self._irrigation_service = irrigation_service
        self._usuario_id = usuario_id

        self._observers: list = []

    # ------------------------------------------------------------------
    # CRUD con usuario_id
    # ------------------------------------------------------------------
    def create(self, parcela_id: str, name: str) -> Parcela:
        pid = parcela_id.strip()
        name = name.strip()

        if not pid or not name:
            raise ValueError("ID y nombre son obligatorios")

        if self._finca.get_parcela(pid):
            raise ValueError(f"Ya existe una parcela con ID '{pid}'")

        # Snapshot antes de modificar
        self._config_manager.save_snapshot(
            self._finca,
            f"Antes de añadir parcela {pid}",
            self._db
        )

        # Crear en modelo con usuario_id
        parcela = Parcela(
            id=pid,
            name=name,
            usuario_id=self._usuario_id,  # ← ASIGNAR AL CREAR
        )
        self._finca.add_parcela(parcela)

        # Persistir en BD con usuario_id
        data = {
            "id": pid,
            "usuario_id": self._usuario_id,  # ← GUARDAR EN BD
            "name": name,
            "umbral_min": 30.0,
            "umbral_max": 70.0,
            "modo": "manual",
        }
        self._db.save_parcela(data)

        if not self._verify_save(pid, {"name": name, "usuario_id": self._usuario_id}):
            self._finca.remove_parcela(pid)
            raise RuntimeError("Error de escritura en base de datos")

        self._notify()
        logger.info("Parcela '%s' (%s) creada para usuario %s", name, pid, self._usuario_id)
        return parcela

    # ------------------------------------------------------------------
    # Observadores
    # ------------------------------------------------------------------
    def add_observer(self, callback):
        """
        Registra un callback on_parcelas_changed().
        La UI se suscribe para refrescar la lista cuando cambia una parcela.
        """
        self._observers.append(callback)

    def remove_observer(self, callback):
        self._observers.remove(callback)

    def _notify(self):
        for obs in self._observers:
            obs()

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------
    def create(self, parcela_id: str, name: str) -> Parcela:
        """
        Crea una nueva parcela, la persiste en BD y la añade al modelo.
        Retorna la parcela creada.
        Levanta ValueError si hay error de validación.
        """
        pid = parcela_id.strip()
        name = name.strip()

        if not pid or not name:
            raise ValueError("ID y nombre son obligatorios")

        if self._finca.get_parcela(pid):
            raise ValueError(f"Ya existe una parcela con ID '{pid}'")

        # Snapshot antes de modificar
        self._config_manager.save_snapshot(
            self._finca,
            f"Antes de añadir parcela {pid}",
            self._db
        )

        # Crear en modelo
        parcela = Parcela(pid, name)
        self._finca.add_parcela(parcela)

        # Persistir en BD
        data = {
            "id": pid,
            "name": name,
            "umbral_min": 30.0,
            "umbral_max": 70.0,
            "modo": "manual",
        }
        self._db.save_parcela(data)

        # Verificar
        if not self._verify_save(pid, {"name": name}):
            # Revertir modelo si falló la persistencia
            self._finca.remove_parcela(pid)
            raise RuntimeError("Error de escritura en base de datos")

        self._notify()
        logger.info("Parcela '%s' (%s) creada", name, pid)
        return parcela

    def delete(self, parcela_id: str) -> None:
        """
        Elimina una parcela del modelo y de la BD.
        Levanta ValueError si la parcela no existe.
        """
        if not parcela_id:
            raise ValueError("ID de parcela requerido")

        if self._finca.get_parcela(parcela_id) is None:
            raise ValueError(f"Parcela '{parcela_id}' no encontrada")

        # Snapshot antes de modificar
        self._config_manager.save_snapshot(
            self._finca,
            f"Antes de eliminar parcela {parcela_id}",
            self._db
        )

        # Eliminar de BD
        self._db.delete_parcela(parcela_id)

        # Verificar eliminación
        if self._db.get_parcela(parcela_id) is not None:
            raise RuntimeError("Error al eliminar parcela de la base de datos")

        # Eliminar del modelo
        self._finca.remove_parcela(parcela_id)

        self._notify()
        logger.info("Parcela '%s' eliminada", parcela_id)

    def get(self, parcela_id: str) -> Parcela | None:
        """Retorna una parcela por ID, o None si no existe."""
        return self._finca.get_parcela(parcela_id)

    def list_all(self) -> list[Parcela]:
        """Retorna todas las parcelas de la finca."""
        return self._finca.get_children()

    # ------------------------------------------------------------------
    # Umbrales
    # ------------------------------------------------------------------
    def set_thresholds(self, parcela_id: str, min_str: str, max_str: str) -> None:
        """
        Actualiza los umbrales de humedad de una parcela.
        Valida rango (0-100, min < max) y persiste con verificación.
        Envía el comando al hardware vía irrigation_service.
        """
        parcela = self._finca.get_parcela(parcela_id)
        if not parcela:
            raise ValueError(f"Parcela '{parcela_id}' no encontrada")

        try:
            min_val = float(min_str)
            max_val = float(max_str)
        except ValueError:
            raise ValueError("Los umbrales deben ser números")

        if not (0 <= min_val < max_val <= 100):
            raise ValueError("Umbrales inválidos: 0 ≤ min < max ≤ 100")

        # Snapshot antes de modificar
        self._config_manager.save_snapshot(
            self._finca,
            f"Antes de cambiar umbrales en {parcela_id}",
            self._db
        )

        # Actualizar modelo
        parcela.umbral_min = min_val
        parcela.umbral_max = max_val

        # Persistir en BD
        data = {
            "id": parcela_id,
            "name": parcela.get_name(),
            "umbral_min": min_val,
            "umbral_max": max_val,
            "modo": parcela.modo,
        }
        self._db.save_parcela(data)

        # Verificar
        expected = {"umbral_min": min_val, "umbral_max": max_val}
        if not self._verify_save(parcela_id, expected):
            raise RuntimeError("Error de escritura en base de datos")

        # Enviar comando al hardware
        self._irrigation_service.set_thresholds(parcela_id, min_val, max_val)

        self._notify()
        logger.info(
            "Umbrales actualizados en %s: min=%s%% max=%s%%",
            parcela_id, min_val, max_val
        )

    # ------------------------------------------------------------------
    # Modo
    # ------------------------------------------------------------------
    def set_mode(self, parcela_id: str, value: str) -> None:
        """
        Cambia el modo de una parcela.
        value: 'automático' o 'manual' (viene de la UI).
        """
        parcela = self._finca.get_parcela(parcela_id)
        if not parcela:
            raise ValueError(f"Parcela '{parcela_id}' no encontrada")

        modo = "auto" if value == "automático" else "manual"
        parcela.modo = modo

        # Persistir en BD
        data = {
            "id": parcela_id,
            "name": parcela.get_name(),
            "umbral_min": parcela.umbral_min,
            "umbral_max": parcela.umbral_max,
            "modo": modo,
        }
        self._db.save_parcela(data)

        # Enviar comando al hardware
        self._irrigation_service.set_mode(parcela_id, modo)

        self._notify()
        logger.info("Modo cambiado a '%s' en %s", modo, parcela_id)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _verify_save(self, parcela_id: str, expected: dict) -> bool:
        """Verifica que una escritura en BD se haya aplicado correctamente."""
        saved_ok = verify_parcela_saved(self._db, parcela_id, expected)
        if not saved_ok:
            logger.warning("Verificación fallida para %s, reintentando...", parcela_id)
            # Reintentar una vez
            # Nota: el caller debe haber hecho save_parcela antes de llamar esto
            # Aquí solo verificamos; el reintento lo hace el caller si quiere
        return saved_ok
