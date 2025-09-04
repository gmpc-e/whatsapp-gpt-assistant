#!/usr/bin/env python3
"""Comprehensive verification script for import fixes."""

import sys
import traceback

def test_core_models_import():
    """Test that all core models can be imported."""
    print("🧪 Testing core models import...")
    try:
        from app.models import (
            EventCreate,
            EventUpdate, 
            EventUpdateChanges,
            EventUpdateCriteria,
            EventListQuery,
            TaskItem,
            TaskUpdate,
            TaskOp,
            IntentResult,
            TaskPriority,
            TaskCategory,
            EnhancedTaskItem
        )
        print("✅ All core models imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Core models import failed: {e}")
        traceback.print_exc()
        return False

def test_dependencies_available():
    """Test that all required dependencies are available."""
    print("\n🧪 Testing dependencies...")
    try:
        import pytest
        import dateparser
        import fastapi
        import uvicorn
        import pydantic_settings
        print("✅ All critical dependencies available")
        return True
    except ImportError as e:
        print(f"❌ Dependencies missing: {e}")
        return False

def test_connectors_import():
    """Test that connectors can import their dependencies."""
    print("\n🧪 Testing connectors import...")
    try:
        from app.connectors.google_calendar import GoogleCalendarConnector
        from app.connectors.openai_intent import OpenAIIntentConnector
        print("✅ Connectors imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Connectors import failed: {e}")
        return False
    except Exception as e:
        if 'ValidationError' in str(type(e).__name__) and 'OPENAI_API_KEY' in str(e):
            print("✅ Connectors import successfully (fail due to missing env vars, not imports)")
            return True
        else:
            print(f"❌ Connectors import failed: {e}")
            return False

def test_app_import_behavior():
    """Test that app fails correctly due to env vars, not imports."""
    print("\n🧪 Testing app import behavior...")
    try:
        import app.main
        print("❌ App imported unexpectedly (should fail due to missing env vars)")
        return False
    except Exception as e:
        if 'ValidationError' in str(type(e).__name__) and 'OPENAI_API_KEY' in str(e):
            print("✅ App fails correctly due to missing env vars (not import errors)")
            return True
        else:
            print(f"❌ App fails due to unexpected error: {type(e).__name__}")
            return False

def test_pytest_discovery():
    """Test that pytest can discover tests."""
    print("\n🧪 Testing pytest test discovery...")
    import subprocess
    try:
        result = subprocess.run([
            sys.executable, '-m', 'pytest', '--collect-only', '-q'
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("✅ pytest can discover tests successfully")
            return True
        else:
            print(f"❌ pytest discovery failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ pytest discovery test failed: {e}")
        return False

def main():
    """Run all verification tests."""
    print("🔍 Import Fixes Verification")
    print("=" * 50)
    
    tests = [
        test_core_models_import,
        test_dependencies_available,
        test_connectors_import,
        test_app_import_behavior,
        test_pytest_discovery
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
            results.append(False)
    
    passed = sum(results)
    total = len(results)
    
    print(f"\n📊 Final Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All import fixes verified successfully!")
        print("✅ The app is ready to launch with proper environment configuration")
        return True
    else:
        print("💥 Some verification tests failed!")
        print("❌ Import fixes need additional work")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
