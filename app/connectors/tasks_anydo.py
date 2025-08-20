import os
import requests
from typing import List, Optional
from app.models import TaskItem, TaskOp

class AnyDoConnector:
    """
    Placeholder Any.do connector.
    NOTE: Any.do public API access may vary. Configure ANYDO_BASE_URL and ANYDO_TOKEN if available.
    Falls back to NotImplementedError when not configured.
    """
    def __init__(self):
        self.base = os.getenv("ANYDO_BASE_URL")
        self.token = os.getenv("ANYDO_TOKEN")

    def _session(self):
        if not (self.base and self.token):
            raise NotImplementedError("Any.do API is not configured. Set ANYDO_BASE_URL and ANYDO_TOKEN.")
        s = requests.Session()
        s.headers.update({"Authorization": f"Bearer {self.token}","Content-Type":"application/json"})
        return s

    def create(self, tasks: List[TaskItem]):
        raise NotImplementedError("Implement Any.do create using your account's API.")

    def update(self, op: TaskOp):
        raise NotImplementedError("Implement Any.do update using your account's API.")

    def list(self, criteria: Optional[dict] = None):
        raise NotImplementedError("Implement Any.do list using your account's API.")

    def complete(self, op: TaskOp):
        raise NotImplementedError("Implement Any.do complete using your account's API.")

    def delete(self, op: TaskOp):
        raise NotImplementedError("Implement Any.do delete using your account's API.")
