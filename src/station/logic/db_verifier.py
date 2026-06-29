"""
logic/db_verifier.py
Verifica que una operación de escritura en la base de datos se haya aplicado correctamente.
"""
import logging
from data.database import Database

logger = logging.getLogger(__name__)


def verify_board_saved(db: Database, board_id: str, expected: dict) -> bool:
    """
    Comprueba que la board con board_id tenga los campos de expected.
    expected debe contener las columnas que queremos verificar (ej: status, sketch_id).
    Retorna True si coinciden.
    """
    board = db.get_board_by_id(board_id)
    if board is None:
        return False
    for key, value in expected.items():
        if board.get(key) != value:
            return False
    return True
