# controller/snapshot_controller.py
import logging

from service.snapshot_service import SnapshotService

logger = logging.getLogger(__name__)


class SnapshotController:
    def __init__(self, snapshot_service: SnapshotService):
        self._service = snapshot_service

    def save_manual(self, boards: list) -> None:
        self._service.save_manual(boards)

    def list_snapshots(self) -> list[dict]:
        return self._service.list_all()

    def restore(self, snapshot_id: int) -> dict:
        return self._service.restore(snapshot_id)