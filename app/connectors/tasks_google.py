from typing import List, Optional, Dict, Any
from app.models import TaskItem, TaskOp

class GoogleTasksConnector:
    """Minimal Google Tasks fallback connector.
    You can wire Google Tasks API here if desired; placeholder signatures included.
    """
    def __init__(self, gtasks_service=None):
        self.svc = gtasks_service  # not wired by default in this MVP

    def create(self, tasks: List[TaskItem]) -> List[str]:
        # TODO: Implement with Google Tasks API if needed.
        return [f"(created locally) {t.title}" for t in tasks]

    def update(self, op: TaskOp) -> str:
        # TODO: Implement
        return "(update - not implemented)"

    def list(self, criteria: Optional[Dict[str, Any]] = None) -> List[str]:
        # TODO: Implement
        return ["(list - not implemented)"]

    def complete(self, op: TaskOp) -> str:
        # TODO: Implement
        return "(complete - not implemented)"

    def delete(self, op: TaskOp) -> str:
        # TODO: Implement
        return "(delete - not implemented)"
