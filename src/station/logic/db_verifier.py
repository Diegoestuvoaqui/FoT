"""
logic/db_verifier.py
Verifica que una operación de escritura en la base de datos se haya aplicado correctamente.
"""
import logging
from data.database import Database

logger = logging.getLogger(__name__)


def verify_parcela_saved(db: Database, parcela_id: str, expected: dict) -> bool:
    """
    Comprueba que la parcela con parcela_id tenga los campos de expected.
    expected debe contener las columnas que queremos verificar (ej: umbral_min, umbral_max).
    Retorna True si coinciden.
    """
    parcela = db.get_parcela(parcela_id)  # Asumimos que get_parcela devuelve un dict o None
    if parcela is None:
        return False
    for key, value in expected.items():
        if parcela.get(key) != value:
            return False
    return True
