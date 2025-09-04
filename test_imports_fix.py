"""Test script to verify import fixes work correctly."""

def test_models_import():
    """Test that all models can be imported from app.models."""
    try:
        from app.models import (
            EventCreate,
            EventUpdate,
            EventUpdateChanges,
            TaskItem,
            IntentResult,
            TaskPriority,
            TaskCategory,
            EnhancedTaskItem
        )
        print("✅ All models imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Models import failed: {e}")
        return False

def test_connectors_import():
    """Test that connectors can import their dependencies."""
    try:
        from app.connectors.google_calendar import GoogleCalendarConnector
        from app.connectors.openai_intent import OpenAIIntentConnector
        print("✅ Connectors imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Connectors import failed: {e}")
        return False

def test_pytest_available():
    """Test that pytest is available."""
    try:
        import pytest
        print("✅ pytest imported successfully")
        return True
    except ImportError as e:
        print(f"❌ pytest import failed: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing import fixes...")
    
    tests = [test_models_import, test_connectors_import, test_pytest_available]
    results = [test() for test in tests]
    
    passed = sum(results)
    total = len(results)
    
    print(f"\n📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All import tests passed!")
    else:
        print("💥 Some import tests failed!")
