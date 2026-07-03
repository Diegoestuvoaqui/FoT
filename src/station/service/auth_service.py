# service/auth_service.py
import logging
import secrets

try:
    import bcrypt
except ImportError:
    bcrypt = None

from data.database import Database
from domain.user import User, Role

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(self, db: Database):
        self._db = db

    # ------------------------------------------------------------------
    # Validaciones compartidas
    # ------------------------------------------------------------------
    @staticmethod
    def _validate_username(username: str) -> tuple[bool, str]:
        if not username or not username.strip():
            return False, "El usuario es obligatorio"
        if " " in username:
            return False, "El usuario no puede contener espacios"
        return True, ""

    @staticmethod
    def _validate_password(password: str) -> tuple[bool, str]:
        if not password:
            return False, "La contraseña es obligatoria"
        if " " in password:
            return False, "La contraseña no puede contener espacios"
        if len(password) < 4:
            return False, "La contraseña debe tener al menos 4 caracteres"
        return True, ""

    # ------------------------------------------------------------------
    # Registro
    # ------------------------------------------------------------------
    def register(self, username: str, password: str, role: str = Role.USER.value) -> tuple[bool, str]:
        ok, msg = self._validate_username(username)
        if not ok:
            return False, msg

        ok, msg = self._validate_password(password)
        if not ok:
            return False, msg

        existing = self._db.get_user_by_username(username)
        if existing:
            return False, f"El usuario '{username}' ya existe"

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
    # service/auth_service.py — login()
    def login(self, username: str, password: str) -> tuple[bool, User | str]:
        ok, msg = self._validate_username(username)
        if not ok:
            return False, msg

        ok, msg = self._validate_password(password)
        if not ok:
            return False, msg

        row = self._db.get_user_by_username(username)
        if not row:
            return False, "Usuario o contraseña incorrectos"

        if not row.get("is_active", 1):
            return False, "Cuenta desactivada. Contacte al administrador."

        stored_hash = row["password_hash"]
        if not self._verify_password(password, stored_hash):
            return False, "Usuario o contraseña incorrectos"

        self._db.update_user_last_login(row["id"])

        user = User(
            id=row["id"],
            username=row["username"],
            role=row["role"],
            is_active=bool(row.get("is_active", 1)),
            must_change_password=bool(row.get("must_change_password", 0)),  # ← NUEVO
        )
        logger.info("Login exitoso: %s (role=%s, must_change=%s)",
                    username, user.role, user.must_change_password)
        return True, user
    # ------------------------------------------------------------------
    # Gestión de usuarios (solo admin)
    # ------------------------------------------------------------------
    def list_users(self, requesting_user: User) -> tuple[bool, list[dict] | str]:
        if not requesting_user.is_admin():
            return False, "Permiso denegado"
        users = self._db.list_users()
        for u in users:
            u.pop("password_hash", None)
        return True, users

    def delete_user(self, requesting_user: User, target_user_id: int) -> tuple[bool, str]:
        if not requesting_user.is_admin():
            return False, "Permiso denegado"
        if requesting_user.id == target_user_id:
            return False, "No puedes eliminarte a ti mismo"

        self._db.delete_user(target_user_id)
        logger.info("Usuario eliminado: %s (por admin %s)", target_user_id, requesting_user.username)
        return True, ""

    def reset_password(self, requesting_user: User, target_user_id: int) -> tuple[bool, str]:
        if not requesting_user.is_admin():
            return False, "Permiso denegado"
        if requesting_user.id == target_user_id:
            return False, "Usá 'Cambiar contraseña' para tu propia cuenta"

        row = self._db.get_user_by_id(target_user_id)
        if not row:
            return False, "Usuario no encontrado"

        temp_password = secrets.token_urlsafe(8)

        new_hash = self._hash_password(temp_password)
        self._db.update_user_password(target_user_id, new_hash)
        self._db.set_must_change_password(target_user_id, True)

        logger.info("Admin %s reseteó password de usuario id=%s",
                    requesting_user.username, target_user_id)
        return True, temp_password

    def toggle_user_active(self, requesting_user: User, target_user_id: int, active: bool) -> tuple[bool, str]:
        if not requesting_user.is_admin():
            return False, "Permiso denegado"
        if requesting_user.id == target_user_id:
            return False, "No puedes desactivar tu propia cuenta"

        row = self._db.get_user_by_id(target_user_id)
        if not row:
            return False, "Usuario no encontrado"

        self._db.set_user_active(target_user_id, active)
        estado = "activada" if active else "desactivada"
        logger.info("Cuenta %s: usuario id=%s (por admin %s)",
                    estado, target_user_id, requesting_user.username)
        return True, f"Cuenta {estado}"

    # ------------------------------------------------------------------
    # Cambio de contraseña propia
    # ------------------------------------------------------------------
    def change_password(self, user: User, old_password: str, new_password: str) -> tuple[bool, str]:
        ok, msg = self._validate_password(new_password)
        if not ok:
            return False, msg

        row = self._db.get_user_by_id(user.id)
        if not row or not self._verify_password(old_password, row["password_hash"]):
            return False, "Contraseña actual incorrecta"

        new_hash = self._hash_password(new_password)
        self._db.update_user_password(user.id, new_hash)
        self._db.set_must_change_password(user.id, False)
        logger.info("Contraseña cambiada para: %s", user.username)
        return True, ""

    # ------------------------------------------------------------------
    # Admin inicial
    # ------------------------------------------------------------------
    def ensure_admin_exists(self) -> None:
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
            import hashlib
            return hashlib.sha256(password.encode()).hexdigest()

    @staticmethod
    def _verify_password(password: str, stored_hash: str) -> bool:
        if bcrypt:
            return bcrypt.checkpw(password.encode(), stored_hash.encode())
        else:
            import hashlib
            return hashlib.sha256(password.encode()).hexdigest() == stored_hash