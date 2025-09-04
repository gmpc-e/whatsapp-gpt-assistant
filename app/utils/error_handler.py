"""Centralized error handling utilities."""

import logging
from typing import Optional, Callable, Any
from functools import wraps


def handle_api_errors(logger: Optional[logging.Logger] = None, 
                     fallback_message: str = "An error occurred"):
    """Decorator to handle API errors gracefully."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if logger:
                    logger.error("API error in %s: %s", func.__name__, e)
                raise RuntimeError(fallback_message) from e
        return wrapper
    return decorator


def safe_execute(func: Callable, fallback: Any = None, 
                logger: Optional[logging.Logger] = None) -> Any:
    """Safely execute a function with fallback."""
    try:
        return func()
    except Exception as e:
        if logger:
            logger.error("Safe execution failed: %s", e)
        return fallback
