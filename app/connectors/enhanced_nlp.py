"""Enhanced natural language processing for calendar and task queries."""

import re
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Tuple, Any
from zoneinfo import ZoneInfo
from app.config import settings


class EnhancedNLPProcessor:
    """Enhanced NLP for better calendar and task understanding."""
    
    def __init__(self):
        self.timezone = ZoneInfo(settings.TIMEZONE)
        
        self.time_patterns = {
            'today': 0,
            'tomorrow': 1,
            'yesterday': -1,
            'next week': 7,
            'this week': 0,
            'next month': 30,
            'this month': 0,
        }
        
        self.day_patterns = {
            'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
            'friday': 4, 'saturday': 5, 'sunday': 6,
            'mon': 0, 'tue': 1, 'wed': 2, 'thu': 3,
            'fri': 4, 'sat': 5, 'sun': 6
        }
        
        self.task_status_patterns = {
            'open': ['open', 'pending', 'todo', 'incomplete', 'active'],
            'completed': ['completed', 'done', 'finished', 'closed'],
            'all': ['all', 'everything', 'any']
        }
    
    def parse_date_range(self, text: str) -> Tuple[datetime, datetime]:
        """Parse natural language date ranges."""
        text_lower = text.lower()
        now = datetime.now(self.timezone)
        today = now.date()
        
        if 'next sunday' in text_lower:
            days_ahead = 6 - today.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            target_date = today + timedelta(days=days_ahead)
            start = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=self.timezone)
            end = start + timedelta(days=1)
            return start, end
        
        if 'next week' in text_lower:
            days_until_monday = 7 - today.weekday()
            next_monday = today + timedelta(days=days_until_monday)
            start = datetime.combine(next_monday, datetime.min.time()).replace(tzinfo=self.timezone)
            end = start + timedelta(days=7)
            return start, end
        
        if 'this week' in text_lower:
            days_since_monday = today.weekday()
            this_monday = today - timedelta(days=days_since_monday)
            start = datetime.combine(this_monday, datetime.min.time()).replace(tzinfo=self.timezone)
            end = start + timedelta(days=7)
            return start, end
        
        if 'tomorrow' in text_lower:
            tomorrow = today + timedelta(days=1)
            start = datetime.combine(tomorrow, datetime.min.time()).replace(tzinfo=self.timezone)
            end = start + timedelta(days=1)
            return start, end
        
        if 'today' in text_lower:
            start = datetime.combine(today, datetime.min.time()).replace(tzinfo=self.timezone)
            end = start + timedelta(days=1)
            return start, end
        
        start = datetime.combine(today, datetime.min.time()).replace(tzinfo=self.timezone)
        end = start + timedelta(days=1)
        return start, end
    
    def extract_task_status_filter(self, text: str) -> Optional[str]:
        """Extract task status filter from text."""
        text_lower = text.lower()
        
        for status, patterns in self.task_status_patterns.items():
            if any(pattern in text_lower for pattern in patterns):
                return status
        
        return None
    
    def find_free_slots(self, events: List[Dict], start_date: datetime, 
                       end_date: datetime, duration_hours: int = 2) -> List[Dict]:
        """Find free time slots between events."""
        if not events:
            return [{
                'start': start_date,
                'end': end_date,
                'duration_hours': (end_date - start_date).total_seconds() / 3600,
                'suggestion': f"Entire period is free ({duration_hours}+ hours available)"
            }]
        
        sorted_events = sorted(events, key=lambda e: self._parse_event_time(e.get('start', {})) or datetime.min.replace(tzinfo=self.timezone))
        
        free_slots = []
        current_time = start_date
        
        for event in sorted_events:
            event_start = self._parse_event_time(event.get('start', {}))
            if event_start and current_time < event_start:
                slot_duration = (event_start - current_time).total_seconds() / 3600
                if slot_duration >= duration_hours:
                    free_slots.append({
                        'start': current_time,
                        'end': event_start,
                        'duration_hours': slot_duration,
                        'suggestion': f"Free slot: {current_time.strftime('%a %H:%M')} - {event_start.strftime('%H:%M')}"
                    })
            
            event_end = self._parse_event_time(event.get('end', {}))
            if event_end:
                current_time = max(current_time, event_end)
        
        if current_time < end_date:
            slot_duration = (end_date - current_time).total_seconds() / 3600
            if slot_duration >= duration_hours:
                free_slots.append({
                    'start': current_time,
                    'end': end_date,
                    'duration_hours': slot_duration,
                    'suggestion': f"Free slot: {current_time.strftime('%a %H:%M')} - {end_date.strftime('%H:%M')}"
                })
        
        return free_slots
    
    def _parse_event_time(self, time_obj: Dict) -> Optional[datetime]:
        """Parse event time from Google Calendar format."""
        if not time_obj:
            return None
        
        time_str = time_obj.get('dateTime') or time_obj.get('date')
        if not time_str:
            return None
        
        try:
            if 'T' in time_str:
                return datetime.fromisoformat(time_str.replace('Z', '+00:00')).astimezone(self.timezone)
            else:
                return datetime.combine(
                    date.fromisoformat(time_str), 
                    datetime.min.time()
                ).replace(tzinfo=self.timezone)
        except Exception:
            return None
    
    def generate_summary(self, events: List[Dict], tasks: List[Dict], 
                        period_name: str = "this period") -> str:
        """Generate a comprehensive summary of events and tasks."""
        summary_parts = [f"📊 Summary for {period_name}:"]
        
        if events:
            summary_parts.append(f"\n🗓️ Events ({len(events)}):")
            for event in events[:5]:  # Show first 5
                title = event.get('summary', 'Untitled')
                start_time = self._format_event_time(event.get('start', {}))
                summary_parts.append(f"  • {start_time} - {title}")
            
            if len(events) > 5:
                summary_parts.append(f"  ... and {len(events) - 5} more events")
        else:
            summary_parts.append(f"\n🗓️ No events scheduled for {period_name}")
        
        if tasks:
            open_tasks = [t for t in tasks if t.get('status') != 'completed']
            completed_tasks = [t for t in tasks if t.get('status') == 'completed']
            
            summary_parts.append(f"\n🧩 Tasks:")
            summary_parts.append(f"  • Open: {len(open_tasks)}")
            summary_parts.append(f"  • Completed: {len(completed_tasks)}")
            
            if open_tasks:
                summary_parts.append("  Top open tasks:")
                for task in open_tasks[:3]:
                    title = task.get('title', 'Untitled')
                    due = task.get('due')
                    due_str = f" (due {self._format_task_due(due)})" if due else ""
                    summary_parts.append(f"    - {title}{due_str}")
        else:
            summary_parts.append(f"\n🧩 No tasks found")
        
        return "\n".join(summary_parts)
    
    def _format_event_time(self, time_obj: Dict) -> str:
        """Format event time for display."""
        parsed_time = self._parse_event_time(time_obj)
        if not parsed_time:
            return "No time"
        
        if time_obj.get('date'):  # All-day event
            return parsed_time.strftime('%a %m/%d')
        else:
            return parsed_time.strftime('%a %m/%d %H:%M')
    
    def _format_task_due(self, due_str: Optional[str]) -> str:
        """Format task due date for display."""
        if not due_str:
            return ""
        
        try:
            if due_str.endswith('Z'):
                due_dt = datetime.fromisoformat(due_str.replace('Z', '+00:00'))
            else:
                due_dt = datetime.fromisoformat(due_str)
            
            due_local = due_dt.astimezone(self.timezone)
            return due_local.strftime('%m/%d %H:%M')
        except Exception:
            return due_str
