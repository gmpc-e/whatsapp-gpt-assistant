"""End-to-end tests for webhook functionality."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from app.main import app


class TestWebhookIntegration:
    """Integration tests for webhook endpoints."""
    
    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)
    
    def test_health_endpoint(self):
        """Test health check endpoint."""
        response = self.client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert "services" in data
        assert "pending_confirmations" in data
    
    def test_debug_endpoint(self):
        """Test debug endpoint."""
        response = self.client.get("/debug")
        assert response.status_code == 200
        
        data = response.json()
        assert "timezone" in data
        assert "connectors" in data
        assert "performance" in data
    
    @patch('app.main.validate_phone_number')
    @patch('app.main.intent')
    def test_webhook_basic_message(self, mock_intent, mock_validate):
        """Test basic webhook message processing."""
        mock_validate.return_value = True
        mock_intent.parse.return_value = Mock(
            intent="GENERAL_QA",
            answer="Hello! How can I help you?"
        )
        
        form_data = {
            "From": "whatsapp:+1234567890",
            "Body": "Hello",
            "NumMedia": "0"
        }
        
        response = self.client.post("/whatsapp", data=form_data)
        assert response.status_code == 200
        assert "Hello! How can I help you?" in response.text
    
    @patch('app.main.validate_phone_number')
    @patch('app.main.intent')
    @patch('app.main.calendar')
    def test_webhook_event_list(self, mock_calendar, mock_intent, mock_validate):
        """Test event listing through webhook."""
        mock_validate.return_value = True
        mock_intent.parse.return_value = Mock(
            intent="EVENT_LIST",
            list_query=Mock(scope="day", date_hint=None)
        )
        mock_calendar.list_range.return_value = [
            {
                'summary': 'Test Event',
                'start': {'dateTime': '2024-01-01T10:00:00Z'},
                'location': 'Office'
            }
        ]
        
        form_data = {
            "From": "whatsapp:+1234567890",
            "Body": "show me events today",
            "NumMedia": "0"
        }
        
        response = self.client.post("/whatsapp", data=form_data)
        assert response.status_code == 200
        assert "Test Event" in response.text
    
    @patch('app.main.validate_phone_number')
    @patch('app.main.intent')
    @patch('app.main.tasks')
    def test_webhook_task_list(self, mock_tasks, mock_intent, mock_validate):
        """Test task listing through webhook."""
        mock_validate.return_value = True
        mock_intent.parse.return_value = Mock(
            intent="TASK_OP",
            task_op=Mock(op="list", criteria={})
        )
        mock_tasks.list.return_value = [
            {
                'title': 'Test Task',
                'status': 'needsAction',
                'due': '2024-01-01T15:00:00Z'
            }
        ]
        
        form_data = {
            "From": "whatsapp:+1234567890",
            "Body": "show me my tasks",
            "NumMedia": "0"
        }
        
        response = self.client.post("/whatsapp", data=form_data)
        assert response.status_code == 200
        assert "Test Task" in response.text
    
    def test_webhook_invalid_phone(self):
        """Test webhook with invalid phone number."""
        form_data = {
            "From": "invalid-phone",
            "Body": "Hello",
            "NumMedia": "0"
        }
        
        response = self.client.post("/whatsapp", data=form_data)
        assert response.status_code == 200
        assert "Invalid phone number" in response.text
    
    @patch('app.main.validate_phone_number')
    def test_webhook_empty_body(self, mock_validate):
        """Test webhook with empty message body."""
        mock_validate.return_value = True
        
        form_data = {
            "From": "whatsapp:+1234567890",
            "Body": "",
            "NumMedia": "0"
        }
        
        response = self.client.post("/whatsapp", data=form_data)
        assert response.status_code == 200
        assert "Send a message" in response.text
