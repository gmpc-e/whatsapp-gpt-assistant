#!/usr/bin/env python3
"""
Test the specific parsing issue from user's error log.
"""

import json
from unittest.mock import Mock

def test_nested_operation_parsing():
    """Test the exact OpenAI response format that's causing the error."""
    print("🧪 Testing Nested Operation Parsing Issue")
    print("=" * 50)
    
    openai_response = {
        "intent": "TASK_OP",
        "task_op": {
            "operation": "create",
            "description": "shopping"
        },
        "answer": "I've created a task for you to do shopping."
    }
    
    print(f"OpenAI Response: {json.dumps(openai_response, indent=2)}")
    
    data = openai_response
    task_op_data = data.get("task_op")
    
    print(f"\nParsing task_op_data: {task_op_data}")
    print(f"Type: {type(task_op_data)}")
    
    if isinstance(task_op_data, dict):
        if "operation" in task_op_data:
            print(f"✅ Found 'operation': {task_op_data['operation']}")
            
            if "description" in task_op_data:
                print(f"✅ Found 'description': {task_op_data['description']}")
                print("✅ Should create TaskItem(title='shopping')")
            elif "task" in task_op_data:
                print(f"✅ Found 'task': {task_op_data['task']}")
            else:
                print("❌ No task data found in nested format")
        else:
            print("❌ No 'operation' field found")
    else:
        print(f"❌ task_op_data is not a dict: {type(task_op_data)}")
    
    try:
        from app.models import TaskOp, TaskItem
        
        task_op = TaskOp(op=task_op_data["operation"])
        print(f"✅ TaskOp created: {task_op}")
        
        task_item = TaskItem(title=task_op_data["description"])
        print(f"✅ TaskItem created: {task_item}")
        
    except Exception as e:
        print(f"❌ Model creation failed: {e}")

def test_user_input_patterns():
    """Test various user input patterns that should work."""
    print("\n🧪 Testing User Input Patterns")
    print("=" * 35)
    
    test_cases = [
        "create a task to do shopping",
        "create task buy groceries", 
        "add task call mom",
        "new task finish report",
        "תוסיף משימה לקנות חלב",
        "create few tasks, buy apples, buy oranges"
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. Input: '{test_case}'")
        
        if any(phrase in test_case.lower() for phrase in ['create a task', 'create task', 'add task', 'new task']):
            print("   ✅ English pattern detected")
        elif any(phrase in test_case for phrase in ['תוסיף משימה', 'הוסף משימה']):
            print("   ✅ Hebrew pattern detected")
        elif 'create few tasks' in test_case.lower():
            print("   ✅ Multiple task pattern detected")
        else:
            print("   ❌ No pattern detected")

def main():
    """Run the specific parsing issue tests."""
    print("🔧 Testing Specific Parsing Issue from User Log")
    print("=" * 60)
    
    test_nested_operation_parsing()
    test_user_input_patterns()
    
    print(f"\n🎯 Parsing issue tests completed!")
    print("\nKey findings:")
    print("- OpenAI returns nested format with 'operation' and 'description'")
    print("- Need to handle 'description' field as task title")
    print("- TaskOp should be created from 'operation' field")
    print("- TaskItem should be created from 'description' field")

if __name__ == "__main__":
    main()
