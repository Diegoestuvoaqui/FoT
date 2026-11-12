# src/station/domain/permissions.py
"""Reglas de autorización centralizadas.

Un único lugar para decidir si un usuario puede hacer una acción.
La UI y los servicios llaman `can(actor, action, board)` en vez de
duplicar `if user.is_admin()` por todos lados.
"""
from __future__ import annotations

from typing import Optional

from domain.boards import Board
from domain.user import User


# Acciones reconocidas
ACT_MANAGE_USERS = "manage_users"
ACT_VIEW_AUDIT_ALL = "view_audit_all"
ACT_CREATE_USER = "create_user"
ACT_DELETE_USER = "delete_user"
ACT_RESET_PASSWORD = "reset_password"
ACT_CLAIM_BOARD = "claim_board"
ACT_UNASSIGN_BOARD = "unassign_board"
ACT_DELETE_BOARD = "delete_board"
ACT_ADMIN_REASSIGN_BOARD = "admin_reassign_board"
ACT_SET_RELAY = "set_relay"
ACT_FLASH_FIRMWARE = "flash_firmware"


def can(actor: Optional[User], action: str,
        board: Optional[Board] = None) -> bool:
    """Devuelve True si `actor` puede ejecutar `action` (opcionalmente
    sobre `board`). `actor=None` = sistema (acciones automáticas)."""
    if actor is None:
        return False

    is_admin = actor.is_admin()
    is_owner = (
        board is not None
        and actor.id is not None
        and board.usuario_id == actor.id
    )

    if action in (ACT_MANAGE_USERS, ACT_VIEW_AUDIT_ALL,
                  ACT_CREATE_USER, ACT_DELETE_USER,
                  ACT_RESET_PASSWORD, ACT_DELETE_BOARD,
                  ACT_ADMIN_REASSIGN_BOARD):
        return is_admin

    if action == ACT_CLAIM_BOARD:
        # Cualquier usuario autenticado; solo si la placa está libre.
        if board is None:
            return False
        return board.usuario_id is None

    if action == ACT_UNASSIGN_BOARD:
        return is_admin or is_owner

    if action in (ACT_SET_RELAY, ACT_FLASH_FIRMWARE):
        return is_admin or is_owner

    return False