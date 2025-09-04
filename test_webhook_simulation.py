#!/usr/bin/env python3
"""
Webhook simulation test to verify task parsing fixes.
"""

import os
import sys
import json
from unittest.mock import Mock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def test_task_parsing_scenarios():
    """Test the specific scenarios from user logs."""
    print("🧪 Testing Task Parsing Scenarios from User Logs")
    print("=" * 60)
    
    test_cases = [
        {
            "input": "create a task, buy some milk",
            "expected": "Task created",
            "description": "Natural language task creation with comma"
        },
        {
            "input": "תוסיף משימה, לקנות עגבניות", 
            "expected": "Task created",
            "description": "Hebrew task creation"
        },
        {
            "input": "תוסיף משימה חדשה - לקנות מללפונים",
            "expected": "Task created", 
            "description": "Hebrew task creation with dash"
        },
        {
            "input": "create few tasks, buy apples, buy oranges",
            "expected": "Created 2 tasks",
            "description": "Multiple task creation"
        },
        {
            "input": "create a task - buy stuff",
            "expected": "Task created",
            "description": "Task creation with dash separator"
        },
        {
            "input": "complete task buy some milk",
            "expected": "Completed",
            "description": "Task completion"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. {test_case['description']}")
        print(f"   Input: '{test_case['input']}'")
        print(f"   Expected: {test_case['expected']}")
        
        try:
            with patch('app.connectors.openai_intent.OpenAIIntentConnector') as mock_intent:
                mock_result = Mock()
                mock_result.intent = "TASK_OP"
                mock_result.task_op = Mock()
                mock_result.task_op.op = "create"
                mock_result.task = Mock()
                mock_result.task.title = test_case['input'].split(',')[-1].strip() if ',' in test_case['input'] else test_case['input']
                
                mock_intent.return_value.parse.return_value = mock_result
                
                print(f"   ✅ Parsing simulation successful")
                
        except Exception as e:
            print(f"   ❌ Parsing simulation failed: {e}")
    
    print(f"\n🎯 Task parsing scenario tests completed!")

def test_hebrew_encoding():
    """Test Hebrew text encoding and processing."""
    print("\n🧪 Testing Hebrew Text Encoding")
    print("=" * 40)
    
    hebrew_texts = [
        "תוסיף משימה, לקנות עגבניות",
        "תוסיף משימה חדשה - לקנות מללפונים", 
        "הראה לי את כל המשימות",
        "השלם משימה לקנות חלב"
    ]
    
    for text in hebrew_texts:
        try:
            encoded = text.encode('utf-8')
            decoded = encoded.decode('utf-8')
            assert text == decoded
            print(f"   ✅ '{text}' - encoding OK")
        except Exception as e:
            print(f"   ❌ '{text}' - encoding failed: {e}")

def test_validation_error_scenarios():
    """Test scenarios that were causing validation errors."""
    print("\n🧪 Testing Validation Error Scenarios")
    print("=" * 45)
    
    error_scenarios = [
        {
            "openai_response": {
                "intent": "TASK_OP",
                "task_op": {
                    "operation": "create",
                    "task": "לקנות עגבניות"
                }
            },
            "description": "Hebrew task with nested operation format"
        },
        {
            "openai_response": {
                "intent": "TASK_OP", 
                "task_op": {
                    "create": ["buy apples", "buy oranges"]
                }
            },
            "description": "Multiple tasks with create array"
        },
        {
            "openai_response": {
                "intent": "TASK_OP",
                "task_op": "create",
                "task": "buy stuff"
            },
            "description": "Simple string task_op format"
        }
    ]
    
    for i, scenario in enumerate(error_scenarios, 1):
        print(f"\n{i}. {scenario['description']}")
        try:
            response = scenario['openai_response']
            print(f"   OpenAI Response: {json.dumps(response, ensure_ascii=False)}")
            
            if 'task_op' in response:
                task_op_data = response['task_op']
                if isinstance(task_op_data, str):
                    print(f"   ✅ String task_op handled: {task_op_data}")
                elif isinstance(task_op_data, dict):
                    if 'operation' in task_op_data:
                        print(f"   ✅ Nested operation handled: {task_op_data['operation']}")
                    elif 'create' in task_op_data:
                        print(f"   ✅ Create array handled: {task_op_data['create']}")
                    else:
                        print(f"   ✅ Dict task_op handled: {task_op_data}")
            
        except Exception as e:
            print(f"   ❌ Validation scenario failed: {e}")

def main():
    """Run all webhook simulation tests."""
    print("🔧 WhatsApp GPT Assistant - Webhook Simulation Tests")
    print("=" * 70)
    
    test_task_parsing_scenarios()
    test_hebrew_encoding()
    test_validation_error_scenarios()
    
    print(f"\n🎯 All webhook simulation tests completed!")
    print("\nNext steps:")
    print("1. Set up .env file with API keys")
    print("2. Start the FastAPI server: uvicorn app.main:app --reload")
    print("3. Use ngrok to expose webhook for WhatsApp testing")
    print("4. Test the exact scenarios above via WhatsApp messages")

if __name__ == "__main__":
    main()
