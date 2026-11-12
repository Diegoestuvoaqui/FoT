# service/auth_service.py
"""Autenticación y gestión de usuarios.

Reglas de esta fase:
- bcrypt obligatorio (sin fallback a SHA-256). Si falta el paquete,
  la app no arranca: es más seguro que un downgrade silencioso.
- Política de contraseñas centralizada: mínimo configurable, sin ser
  igual al usuario, sin estar en una lista corta de comunes.
- Bloqueo por intentos fallidos (failed_attempts / locked_until).
- Login uniforme: mismo mensaje y mismo tiempo para "usuario no
  existe" y "contraseña incorrecta".
- Rehash automático: si encuentra un hash SHA-256 viejo, lo migra a
  bcrypt en el siguiente login correcto.
- Autorización: primer usuario queda como admin; usuarios adicionales
  solo los crea un admin (o cualquier usuario si allow_self_register).
"""
from __future__ import annotations

import hashlib
import logging
import secrets
import re  
import bcrypt

from data.database import Database
from domain.user import Role, User

logger = logging.getLogger(__name__)

_DUMMY_HASH = bcrypt.hashpw(b"dummy-password", bcrypt.gensalt(rounds=12)).decode()
_COMMON_PASSWORDS = {
    "12345678", "123456789", "password", "password1", "qwerty123",
    "admin123", "letmein1", "iloveyou", "welcome1", "abc12345",
}


class AuthService:
    def __init__(self,
                 db: Database,
                 allow_self_register: bool = False,
                 password_min_length: int = 8,
                 login_max_attempts: int = 5,
                 login_lock_seconds: int = 60):
        self._db = db
        self._allow_self_register = allow_self_register
        self._password_min_length = password_min_length
        self._max_attempts = login_max_attempts
        self._lock_seconds = login_lock_seconds

    # ------------------------------------------------------------------
    # Validaciones
    # ------------------------------------------------------------------
    @staticmethod
    def _validate_username(username: str) -> tuple[bool, str]:
        if not username or not username.strip():
            return False, "El usuario es obligatorio"
        if " " in username:
            return False, "El usuario no puede contener espacios"
        if len(username) > 64:
            return False, "El usuario es demasiado largo (máx 64)"
        return True, ""

    def validate_password(self, password: str,
                          username: str = "") -> tuple[bool, str]:
        if not password:
            return False, "La contraseña es obligatoria"
        if " " in password:
            return False, "La contraseña no puede contener espacios"
        if len(password) < self._password_min_length:
            return False, (
                f"La contraseña debe tener al menos "
                f"{self._password_min_length} caracteres "
                f"(ahora tiene {len(password)})")
        if not re.search(r"[A-Za-z]", password):
            return False, "La contraseña debe contener al menos una letra"
        if not re.search(r"\d", password):
            return False, "La contraseña debe contener al menos un número"
        if username and password.lower() == username.lower():
            return False, "La contraseña no puede ser igual al usuario"
        if password.lower() in _COMMON_PASSWORDS:
            return False, "Esa contraseña es demasiado común"
        return True, ""

    # ------------------------------------------------------------------
    # Registro
    # ------------------------------------------------------------------
    def register(self,
                 username: str,
                 password: str,
                 role: str = Role.USER.value,
                 actor: User | None = None) -> tuple[bool, str]:
        ok, msg = self._validate_username(username)
        if not ok:
            return False, msg
        ok, msg = self.validate_password(password, username)
        if not ok:
            return False, msg

        is_first_user = not self._db.user_exists()

        if is_first_user:
            if actor is not None:
                # No debería pasar: no puede haber admin si no hay usuarios
                return False, "No hay usuarios registrados; regístrate primero"
            role = Role.ADMIN.value
        else:
            if actor is None:
                if not self._allow_self_register:
                    return False, "Solo un administrador puede crear cuentas"
                role = Role.USER.value
            elif not actor.is_admin():
                return False, "Permiso denegado"

        if role not in (Role.ADMIN.value, Role.USER.value):
            return False, "Rol inválido"

        if self._db.get_user_by_username(username):
            return False, f"El usuario '{username}' ya existe"

        password_hash = self._hash_password(password)
        try:
            user_id = self._db.create_user(username, password_hash, role)
            logger.info("Usuario creado: %s (id=%s, role=%s) por %s",
                        username, user_id, role,
                        actor.username if actor else "auto-registro")
            return True, ""
        except Exception as e:
            logger.error("Error al registrar usuario: %s", e)
            return False, "Error interno al crear usuario"

    def can_register(self, current_user: User | None = None) -> bool:
        """¿Puede mostrarse / ejecutarse el registro?

        - Sin usuarios: True (crear el primer admin).
        - Con usuario admin: True.
        - Anónimo (sin sesión) tras el primer usuario:
          depende de `allow_self_register`.
        """
        if current_user is None:
            if not self._db.user_exists():
                return True
            return self._allow_self_register
        return current_user.is_admin()

    # ------------------------------------------------------------------
    # Login
    # ------------------------------------------------------------------
    def user_exists(self) -> bool:
        """True si hay al menos un usuario registrado.
        Público para que main.py no tenga que acceder a `self._db`
        (Fase 6 del plan)."""
        return self._db.user_exists()

    def login(self, username: str, password: str) -> tuple[bool, User | str]:
        ok, msg = self._validate_username(username)
        if not ok:
            return False, msg

        row = self._db.get_user_by_username(username)
        if not row:
            # Timing uniforme: mismo costo que si existiera
            bcrypt.checkpw(password.encode(), _DUMMY_HASH.encode())
            return False, "Usuario o contraseña incorrectos"

        if self._db.is_user_locked(row["id"]):
            return False, ("Cuenta bloqueada por intentos fallidos. "
                           "Espera unos minutos e inténtalo de nuevo.")

        # Verificación (con rehash automático si es SHA-256 viejo)
        if not self._verify_and_maybe_rehash(row["id"], password,
                                             row["password_hash"]):
            attempts = self._db.register_failed_login(
                row["id"],
                max_attempts=self._max_attempts,
                lock_seconds=self._lock_seconds,
            )
            logger.warning("Login fallido: %s (intento %s)", username, attempts)
            if attempts >= self._max_attempts:
                return False, (
                    "Demasiados intentos fallidos. "
                    "La cuenta quedó bloqueada temporalmente.")
            return False, "Usuario o contraseña incorrectos"

        if not row.get("is_active", 1):
            return False, "Cuenta desactivada. Contacta al administrador."

        self._db.reset_failed_login(row["id"])
        self._db.update_user_last_login(row["id"])

        user = User(
            id=row["id"],
            username=row["username"],
            role=row["role"],
            is_active=bool(row.get("is_active", 1)),
            must_change_password=bool(row.get("must_change_password", 0)),
        )
        logger.info("Login exitoso: %s (role=%s, must_change=%s)",
                    username, user.role, user.must_change_password)
        return True, user

    def _verify_and_maybe_rehash(self, user_id: int, password: str,
                                 stored_hash: str) -> bool:
        if _looks_like_sha256(stored_hash):
            if hashlib.sha256(password.encode()).hexdigest() != stored_hash:
                return False
            new_hash = self._hash_password(password)
            self._db.update_user_password(user_id, new_hash)
            logger.info("Hash SHA-256 migrado a bcrypt para user id=%s", user_id)
            return True
        try:
            return bcrypt.checkpw(password.encode(), stored_hash.encode())
        except (ValueError, TypeError):
            return False

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

    def delete_user(self, requesting_user: User,
                    target_user_id: int) -> tuple[bool, str]:
        if not requesting_user.is_admin():
            return False, "Permiso denegado"
        if requesting_user.id == target_user_id:
            return False, "No puedes eliminarte a ti mismo"
        if not self._db.get_user_by_id(target_user_id):
            return False, "Usuario no encontrado"
        self._db.delete_user(target_user_id)
        logger.info("Usuario eliminado: %s (por admin %s)",
                    target_user_id, requesting_user.username)
        return True, ""

    def reset_password(self, requesting_user: User,
                       target_user_id: int) -> tuple[bool, str]:
        if not requesting_user.is_admin():
            return False, "Permiso denegado"
        if requesting_user.id == target_user_id:
            return False, "Usá 'Cambiar contraseña' para tu propia cuenta"
        row = self._db.get_user_by_id(target_user_id)
        if not row:
            return False, "Usuario no encontrado"
        temp_password = secrets.token_urlsafe(12)
        new_hash = self._hash_password(temp_password)
        self._db.update_user_password(target_user_id, new_hash)
        self._db.set_must_change_password(target_user_id, True)
        logger.info("Admin %s reseteó password de user id=%s",
                    requesting_user.username, target_user_id)
        return True, temp_password

    def toggle_user_active(self, requesting_user: User,
                           target_user_id: int, active: bool) -> tuple[bool, str]:
        if not requesting_user.is_admin():
            return False, "Permiso denegado"
        if requesting_user.id == target_user_id:
            return False, "No puedes desactivar tu propia cuenta"
        if not self._db.get_user_by_id(target_user_id):
            return False, "Usuario no encontrado"
        self._db.set_user_active(target_user_id, active)
        estado = "activada" if active else "desactivada"
        logger.info("Cuenta %s: user id=%s (por admin %s)",
                    estado, target_user_id, requesting_user.username)
        return True, f"Cuenta {estado}"

    # ------------------------------------------------------------------
    # Cambio de contraseña propia
    # ------------------------------------------------------------------
    def change_password(self, user: User, old_password: str,
                        new_password: str) -> tuple[bool, str]:
        ok, msg = self.validate_password(new_password, user.username)
        if not ok:
            return False, msg
        row = self._db.get_user_by_id(user.id)
        if not row or not self._verify_and_maybe_rehash(
                user.id, old_password, row["password_hash"]):
            return False, "Contraseña actual incorrecta"
        new_hash = self._hash_password(new_password)
        self._db.update_user_password(user.id, new_hash)
        self._db.set_must_change_password(user.id, False)
        logger.info("Contraseña cambiada: %s", user.username)
        return True, ""

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _hash_password(password: str) -> str:
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()


def _looks_like_sha256(h: str) -> bool:
    if not h or len(h) != 64:
        return False
    return all(c in "0123456789abcdef" for c in h)