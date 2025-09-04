"""Rate limiting utilities for API calls."""

import time
from collections import defaultdict, deque
from typing import Dict, Deque
from threading import Lock


class RateLimiter:
    """Simple in-memory rate limiter."""
    
    def __init__(self):
        self._calls: Dict[str, Deque[float]] = defaultdict(deque)
        self._lock = Lock()
    
    def is_allowed(self, key: str, max_calls: int, window_seconds: int) -> bool:
        """Check if a call is allowed within the rate limit."""
        with self._lock:
            now = time.time()
            calls = self._calls[key]
            
            while calls and calls[0] <= now - window_seconds:
                calls.popleft()
            
            if len(calls) >= max_calls:
                return False
            
            calls.append(now)
            return True
    
    def wait_time(self, key: str, max_calls: int, window_seconds: int) -> float:
        """Get the time to wait before the next call is allowed."""
        with self._lock:
            now = time.time()
            calls = self._calls[key]
            
            if len(calls) < max_calls:
                return 0.0
            
            return max(0.0, calls[0] + window_seconds - now)


rate_limiter = RateLimiter()
