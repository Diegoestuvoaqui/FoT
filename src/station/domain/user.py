# domain/user.py
from enum import Enum


class Role(Enum):
    ADMIN = "admin"
    USER = "user"


class User:
    """
    Representa un usuario del sistema.
    Inmutable una vez creado (excepto para cambio de password).
    """

    def __init__(self, id: int, username: str, role: str):
        self.id = id
        self.username = username
        self._role = role

    @property
    def role(self) -> str:
        return self._role

    def is_admin(self) -> bool:
        return self._role == Role.ADMIN.value

    def is_user(self) -> bool:
        return self._role == Role.USER.value

    def __repr__(self) -> str:
        return f"User(id={self.id}, username={self.username!r}, role={self.role!r})"

    def __eq__(self, other) -> bool:
        if not isinstance(other, User):
            return False
        return self.id == other.id
