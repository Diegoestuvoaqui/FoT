# service/auth_service.py
import logging

try:
    import bcrypt
except ImportError:
    bcrypt = None  # fallback: hash simple con hashlib (no usar en producción)

from data.database import Database
from domain.user import User, Role

logger = logging.getLogger(__name__)


class AuthService:
    """
    Gestiona autenticación y autorización de usuarios.
    No importa tkinter.
    """

    def __init__(self, db: Database):
        self._db = db

    # ------------------------------------------------------------------
    # Registro
    # ------------------------------------------------------------------
    def register(self, username: str, password: str, role: str = Role.USER.value) -> tuple[bool, str]:
        """
        Crea un nuevo usuario.
        Retorna (éxito, mensaje_error).
        """
        if not username or not password:
            return False, "Usuario y contraseña son obligatorios"

        if len(password) < 4:
            return False, "La contraseña debe tener al menos 4 caracteres"

        # Verificar si ya existe
        existing = self._db.get_user_by_username(username)
        if existing:
            return False, f"El usuario '{username}' ya existe"

        # Hash de contraseña
        password_hash = self._hash_password(password)

        try:
            user_id = self._db.create_user(username, password_hash, role)
            logger.info("Usuario registrado: %s (id=%s, role=%s)", username, user_id, role)
            return True, ""
        except Exception as e:
            logger.error("Error al registrar usuario: %s", e)
            return False, "Error interno al crear usuario"

    # ------------------------------------------------------------------
    # Login
    # ------------------------------------------------------------------
    def login(self, username: str, password: str) -> tuple[bool, User | str]:
        """
        Verifica credenciales.
        Retorna (éxito, User) o (False, mensaje_error).
        """
        if not username or not password:
            return False, "Usuario y contraseña son obligatorios"

        row = self._db.get_user_by_username(username)
        if not row:
            return False, "Usuario o contraseña incorrectos"

        stored_hash = row["password_hash"]
        if not self._verify_password(password, stored_hash):
            return False, "Usuario o contraseña incorrectos"

        user = User(
            id=row["id"],
            username=row["username"],
            role=row["role"]
        )
        logger.info("Login exitoso: %s (role=%s)", username, user.role)
        return True, user

    # ------------------------------------------------------------------
    # Gestión de usuarios (solo admin)
    # ------------------------------------------------------------------
    def list_users(self, requesting_user: User) -> tuple[bool, list[dict] | str]:
        """Lista todos los usuarios. Solo admin."""
        if not requesting_user.is_admin():
            return False, "Permiso denegado"

        users = self._db.list_users()
        return True, users

    def delete_user(self, requesting_user: User, target_user_id: int) -> tuple[bool, str]:
        """Elimina un usuario. Solo admin. No puede eliminarse a sí mismo."""
        if not requesting_user.is_admin():
            return False, "Permiso denegado"

        if requesting_user.id == target_user_id:
            return False, "No puedes eliminarte a ti mismo"

        self._db.delete_user(target_user_id)
        logger.info("Usuario eliminado: %s (por admin %s)", target_user_id, requesting_user.username)
        return True, ""

    def change_password(self, user: User, old_password: str, new_password: str) -> tuple[bool, str]:
        """Cambia la contraseña de un usuario."""
        if len(new_password) < 4:
            return False, "La nueva contraseña debe tener al menos 4 caracteres"

        # Verificar old_password
        row = self._db.get_user_by_id(user.id)
        if not row or not self._verify_password(old_password, row["password_hash"]):
            return False, "Contraseña actual incorrecta"

        new_hash = self._hash_password(new_password)
        self._db.update_user_password(user.id, new_hash)
        logger.info("Contraseña cambiada para: %s", user.username)
        return True, ""

    # ------------------------------------------------------------------
    # Admin inicial
    # ------------------------------------------------------------------
    def ensure_admin_exists(self) -> None:
        """Crea admin por defecto si no hay usuarios."""
        if not self._db.user_exists():
            logger.info("No hay usuarios. Creando admin por defecto...")
            password_hash = self._hash_password("admin")
            self._db.create_user("admin", password_hash, Role.ADMIN.value)
            logger.warning("Admin creado: usuario='admin', contraseña='admin' — CAMBIA ESTA CONTRASEÑA")

    # ------------------------------------------------------------------
    # Helpers de hash
    # ------------------------------------------------------------------
    @staticmethod
    def _hash_password(password: str) -> str:
        if bcrypt:
            return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        else:
            # Fallback NO seguro — solo para desarrollo
            import hashlib
            return hashlib.sha256(password.encode()).hexdigest()

    @staticmethod
    def _verify_password(password: str, stored_hash: str) -> bool:
        if bcrypt:
            return bcrypt.checkpw(password.encode(), stored_hash.encode())
        else:
            import hashlib
            return hashlib.sha256(password.encode()).hexdigest() == stored_hash
