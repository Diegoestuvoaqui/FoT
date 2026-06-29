# controller/auth_controller.py
import logging

from domain.user import User
from service.auth_service import AuthService

logger = logging.getLogger(__name__)


class AuthController:
    def __init__(self, auth_service: AuthService):
        self._service = auth_service

    # ------------------------------------------------------------------
    # Login
    # ------------------------------------------------------------------
    def login(self, username: str, password: str) -> tuple[bool, User | str]:
        return self._service.login(username, password)

    # ------------------------------------------------------------------
    # Registro
    # ------------------------------------------------------------------
    def register(self, username: str, password: str, role: str = "user") -> tuple[bool, str]:
        return self._service.register(username, password, role)

    # ------------------------------------------------------------------
    # Admin: gestión de usuarios
    # ------------------------------------------------------------------
    def list_users(self, requesting_user: User) -> tuple[bool, list[dict] | str]:
        return self._service.list_users(requesting_user)

    def delete_user(self, requesting_user: User, target_user_id: int) -> tuple[bool, str]:
        return self._service.delete_user(requesting_user, target_user_id)

    def reset_password(self, requesting_user: User, target_user_id: int) -> tuple[bool, str]:
        return self._service.reset_password(requesting_user, target_user_id)

    def toggle_user_active(self, requesting_user: User, target_user_id: int, active: bool) -> tuple[bool, str]:
        return self._service.toggle_user_active(requesting_user, target_user_id, active)

    # ------------------------------------------------------------------
    # Cambio de contraseña
    # ------------------------------------------------------------------
    def change_password(self, user: User, old_password: str, new_password: str) -> tuple[bool, str]:
        return self._service.change_password(user, old_password, new_password)

    # ------------------------------------------------------------------
    # Utilidades
    # ------------------------------------------------------------------
    def ensure_admin_exists(self) -> None:
        self._service.ensure_admin_exists()

    def can_register(self, current_user: User | None = None) -> bool:
        if current_user is None:
            return not self._service._db.user_exists()
        return current_user.is_admin()