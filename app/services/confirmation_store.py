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
        self._cleanup()
        self._store[user] = {
            "type": ptype,
            "payload": payload,
            "expires_at": dt.datetime.now() + dt.timedelta(minutes=self.ttl),
            "created_at": dt.datetime.now(),
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
        return t in {"1","confirm","confirmed","yes","y","ok","okay","sure","yep","yeah",
                     "oui","si","sí","ja","да","はい","כן","מאשר","מאשרת","לאשר","אשר","אישור","מְאָמֵת","✔","✅","👍"}

    @staticmethod
    def is_cancel(text: str) -> bool:
        t = (text or "").strip().lower()
        return t in {"0","cancel","c","no","n","abort","stop","nope","nah",
                     "nein","non","нет","いいえ","בטל","ביטול","לא","לבטל","✖","❌","👎"}
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about pending confirmations."""
        self._cleanup()
        stats = {
            "total": len(self._store),
            "by_type": {},
            "oldest_timestamp": None,
            "newest_timestamp": None
        }
        
        if self._store:
            timestamps = []
            for data in self._store.values():
                ptype = data.get("type", "unknown")
                stats["by_type"][ptype] = stats["by_type"].get(ptype, 0) + 1
                
                timestamp = data.get("created_at")
                if timestamp:
                    timestamps.append(timestamp)
            
            if timestamps:
                stats["oldest_timestamp"] = min(timestamps)
                stats["newest_timestamp"] = max(timestamps)
        
        return stats
