"""Input validation utilities for the WhatsApp assistant."""

import re
from typing import Optional
from datetime import datetime


def validate_phone_number(phone: str) -> bool:
    """Validate WhatsApp phone number format."""
    if not phone:
        return False
    pattern = r'^whatsapp:\+\d{10,15}$'
    return bool(re.match(pattern, phone))


def validate_date_string(date_str: str) -> bool:
    """Validate date string in YYYY-MM-DD format."""
    if not date_str:
        return False
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return True
    except ValueError:
        return False


def validate_time_string(time_str: str) -> bool:
    """Validate time string in HH:MM format."""
    if not time_str:
        return False
    try:
        datetime.strptime(time_str, '%H:%M')
        return True
    except ValueError:
        return False


def sanitize_text_input(text: str, max_length: int = 1000) -> str:
    """Sanitize text input by removing potentially harmful content."""
    if not text:
        return ""
    
    sanitized = ''.join(char for char in text if ord(char) >= 32 or char in '\n\r\t')
    
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length] + "..."
    
    return sanitized.strip()


def validate_event_title(title: str) -> Optional[str]:
    """Validate and sanitize event title."""
    if not title or not title.strip():
        return None
    
    sanitized = sanitize_text_input(title, max_length=200)
    return sanitized if sanitized else None
