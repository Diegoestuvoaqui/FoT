# src/station/service/audit_service.py
"""Registro de acciones para auditoría.

- Usuarios normales solo ven sus propias acciones.
- Admins ven todo.
- El propio registro se guarda en `audit_log` (Fase 3).
"""
from __future__ import annotations

import logging
from typing import Optional

from data.database import Database
from domain.user import User

logger = logging.getLogger(__name__)


class AuditService:
    def __init__(self, db: Database):
        self._db = db
        self._observers: list = []

    # ------------------------------------------------------------------
    def add_observer(self, callback) -> None:
        if callback not in self._observers:
            self._observers.append(callback)

    def remove_observer(self, callback) -> None:
        if callback in self._observers:
            self._observers.remove(callback)

    # ------------------------------------------------------------------
    def log(self,
            actor: Optional[User],
            accion: str,
            objetivo: Optional[str] = None,
            resultado: str = "ok",
            detalle: Optional[str] = None) -> None:
        try:
            self._db.save_audit(
                accion=accion,
                objetivo=objetivo,
                usuario_id=actor.id if actor else None,
                username=actor.username if actor else "system",
                resultado=resultado,
                detalle=detalle,
            )
        except Exception as e:
            logger.error("Error guardando audit_log: %s", e)
            return
        # Observer para refresco de UI
        for obs in list(self._observers):
            try:
                obs()
            except Exception as e:
                logger.error("Error en observer de auditoría: %s", e)

    # ------------------------------------------------------------------
    def list_events(self,
                    actor: User,
                    limit: int = 100,
                    usuario_id: Optional[int] = None) -> list[dict]:
        """Admin ve todo (o filtra por usuario). Usuario ve solo lo suyo."""
        if actor.is_admin():
            return self._db.get_audit(limit=limit, usuario_id=usuario_id)
        return self._db.get_audit(limit=limit, usuario_id=actor.id)