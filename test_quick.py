"""Quick test to verify enhanced features work."""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "app"))

def test_basic_imports():
    """Test that basic imports work."""
    print("Testing basic imports...")
    
    try:
        from app.connectors.enhanced_nlp import EnhancedNLPProcessor
        nlp = EnhancedNLPProcessor()
        print("✅ Enhanced NLP imported and instantiated")
        
        start, end = nlp.parse_date_range("tomorrow")
        print(f"✅ Date parsing works: {start} to {end}")
        
        status = nlp.extract_task_status_filter("show me open tasks")
        print(f"✅ Task status filtering: {status}")
        
        return True
        
    except Exception as e:
        print(f"❌ Import test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_validation():
    """Test validation utilities."""
    print("\nTesting validation...")
    
    try:
        from app.utils.validation import validate_phone_number, sanitize_text_input
        
        valid = validate_phone_number("whatsapp:+1234567890")
        print(f"✅ Phone validation: {valid}")
        
        clean = sanitize_text_input("Hello <script>alert('test')</script>")
        print(f"✅ Text sanitization: '{clean}'")
        
        return True
        
    except Exception as e:
        print(f"❌ Validation test failed: {e}")
        return False

def main():
    """Run quick tests."""
    print("🚀 Quick Test - Enhanced WhatsApp GPT Assistant")
    print("=" * 50)
    
    tests = [test_basic_imports, test_validation]
    results = []
    
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test failed: {e}")
            results.append(False)
    
    passed = sum(results)
    total = len(results)
    
    print(f"\n📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All quick tests passed!")
        return True
    else:
        print("💥 Some tests failed!")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
