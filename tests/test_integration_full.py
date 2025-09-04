"""Comprehensive integration tests for enhanced features."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.connectors.enhanced_nlp import EnhancedNLPProcessor


class TestEnhancedIntegration:
    """Full integration tests for enhanced NLP and task management."""
    
    def setup_method(self):
        """Set up test client and mocks."""
        self.client = TestClient(app)
        self.nlp = EnhancedNLPProcessor()
    
    @patch('app.main.validate_phone_number')
    @patch('app.main.intent')
    @patch('app.main.calendar')
    def test_next_week_events_query(self, mock_calendar, mock_intent, mock_validate):
        """Test 'show me events next week' query."""
        mock_validate.return_value = True
        mock_intent.parse.return_value = Mock(
            intent="EVENT_LIST",
            list_query=Mock(scope="week", date_hint=None)
        )
        
        next_week_events = [
            {
                'summary': 'Team Meeting',
                'start': {'dateTime': (datetime.now() + timedelta(days=7)).isoformat()},
                'location': 'Conference Room'
            },
            {
                'summary': 'Project Review',
                'start': {'dateTime': (datetime.now() + timedelta(days=9)).isoformat()},
                'location': 'Office'
            }
        ]
        mock_calendar.list_range.return_value = next_week_events
        
        form_data = {
            "From": "whatsapp:+1234567890",
            "Body": "show me events next week",
            "NumMedia": "0"
        }
        
        response = self.client.post("/whatsapp", data=form_data)
        assert response.status_code == 200
        assert "Team Meeting" in response.text
        assert "Project Review" in response.text
    
    @patch('app.main.validate_phone_number')
    @patch('app.main.intent')
    @patch('app.main.calendar')
    def test_free_slots_query(self, mock_calendar, mock_intent, mock_validate):
        """Test 'show me free slots next week' query."""
        mock_validate.return_value = True
        mock_intent.parse.return_value = Mock(
            intent="EVENT_LIST",
            list_query=Mock(scope="week", date_hint=None)
        )
        
        busy_events = [
            {
                'summary': 'Busy Meeting',
                'start': {'dateTime': (datetime.now() + timedelta(days=7, hours=10)).isoformat()},
                'end': {'dateTime': (datetime.now() + timedelta(days=7, hours=11)).isoformat()}
            }
        ]
        mock_calendar.list_range.return_value = busy_events
        
        form_data = {
            "From": "whatsapp:+1234567890",
            "Body": "show me free slots next week for the beach",
            "NumMedia": "0"
        }
        
        response = self.client.post("/whatsapp", data=form_data)
        assert response.status_code == 200
        assert "Free time slots" in response.text or "free" in response.text.lower()
    
    @patch('app.main.validate_phone_number')
    @patch('app.main.intent')
    @patch('app.main.tasks')
    def test_open_tasks_query(self, mock_tasks, mock_intent, mock_validate):
        """Test 'show me open tasks' query."""
        mock_validate.return_value = True
        mock_intent.parse.return_value = Mock(
            intent="TASK_OP",
            task_op=Mock(op="list", criteria={})
        )
        
        task_list = [
            {
                'title': 'Complete project',
                'status': 'needsAction',
                'due': (datetime.now() + timedelta(days=2)).isoformat() + 'Z'
            },
            {
                'title': 'Review documents',
                'status': 'completed',
                'due': (datetime.now() - timedelta(days=1)).isoformat() + 'Z'
            },
            {
                'title': 'Call client',
                'status': 'needsAction',
                'due': None
            }
        ]
        mock_tasks.list.return_value = task_list
        
        form_data = {
            "From": "whatsapp:+1234567890",
            "Body": "show me open tasks",
            "NumMedia": "0"
        }
        
        response = self.client.post("/whatsapp", data=form_data)
        assert response.status_code == 200
        assert "Complete project" in response.text
        assert "Call client" in response.text
        assert "Review documents" not in response.text  # Should be filtered out (completed)
    
    @patch('app.main.validate_phone_number')
    @patch('app.main.intent')
    @patch('app.main.tasks')
    def test_completed_tasks_query(self, mock_tasks, mock_intent, mock_validate):
        """Test 'show me completed tasks' query."""
        mock_validate.return_value = True
        mock_intent.parse.return_value = Mock(
            intent="TASK_OP",
            task_op=Mock(op="list", criteria={})
        )
        
        task_list = [
            {
                'title': 'Finished task',
                'status': 'completed',
                'due': (datetime.now() - timedelta(days=1)).isoformat() + 'Z'
            },
            {
                'title': 'Another done task',
                'status': 'completed',
                'due': None
            },
            {
                'title': 'Still pending',
                'status': 'needsAction',
                'due': None
            }
        ]
        mock_tasks.list.return_value = task_list
        
        form_data = {
            "From": "whatsapp:+1234567890",
            "Body": "show me completed tasks",
            "NumMedia": "0"
        }
        
        response = self.client.post("/whatsapp", data=form_data)
        assert response.status_code == 200
        assert "Finished task" in response.text
        assert "Another done task" in response.text
        assert "Still pending" not in response.text  # Should be filtered out (not completed)
    
    @patch('app.main.validate_phone_number')
    @patch('app.main.intent')
    @patch('app.main.tasks')
    def test_task_creation_with_datetime(self, mock_tasks, mock_intent, mock_validate):
        """Test task creation with date and time."""
        mock_validate.return_value = True
        mock_intent.parse.return_value = Mock(
            intent="TASK_OP",
            task_op=Mock(op="create", criteria={}),
            task=Mock(
                title="Buy groceries",
                date="2024-01-15",
                time="14:00",
                notes="Don't forget milk",
                location="Supermarket"
            )
        )
        
        mock_tasks.create.return_value = {
            'title': 'Buy groceries',
            'id': 'task123'
        }
        
        form_data = {
            "From": "whatsapp:+1234567890",
            "Body": "create task: Buy groceries on January 15th at 2pm, location supermarket, note: don't forget milk",
            "NumMedia": "0"
        }
        
        response = self.client.post("/whatsapp", data=form_data)
        assert response.status_code == 200
        assert "Task created" in response.text
        assert "Buy groceries" in response.text
        
        mock_tasks.create.assert_called_once()
        call_args = mock_tasks.create.call_args[0][0]
        assert call_args['title'] == "Buy groceries"
    
    @patch('app.main.validate_phone_number')
    @patch('app.main.intent')
    @patch('app.main.calendar')
    @patch('app.main.tasks')
    def test_summary_statistics_query(self, mock_tasks, mock_calendar, mock_intent, mock_validate):
        """Test comprehensive summary with statistics."""
        mock_validate.return_value = True
        mock_intent.parse.return_value = Mock(
            intent="EVENT_LIST",
            list_query=Mock(scope="week", date_hint=None)
        )
        
        events = [
            {
                'summary': 'Meeting 1',
                'start': {'dateTime': datetime.now().isoformat()}
            },
            {
                'summary': 'Meeting 2',
                'start': {'dateTime': (datetime.now() + timedelta(hours=2)).isoformat()}
            }
        ]
        mock_calendar.list_range.return_value = events
        
        tasks = [
            {'title': 'Task 1', 'status': 'needsAction'},
            {'title': 'Task 2', 'status': 'completed'},
            {'title': 'Task 3', 'status': 'needsAction'}
        ]
        mock_tasks.list.return_value = tasks
        
        form_data = {
            "From": "whatsapp:+1234567890",
            "Body": "give me a summary of this week with statistics",
            "NumMedia": "0"
        }
        
        response = self.client.post("/whatsapp", data=form_data)
        assert response.status_code == 200
        assert "Summary" in response.text
        assert "Events (2)" in response.text
        assert "Open: 2" in response.text
        assert "Completed: 1" in response.text
    
    def test_nlp_date_parsing_accuracy(self):
        """Test NLP date parsing for various natural language inputs."""
        test_cases = [
            ("tomorrow", 1),
            ("next week", 7),
            ("next sunday", None),  # Variable based on current day
            ("today", 0)
        ]
        
        for text, expected_days in test_cases:
            start, end = self.nlp.parse_date_range(f"show me events {text}")
            
            if expected_days is not None:
                actual_days = (start.date() - datetime.now(self.nlp.timezone).date()).days
                assert actual_days == expected_days, f"Failed for '{text}': expected {expected_days}, got {actual_days}"
            
            assert start < end, f"Invalid date range for '{text}'"
    
    def test_task_status_filtering(self):
        """Test task status filtering logic."""
        test_cases = [
            ("show me open tasks", "open"),
            ("list completed tasks", "completed"),
            ("show all my tasks", "all"),
            ("what are my pending items", "open"),
            ("display finished tasks", "completed")
        ]
        
        for text, expected_status in test_cases:
            actual_status = self.nlp.extract_task_status_filter(text)
            assert actual_status == expected_status, f"Failed for '{text}': expected {expected_status}, got {actual_status}"
    
    @patch('app.main.validate_phone_number')
    def test_error_handling_invalid_input(self, mock_validate):
        """Test error handling for invalid inputs."""
        mock_validate.return_value = True
        
        form_data = {
            "From": "whatsapp:+1234567890",
            "Body": "",
            "NumMedia": "0"
        }
        
        response = self.client.post("/whatsapp", data=form_data)
        assert response.status_code == 200
        assert "Send a message" in response.text
        
        mock_validate.return_value = False
        form_data["Body"] = "Hello"
        
        response = self.client.post("/whatsapp", data=form_data)
        assert response.status_code == 200
        assert "Invalid phone number" in response.text
    
    @patch('app.main.validate_phone_number')
    @patch('app.main.intent')
    def test_rate_limiting_behavior(self, mock_intent, mock_validate):
        """Test rate limiting behavior."""
        mock_validate.return_value = True
        
        mock_intent.parse.return_value = Mock(
            intent="GENERAL_QA",
            answer="I'm processing too many requests right now. Please try again in a moment."
        )
        
        form_data = {
            "From": "whatsapp:+1234567890",
            "Body": "Hello",
            "NumMedia": "0"
        }
        
        response = self.client.post("/whatsapp", data=form_data)
        assert response.status_code == 200
        assert "too many requests" in response.text.lower()
