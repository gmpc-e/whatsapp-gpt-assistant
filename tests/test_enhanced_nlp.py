"""Tests for enhanced NLP processing."""

import pytest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from app.connectors.enhanced_nlp import EnhancedNLPProcessor


class TestEnhancedNLPProcessor:
    """Test cases for enhanced NLP processing."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.nlp = EnhancedNLPProcessor()
        self.timezone = ZoneInfo("Asia/Jerusalem")
    
    def test_parse_date_range_tomorrow(self):
        """Test parsing 'tomorrow' date range."""
        start, end = self.nlp.parse_date_range("show me events tomorrow")
        
        expected_start = datetime.now(self.timezone).date() + timedelta(days=1)
        assert start.date() == expected_start
        assert (end - start).days == 1
    
    def test_parse_date_range_next_week(self):
        """Test parsing 'next week' date range."""
        start, end = self.nlp.parse_date_range("events next week")
        
        assert start.weekday() == 0  # Monday
        assert (end - start).days == 7
    
    def test_parse_date_range_next_sunday(self):
        """Test parsing 'next Sunday' date range."""
        start, end = self.nlp.parse_date_range("events next sunday")
        
        assert start.weekday() == 6  # Sunday
        assert (end - start).days == 1
    
    def test_extract_task_status_filter(self):
        """Test extracting task status filters."""
        assert self.nlp.extract_task_status_filter("show me open tasks") == "open"
        assert self.nlp.extract_task_status_filter("completed tasks") == "completed"
        assert self.nlp.extract_task_status_filter("all my tasks") == "all"
        assert self.nlp.extract_task_status_filter("random text") is None
    
    def test_find_free_slots_empty_calendar(self):
        """Test finding free slots with no events."""
        start = datetime.now(self.timezone)
        end = start + timedelta(hours=8)
        
        free_slots = self.nlp.find_free_slots([], start, end, duration_hours=2)
        
        assert len(free_slots) == 1
        assert free_slots[0]['duration_hours'] == 8
    
    def test_find_free_slots_with_events(self):
        """Test finding free slots between events."""
        start = datetime.now(self.timezone).replace(hour=9, minute=0, second=0, microsecond=0)
        end = start.replace(hour=17)  # 9 AM to 5 PM
        
        events = [
            {
                'start': {'dateTime': start.replace(hour=10).isoformat()},
                'end': {'dateTime': start.replace(hour=11).isoformat()}
            },
            {
                'start': {'dateTime': start.replace(hour=14).isoformat()},
                'end': {'dateTime': start.replace(hour=15).isoformat()}
            }
        ]
        
        free_slots = self.nlp.find_free_slots(events, start, end, duration_hours=2)
        
        assert len(free_slots) >= 2  # At least the longer slots
        
        long_slots = [slot for slot in free_slots if slot['duration_hours'] >= 2]
        assert len(long_slots) >= 2
    
    def test_generate_summary(self):
        """Test generating comprehensive summaries."""
        events = [
            {
                'summary': 'Team Meeting',
                'start': {'dateTime': datetime.now(self.timezone).isoformat()}
            }
        ]
        
        tasks = [
            {'title': 'Complete report', 'status': 'needsAction'},
            {'title': 'Review code', 'status': 'completed'}
        ]
        
        summary = self.nlp.generate_summary(events, tasks, "today")
        
        assert "Summary for today" in summary
        assert "Events (1)" in summary
        assert "Team Meeting" in summary
        assert "Open: 1" in summary
        assert "Completed: 1" in summary
