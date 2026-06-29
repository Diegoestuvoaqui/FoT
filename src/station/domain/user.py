# domain/user.py
from enum import Enum


class Role(Enum):
    ADMIN = "admin"
    USER = "user"


class User:
    def __init__(self, id: int, username: str, role: str, is_active: bool = True):
        self.id = id
        self.username = username
        self._role = role
        self.is_active = is_active

    @property
    def role(self) -> str:
        return self._role

    def is_admin(self) -> bool:
        return self._role == Role.ADMIN.value

    def is_user(self) -> bool:
        return self._role == Role.USER.value

    def __repr__(self) -> str:
        return f"User(id={self.id}, username={self.username!r}, role={self.role!r}, active={self.is_active})"

    def __eq__(self, other) -> bool:
        if not isinstance(other, User):
            return False
        return self.id == other.id