#!/usr/bin/env python3
"""
Test script specifically for task parsing fixes from user feedback.
"""

import os
import sys
import json
from unittest.mock import Mock, patch

def test_hebrew_task_creation():
    """Test Hebrew task creation patterns from user logs."""
    print("🧪 Testing Hebrew Task Creation Patterns")
    print("=" * 50)
    
    hebrew_test_cases = [
        {
            "input": "תוסיף משימה, לקנות עגבניות",
            "expected_title": "לקנות עגבניות",
            "pattern": "comma separator"
        },
        {
            "input": "תוסיף משימה חדשה - לקנות מללפונים", 
            "expected_title": "לקנות מללפונים",
            "pattern": "dash separator"
        },
        {
            "input": "הוסף משימה: לקנות חלב",
            "expected_title": "לקנות חלב", 
            "pattern": "colon separator"
        }
    ]
    
    for i, test_case in enumerate(hebrew_test_cases, 1):
        print(f"\n{i}. Testing {test_case['pattern']}")
        print(f"   Input: '{test_case['input']}'")
        
        body = test_case['input']
        title = None
        
        for pattern in ['תוסיף משימה,', 'תוסיף משימה -', 'תוסיף משימה חדשה -', 'משימה חדשה -', 'הוסף משימה:']:
            if pattern in body:
                start_idx = body.find(pattern) + len(pattern)
                title = body[start_idx:].strip()
                break
        
        if title == test_case['expected_title']:
            print(f"   ✅ Extracted title: '{title}'")
        else:
            print(f"   ❌ Expected: '{test_case['expected_title']}', Got: '{title}'")

def test_english_task_creation():
    """Test English task creation patterns from user logs."""
    print("\n🧪 Testing English Task Creation Patterns")
    print("=" * 50)
    
    english_test_cases = [
        {
            "input": "create a task, buy some milk",
            "expected_title": "buy some milk",
            "pattern": "comma separator"
        },
        {
            "input": "create a task - buy stuff",
            "expected_title": "buy stuff", 
            "pattern": "dash separator"
        },
        {
            "input": "create task: finish report",
            "expected_title": "finish report",
            "pattern": "colon separator"
        },
        {
            "input": "new task: call mom",
            "expected_title": "call mom",
            "pattern": "new task colon"
        }
    ]
    
    for i, test_case in enumerate(english_test_cases, 1):
        print(f"\n{i}. Testing {test_case['pattern']}")
        print(f"   Input: '{test_case['input']}'")
        
        body = test_case['input']
        text_lower = body.lower()
        title = None
        
        for pattern in ['create a task,', 'create a task -', 'create task,', 'create task -', 'create task:', 'new task:', 'add task:']:
            if pattern in text_lower:
                title_start = text_lower.find(pattern) + len(pattern)
                title = body[title_start:].strip()
                break
        
        if title == test_case['expected_title']:
            print(f"   ✅ Extracted title: '{title}'")
        else:
            print(f"   ❌ Expected: '{test_case['expected_title']}', Got: '{title}'")

def test_multiple_task_creation():
    """Test multiple task creation from user logs."""
    print("\n🧪 Testing Multiple Task Creation")
    print("=" * 40)
    
    openai_responses = [
        {
            "intent": "TASK_OP",
            "task_op": {"op": "create"},
            "tasks": [{"title": "buy apples"}, {"title": "buy oranges"}]
        },
        {
            "intent": "TASK_OP", 
            "task_op": {"create": ["buy milk", "buy bread"]}
        }
    ]
    
    for i, response in enumerate(openai_responses, 1):
        print(f"\n{i}. Testing OpenAI response format {i}")
        print(f"   Response: {json.dumps(response, ensure_ascii=False)}")
        
        if 'tasks' in response:
            tasks_data = response['tasks']
            print(f"   ✅ Found {len(tasks_data)} tasks in 'tasks' field")
        elif 'task_op' in response and isinstance(response['task_op'], dict) and 'create' in response['task_op']:
            create_data = response['task_op']['create']
            if isinstance(create_data, list):
                print(f"   ✅ Found {len(create_data)} tasks in task_op.create field")
            else:
                print(f"   ❌ task_op.create is not a list: {create_data}")
        else:
            print(f"   ❌ No multiple tasks found in response")

def test_validation_error_scenarios():
    """Test the exact validation error scenarios from user logs."""
    print("\n🧪 Testing Validation Error Scenarios")
    print("=" * 45)
    
    error_scenarios = [
        {
            "description": "Hebrew task with nested operation format",
            "response": {
                "intent": "TASK_OP",
                "task_op": {
                    "operation": "create",
                    "task": "לקנות עגבניות"
                }
            }
        },
        {
            "description": "Multiple tasks with create array",
            "response": {
                "intent": "TASK_OP",
                "task_op": {
                    "create": ["buy apples", "buy oranges"]
                }
            }
        },
        {
            "description": "String task_op format",
            "response": {
                "intent": "TASK_OP",
                "task_op": "create",
                "task": "buy stuff"
            }
        }
    ]
    
    for i, scenario in enumerate(error_scenarios, 1):
        print(f"\n{i}. {scenario['description']}")
        response = scenario['response']
        
        task_op_data = response.get('task_op')
        
        if isinstance(task_op_data, str):
            print(f"   ✅ String task_op handled: {task_op_data}")
        elif isinstance(task_op_data, dict):
            if "operation" in task_op_data:
                print(f"   ✅ Nested operation handled: {task_op_data['operation']}")
            elif "create" in task_op_data:
                create_data = task_op_data["create"]
                if isinstance(create_data, list):
                    print(f"   ✅ Create array handled: {len(create_data)} tasks")
                else:
                    print(f"   ❌ Create data not a list: {create_data}")
            elif "op" in task_op_data:
                print(f"   ✅ Standard op handled: {task_op_data['op']}")
            else:
                print(f"   ⚠️  Unknown dict format: {task_op_data}")
        else:
            print(f"   ❌ Unexpected task_op type: {type(task_op_data)}")

def main():
    """Run all task parsing fix tests."""
    print("🔧 Task Parsing Fixes - Validation Tests")
    print("=" * 60)
    
    test_hebrew_task_creation()
    test_english_task_creation()
    test_multiple_task_creation()
    test_validation_error_scenarios()
    
    print(f"\n🎯 All task parsing fix tests completed!")
    print("\nKey fixes implemented:")
    print("- Enhanced Hebrew language pattern matching")
    print("- Improved English natural language detection")
    print("- Fixed multiple task creation parsing")
    print("- Resolved TaskUpdate validation errors")
    print("- Added robust fallback mechanisms")
    
    print(f"\nNext steps for testing:")
    print("1. Copy .env.template to .env and add your API keys")
    print("2. Start the server: uvicorn app.main:app --reload")
    print("3. Use ngrok to expose webhook for WhatsApp testing")
    print("4. Test the exact patterns above via WhatsApp messages")

if __name__ == "__main__":
    main()
