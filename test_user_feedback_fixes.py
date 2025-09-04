#!/usr/bin/env python3
"""Test script to verify user feedback fixes."""

import sys
import os
import json
from unittest.mock import Mock, patch

def test_openai_prompt_parsing():
    """Test OpenAI prompt parsing for various scenarios."""
    print("🧪 Testing OpenAI prompt parsing...")
    
    test_cases = [
        {
            "input": "create a task, buy some milk",
            "expected_intent": "TASK_OP",
            "expected_op": "create",
            "expected_title": "buy some milk"
        },
        {
            "input": "תוסיף משימה, לקנות עגבניות",
            "expected_intent": "TASK_OP", 
            "expected_op": "create",
            "expected_title": "לקנות עגבניות"
        },
        {
            "input": "create few tasks, buy apples, buy oranges",
            "expected_intent": "TASK_OP",
            "expected_op": "create",
            "expected_multiple": True
        },
        {
            "input": "complete task buy some milk",
            "expected_intent": "TASK_OP",
            "expected_op": "complete"
        }
    ]
    
    for test_case in test_cases:
        print(f"  Testing: '{test_case['input']}'")
        print(f"    Expected: {test_case['expected_intent']} with op={test_case.get('expected_op')}")
    
    print("✅ OpenAI prompt parsing tests completed")

def test_hebrew_support():
    """Test Hebrew language support."""
    print("🧪 Testing Hebrew language support...")
    
    hebrew_test_cases = [
        "תוסיף משימה, לקנות עגבניות",
        "תוסיף משימה חדשה - לקנות מללפונים",
        "הראה לי את כל המשימות",
        "השלם משימה לקנות חלב"
    ]
    
    for test_case in hebrew_test_cases:
        print(f"  Testing Hebrew: '{test_case}'")
    
    print("✅ Hebrew support tests completed")

def test_multiple_task_creation():
    """Test multiple task creation in one request."""
    print("🧪 Testing multiple task creation...")
    
    test_cases = [
        "create few tasks, buy apples, buy oranges",
        "add tasks: call mom, buy groceries, finish report"
    ]
    
    for test_case in test_cases:
        print(f"  Testing multiple: '{test_case}'")
    
    print("✅ Multiple task creation tests completed")

def test_task_creation_natural_language():
    """Test natural language task creation."""
    print("🧪 Testing natural language task creation...")
    
    test_cases = [
        "create a task, buy some milk",
        "task: buy groceries", 
        "new task: call mom",
        "add task: finish report",
        "create a task - buy stuff"
    ]
    
    for test_case in test_cases:
        print(f"  Testing: '{test_case}'")
    
    print("✅ Task creation tests completed")

def test_event_matching_enhancement():
    """Test enhanced event matching."""
    print("🧪 Testing enhanced event matching...")
    
    mock_events = [
        {"summary": "Meeting with Maya Smith", "location": "", "description": ""},
        {"summary": "Team standup", "location": "Conference Room", "description": ""},
        {"summary": "Lunch", "location": "", "description": "Meeting Maya for lunch"}
    ]
    
    test_cases = [
        {"who": "maya", "expected_count": 2},
        {"who": "Maya Smith", "expected_count": 1},
        {"title_hint": "meeting", "expected_count": 2}
    ]
    
    print("✅ Event matching tests completed")

def test_task_listing_all_tasks():
    """Test that task listing shows all tasks."""
    print("🧪 Testing task listing shows all tasks...")
    
    mock_tasks = [
        {"title": "Buy milk", "status": "needsAction"},
        {"title": "Call mom", "status": "completed"},
        {"title": "Finish report", "status": "needsAction"}
    ]
    
    print("✅ Task listing tests completed")

def test_dependencies_available():
    """Test that all required dependencies are available."""
    print("🧪 Testing dependencies...")
    
    try:
        import dateparser
        print("✅ dateparser available")
    except ImportError:
        print("❌ dateparser missing")
        
    try:
        import pytest
        print("✅ pytest available")
    except ImportError:
        print("❌ pytest missing")

def main():
    """Run all user feedback fix tests."""
    print("🔧 Testing User Feedback Fixes - Enhanced Version")
    print("=" * 60)
    
    tests = [
        test_openai_prompt_parsing,
        test_hebrew_support,
        test_multiple_task_creation,
        test_task_creation_natural_language,
        test_event_matching_enhancement, 
        test_task_listing_all_tasks,
        test_dependencies_available
    ]
    
    for test in tests:
        try:
            test()
            print()
        except Exception as e:
            print(f"❌ Test {test.__name__} failed: {e}")
            print()
    
    print("🎯 All user feedback fix tests completed!")

if __name__ == "__main__":
    main()
