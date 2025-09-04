#!/usr/bin/env python3
"""
Test the webhook parsing fix for the specific user error.
Simulates the webhook request without requiring full environment setup.
"""

import json
import sys
import os
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

def test_webhook_parsing_fix():
    """Test that the webhook parsing fix resolves the TaskUpdate validation error."""
    print("🧪 Testing Webhook Parsing Fix")
    print("=" * 40)
    
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
            from app.connectors.openai_intent import OpenAIIntentConnector
            
            print("✅ Successfully imported models and connector")
            
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
            connector = OpenAIIntentConnector(mock_client, logger, debug=True)
            
            print(f"Testing OpenAI response: {json.dumps(problematic_response, indent=2)}")
            
            result = connector.parse("create a task to do shopping")
            
            print(f"Parsed result intent: {result.intent}")
            print(f"Parsed result answer: {result.answer}")
            
            if hasattr(result, 'task_op') and result.task_op:
                print(f"✅ Result has task_op: {result.task_op.op}")
            else:
                print("❌ Result missing task_op")
                return False
                
            if hasattr(result, 'task') and result.task:
                print(f"✅ Result has task: {result.task.title}")
            else:
                print("❌ Result missing task")
                return False
            
            if hasattr(result, 'task_update') and result.task_update:
                print("❌ Unexpected task_update field found")
                return False
            else:
                print("✅ No task_update field (correct)")
            
            if result.task and result.task.title == "shopping":
                print("✅ Task title correctly extracted from 'description' field")
            else:
                print(f"❌ Task title incorrect: expected 'shopping', got '{result.task.title if result.task else None}'")
                return False
            
            print("✅ Webhook parsing fix test PASSED")
            return True
            
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            import traceback
            traceback.print_exc()
            return False

def test_system_prompt_improvement():
    """Test that the system prompt improvements work."""
    print("\n🧪 Testing System Prompt Improvements")
    print("=" * 40)
    
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
            from app.connectors.openai_intent import SYSTEM_PROMPT
            
            if "NEVER use 'description' field - always use 'title'" in SYSTEM_PROMPT:
                print("✅ System prompt includes description field warning")
            else:
                print("❌ System prompt missing description field warning")
                return False
            
            if "'create a task to do shopping' ->" in SYSTEM_PROMPT:
                print("✅ System prompt includes specific example")
            else:
                print("❌ System prompt missing specific example")
                return False
            
            if '"title":"do shopping"' in SYSTEM_PROMPT:
                print("✅ System prompt example uses 'title' field correctly")
            else:
                print("❌ System prompt example doesn't use 'title' field")
                return False
            
            print("✅ System prompt improvements test PASSED")
            return True
            
        except Exception as e:
            print(f"❌ System prompt test failed: {e}")
            return False

def main():
    """Run all webhook parsing fix tests."""
    print("🔧 Testing Webhook Parsing Fix for User Error")
    print("=" * 60)
    
    success = True
    
    if not test_webhook_parsing_fix():
        success = False
    
    if not test_system_prompt_improvement():
        success = False
    
    if success:
        print(f"\n🎯 All webhook parsing fix tests PASSED!")
        print("\nKey fixes verified:")
        print("✅ Nested {'operation': 'create', 'description': 'shopping'} format handled")
        print("✅ TaskItem created from 'description' field in nested format")
        print("✅ TaskOp created from 'operation' field")
        print("✅ No TaskUpdate validation attempted")
        print("✅ System prompt improved to prefer 'title' over 'description'")
        
        print(f"\nThe user's error should now be resolved:")
        print("- 'create a task to do shopping' will work correctly")
        print("- No more TaskUpdate validation errors")
        print("- Task will be created with title 'shopping'")
    else:
        print(f"\n❌ Some tests FAILED - parsing fix needs more work")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
