# controller/auth_controller.py
import logging

from domain.user import User
from service.auth_service import AuthService

logger = logging.getLogger(__name__)


class AuthController:
    """
    Adaptador entre la UI (LoginDialog/RegisterDialog) y AuthService.
    Traduce interacciones del usuario en llamadas al servicio.
    Devuelve resultados; la UI decide cómo mostrar errores.
    """

    def __init__(self, auth_service: AuthService):
        self._service = auth_service

    # ------------------------------------------------------------------
    # Login
    # ------------------------------------------------------------------
    def login(self, username: str, password: str) -> tuple[bool, User | str]:
        """
        Intenta autenticar un usuario.
        Retorna (éxito, User) o (False, mensaje_error).
        """
        return self._service.login(username, password)

    # ------------------------------------------------------------------
    # Registro
    # ------------------------------------------------------------------
    def register(self, username: str, password: str, role: str = "user") -> tuple[bool, str]:
        """
        Registra un nuevo usuario.
        Retorna (éxito, mensaje_error).
        """
        return self._service.register(username, password, role)

    # ------------------------------------------------------------------
    # Admin: gestión de usuarios
    # ------------------------------------------------------------------
    def list_users(self, requesting_user: User) -> tuple[bool, list[dict] | str]:
        return self._service.list_users(requesting_user)

    def delete_user(self, requesting_user: User, target_user_id: int) -> tuple[bool, str]:
        return self._service.delete_user(requesting_user, target_user_id)

    # ------------------------------------------------------------------
    # Cambio de contraseña
    # ------------------------------------------------------------------
    def change_password(self, user: User, old_password: str, new_password: str) -> tuple[bool, str]:
        return self._service.change_password(user, old_password, new_password)

    # ------------------------------------------------------------------
    # Utilidades
    # ------------------------------------------------------------------
    def ensure_admin_exists(self) -> None:
        """Crea admin por defecto si no hay usuarios."""
        self._service.ensure_admin_exists()

    def can_register(self, current_user: User | None = None) -> bool:
        """
        True si se permite registrar nuevos usuarios.
        - Sin usuarios: cualquiera puede registrar (primer admin)
        - Con admin logueado: solo admin puede registrar
        """
        if current_user is None:
            # No hay sesión: permitir solo si no hay usuarios
            return not self._service._db.user_exists()
        return current_user.is_admin()
