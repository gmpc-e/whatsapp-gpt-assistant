"""Test script for enhanced features."""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "app"))

def test_imports():
    """Test that all new modules can be imported."""
    print("🔍 Testing imports...")
    
    try:
        from app.connectors.enhanced_nlp import EnhancedNLPProcessor
        print("✅ Enhanced NLP imported successfully")
        
        from app.utils.rate_limiter import RateLimiter
        print("✅ Rate limiter imported successfully")
        
        from app.utils.validation import validate_phone_number, sanitize_text_input
        print("✅ Validation utils imported successfully")
        
        from app.utils.performance_monitor import PerformanceMonitor
        print("✅ Performance monitor imported successfully")
        
        from app.utils.config_validator import validate_configuration
        print("✅ Config validator imported successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def test_nlp_functionality():
    """Test enhanced NLP functionality."""
    print("\n🧠 Testing NLP functionality...")
    
    try:
        from app.connectors.enhanced_nlp import EnhancedNLPProcessor
        nlp = EnhancedNLPProcessor()
        
        start, end = nlp.parse_date_range("show me events tomorrow")
        print(f"✅ Date parsing works: {start} to {end}")
        
        status = nlp.extract_task_status_filter("show me open tasks")
        print(f"✅ Task status filtering works: {status}")
        
        free_slots = nlp.find_free_slots([], start, end, duration_hours=2)
        print(f"✅ Free slots detection works: {len(free_slots)} slots found")
        
        summary = nlp.generate_summary([], [], "test period")
        print(f"✅ Summary generation works: {len(summary)} chars")
        
        return True
        
    except Exception as e:
        print(f"❌ NLP test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_validation():
    """Test validation functions."""
    print("\n🔒 Testing validation...")
    
    try:
        from app.utils.validation import validate_phone_number, sanitize_text_input
        
        valid = validate_phone_number("whatsapp:+1234567890")
        print(f"✅ Phone validation works: {valid}")
        
        clean = sanitize_text_input("Hello <script>alert('xss')</script> world")
        print(f"✅ Text sanitization works: '{clean}'")
        
        return True
        
    except Exception as e:
        print(f"❌ Validation test failed: {e}")
        return False

def test_rate_limiting():
    """Test rate limiting."""
    print("\n⏱️ Testing rate limiting...")
    
    try:
        from app.utils.rate_limiter import RateLimiter
        limiter = RateLimiter()
        
        allowed = limiter.is_allowed("test_key", 5, 60)
        print(f"✅ Rate limiting works: {allowed}")
        
        return True
        
    except Exception as e:
        print(f"❌ Rate limiting test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🚀 Testing Enhanced WhatsApp GPT Assistant Features")
    print("=" * 60)
    
    tests = [
        test_imports,
        test_nlp_functionality,
        test_validation,
        test_rate_limiting
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results.append(False)
    
    print("\n" + "=" * 60)
    print("📊 Test Results:")
    
    passed = sum(results)
    total = len(results)
    
    print(f"✅ Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed!")
        return True
    else:
        print("💥 Some tests failed!")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
