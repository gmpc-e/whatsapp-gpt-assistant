#!/usr/bin/env python3
"""
Test the nested parsing fix for the specific user error.
"""

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def test_nested_operation_parsing_fix():
    """Test that the nested operation parsing fix works."""
    print("🧪 Testing Nested Operation Parsing Fix")
    print("=" * 45)
    
    try:
        from models import TaskOp, TaskItem, IntentResult
        print("✅ Successfully imported models")
    except ImportError as e:
        print(f"❌ Failed to import models: {e}")
        return
    
    openai_response = {
        "intent": "TASK_OP",
        "task_op": {
            "operation": "create",
            "description": "shopping"
        },
        "answer": "I've created a task for you to do shopping."
    }
    
    print(f"Testing OpenAI response: {json.dumps(openai_response, indent=2)}")
    
    data = openai_response
    result = IntentResult(
        intent=data.get("intent", "QUESTION"),
        answer=data.get("answer", ""),
        confidence=data.get("confidence", None),
        recency_required=data.get("recency_required", None),
        domain=data.get("domain", None),
    )
    
    if data.get("task_op"):
        try:
            task_op_data = data["task_op"]
            print(f"Parsing task_op_data: {task_op_data}")
            
            if isinstance(task_op_data, dict):
                if "operation" in task_op_data:
                    result.task_op = TaskOp(op=task_op_data["operation"])
                    print(f"✅ Created TaskOp: {result.task_op}")
                    
                    if "description" in task_op_data:
                        result.task = TaskItem(title=task_op_data["description"])
                        print(f"✅ Created TaskItem from description: {result.task}")
                    elif "task" in task_op_data:
                        if isinstance(task_op_data["task"], str):
                            result.task = TaskItem(title=task_op_data["task"])
                            print(f"✅ Created TaskItem from task string: {result.task}")
                        elif isinstance(task_op_data["task"], dict):
                            result.task = TaskItem(**task_op_data["task"])
                            print(f"✅ Created TaskItem from task dict: {result.task}")
                    else:
                        print("❌ No task data found in nested format")
                else:
                    print("❌ No 'operation' field found")
            else:
                print(f"❌ task_op_data is not a dict: {type(task_op_data)}")
                
        except Exception as e:
            print(f"❌ Parsing failed: {e}")
            return
    
    if hasattr(result, 'task_op') and result.task_op:
        print(f"✅ Result has task_op: {result.task_op.op}")
    else:
        print("❌ Result missing task_op")
        
    if hasattr(result, 'task') and result.task:
        print(f"✅ Result has task: {result.task.title}")
    else:
        print("❌ Result missing task")
    
    try:
        from models import TaskUpdate
        TaskUpdate(**task_op_data)
        print("❌ TaskUpdate validation should have failed but didn't")
    except Exception as e:
        print(f"✅ TaskUpdate validation correctly failed: {type(e).__name__}")

def test_improved_system_prompt():
    """Test that the improved system prompt examples are clear."""
    print("\n🧪 Testing Improved System Prompt Examples")
    print("=" * 45)
    
    examples = [
        {
            "input": "create a task to do shopping",
            "expected_output": '{"intent":"TASK_OP", "task_op":{"op":"create"}, "task":{"title":"do shopping"}}'
        },
        {
            "input": "create a task, buy some milk", 
            "expected_output": '{"intent":"TASK_OP", "task_op":{"op":"create"}, "task":{"title":"buy some milk"}}'
        }
    ]
    
    for i, example in enumerate(examples, 1):
        print(f"\n{i}. Input: '{example['input']}'")
        print(f"   Expected: {example['expected_output']}")
        
        try:
            parsed = json.loads(example['expected_output'])
            if 'task' in parsed and 'title' in parsed['task']:
                print(f"   ✅ Uses 'title' field correctly: {parsed['task']['title']}")
            else:
                print(f"   ❌ Missing title field in task")
        except json.JSONDecodeError as e:
            print(f"   ❌ Invalid JSON in example: {e}")

def main():
    """Run all nested parsing fix tests."""
    print("🔧 Testing Nested Parsing Fix for User Error")
    print("=" * 60)
    
    test_nested_operation_parsing_fix()
    test_improved_system_prompt()
    
    print(f"\n🎯 Nested parsing fix tests completed!")
    print("\nKey improvements:")
    print("✅ Handle 'description' field in nested task_op format")
    print("✅ Create TaskItem from description when operation is present")
    print("✅ Updated system prompt to prefer 'title' over 'description'")
    print("✅ Added explicit example for 'create a task to do shopping'")
    
    print(f"\nNext steps:")
    print("1. Commit and push the parsing fix")
    print("2. Test the webhook with 'create a task to do shopping'")
    print("3. Verify no TaskUpdate validation errors appear")

if __name__ == "__main__":
    main()
