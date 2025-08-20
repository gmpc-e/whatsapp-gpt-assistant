import datetime as dt
from typing import Dict, Any, Optional, Literal
from app.models import EventCreate

class PendingStore:
    """In-memory confirmation store supporting multiple pending types."""
    def __init__(self, ttl_min: int = 10):
        self.ttl = ttl_min
        self._store: Dict[str, Dict[str, Any]] = {}

    def _cleanup(self):
        now = dt.datetime.now()
        to_del = [k for k, v in self._store.items() if v.get("expires_at") and v["expires_at"] < now]
        for k in to_del:
            self._store.pop(k, None)

    def add(self, user: str, ptype: Literal["create","update_select","update_confirm"], payload: Dict[str, Any]):
        self._store[user] = {
            "type": ptype,
            "payload": payload,
            "expires_at": dt.datetime.now() + dt.timedelta(minutes=self.ttl),
        }

    def has(self, user: str) -> bool:
        self._cleanup()
        return user in self._store

    def get(self, user: str) -> Optional[Dict[str, Any]]:
        self._cleanup()
        return self._store.get(user)

    def pop(self, user: str) -> Optional[Dict[str, Any]]:
        self._cleanup()
        return self._store.pop(user, None)

    @staticmethod
    def is_confirm(text: str) -> bool:
        t = (text or "").strip().lower()
        return t in {"1","confirm","confirmed","yes","y","ok","okay",
                     "oui","si","sí","ja","да","はい","כן","מאשר","מאשרת","לאשר","אשר","אישור","מְאָמֵת","✔","✅"}

    @staticmethod
    def is_cancel(text: str) -> bool:
        t = (text or "").strip().lower()
        return t in {"0","cancel","c","no","n","abort","stop",
                     "nein","non","нет","いいえ","בטל","ביטול","לא","לבטל","✖","❌"}
