#!/usr/bin/env python3
"""Test the enhanced connector parsing fix."""

import json
import sys
import os
from unittest.mock import Mock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

def test_enhanced_connector_parsing():
    """Test that the enhanced connector handles nested operation format correctly."""
    print("🧪 Testing Enhanced Connector Parsing Fix")
    print("=" * 50)
    
    mock_env = {
        'OPENAI_API_KEY': 'test-key',
        'TWILIO_ACCOUNT_SID': 'test-sid',
        'TWILIO_AUTH_TOKEN': 'test-token',
        'TWILIO_WHATSAPP_NUMBER': 'whatsapp:+1234567890',
        'USER_WHATSAPP_NUMBER': 'whatsapp:+0987654321',
        'GOOGLE_CREDENTIALS_FILE': 'test-creds.json',
        'TIMEZONE': 'UTC'
    }
    
    with patch.dict(os.environ, mock_env):
        try:
            from app.models import IntentResult, TaskOp, TaskItem
            from app.connectors.openai_intent_enhanced import EnhancedOpenAIIntentConnector
            
            print("✅ Successfully imported enhanced connector")
            
            mock_client = Mock()
            mock_completion = Mock()
            mock_completion.choices = [Mock()]
            
            problematic_response = {
                "intent": "TASK_OP",
                "task_op": {
                    "operation": "create",
                    "description": "shopping"
                },
                "answer": "I've created a task for you to do shopping."
            }
            
            mock_completion.choices[0].message.content = json.dumps(problematic_response)
            mock_client.chat.completions.create.return_value = mock_completion
            
            logger = Mock()
            connector = EnhancedOpenAIIntentConnector(mock_client, logger=logger, debug=True)
            
            result = connector.parse("create a task to do shopping")
            
            print(f"Parsed result intent: {result.intent}")
            print(f"Parsed result answer: {result.answer}")
            
            if hasattr(result, 'task_op') and result.task_op and hasattr(result.task_op, 'op'):
                print(f"✅ Result has task_op: {result.task_op.op}")
            else:
                print("❌ Result missing task_op or op field")
                return False
                
            if hasattr(result, 'task') and result.task and hasattr(result.task, 'title'):
                print(f"✅ Result has task: {result.task.title}")
                if result.task.title == "shopping":
                    print("✅ Task title correctly extracted from 'description' field")
                else:
                    print(f"❌ Task title incorrect: expected 'shopping', got '{result.task.title}'")
                    return False
            else:
                print("❌ Result missing task or title field")
                return False
            
            print("✅ Enhanced connector parsing fix test PASSED")
            return True
            
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    success = test_enhanced_connector_parsing()
    print(f"\n{'✅ SUCCESS' if success else '❌ FAILED'}: Enhanced connector parsing fix")
    sys.exit(0 if success else 1)
