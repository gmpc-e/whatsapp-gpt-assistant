"""Support for recurring events in Google Calendar."""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from app.models import EventCreate


class RecurringEventHelper:
    """Helper class for creating recurring events."""
    
    @staticmethod
    def create_recurrence_rule(frequency: str, interval: int = 1, 
                             count: Optional[int] = None, 
                             until: Optional[datetime] = None) -> List[str]:
        """Create RRULE for recurring events.
        
        Args:
            frequency: DAILY, WEEKLY, MONTHLY, YEARLY
            interval: Repeat every N periods
            count: Number of occurrences
            until: End date for recurrence
        """
        rule = f"RRULE:FREQ={frequency.upper()}"
        
        if interval > 1:
            rule += f";INTERVAL={interval}"
        
        if count:
            rule += f";COUNT={count}"
        elif until:
            rule += f";UNTIL={until.strftime('%Y%m%dT%H%M%SZ')}"
        
        return [rule]
    
    @staticmethod
    def enhance_event_for_recurrence(event_body: Dict[str, Any], 
                                   recurrence_pattern: str) -> Dict[str, Any]:
        """Add recurrence to an event body."""
        if recurrence_pattern.lower() in ["daily", "weekly", "monthly", "yearly"]:
            event_body["recurrence"] = RecurringEventHelper.create_recurrence_rule(
                recurrence_pattern, interval=1, count=10
            )
        return event_body
