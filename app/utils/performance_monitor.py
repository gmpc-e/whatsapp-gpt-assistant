"""Performance monitoring utilities."""

import time
import logging
from functools import wraps
from typing import Callable, Any, Optional
from collections import defaultdict, deque


class PerformanceMonitor:
    """Simple performance monitoring for API calls."""
    
    def __init__(self, max_samples: int = 100):
        self.call_times = defaultdict(lambda: deque(maxlen=max_samples))
        self.call_counts = defaultdict(int)
        self.error_counts = defaultdict(int)
        self.logger = logging.getLogger(__name__)
    
    def record_call(self, operation: str, duration: float, success: bool = True):
        """Record a timed operation."""
        self.call_times[operation].append(duration)
        self.call_counts[operation] += 1
        if not success:
            self.error_counts[operation] += 1
    
    def get_stats(self, operation: Optional[str] = None) -> dict:
        """Get performance statistics."""
        if operation:
            times = list(self.call_times[operation])
            if not times:
                return {"operation": operation, "no_data": True}
            
            return {
                "operation": operation,
                "count": self.call_counts[operation],
                "errors": self.error_counts[operation],
                "avg_time": sum(times) / len(times),
                "min_time": min(times),
                "max_time": max(times),
                "error_rate": self.error_counts[operation] / self.call_counts[operation] if self.call_counts[operation] > 0 else 0
            }
        else:
            return {
                op: self.get_stats(op) 
                for op in self.call_counts.keys()
            }
    
    def monitor(self, operation: str):
        """Decorator to monitor function performance."""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs) -> Any:
                start_time = time.time()
                success = True
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    success = False
                    raise
                finally:
                    duration = time.time() - start_time
                    self.record_call(operation, duration, success)
                    if duration > 5.0:  # Log slow operations
                        self.logger.warning("Slow operation %s: %.2fs", operation, duration)
            return wrapper
        return decorator


perf_monitor = PerformanceMonitor()
