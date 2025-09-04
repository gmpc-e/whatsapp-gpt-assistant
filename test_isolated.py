"""Isolated test for enhanced features without config dependencies."""

import sys
import os
from pathlib import Path
from unittest.mock import patch, Mock

sys.path.insert(0, str(Path(__file__).parent / "app"))

def test_nlp_without_config():
    """Test NLP functionality without requiring full config."""
    print("Testing NLP without config dependencies...")
    
    mock_settings = Mock()
    mock_settings.TIMEZONE = "UTC"
    
    with patch('app.connectors.enhanced_nlp.settings', mock_settings):
        try:
            from app.connectors.enhanced_nlp import EnhancedNLPProcessor
            nlp = EnhancedNLPProcessor()
            
            start, end = nlp.parse_date_range("show me events tomorrow")
            print(f"✅ Date parsing works: {start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')}")
            
            status = nlp.extract_task_status_filter("show me open tasks")
            print(f"✅ Task status filtering: {status}")
            
            mock_events = [
                {
                    'start': {'dateTime': start.replace(hour=10).isoformat()},
                    'end': {'dateTime': start.replace(hour=11).isoformat()}
                }
            ]
            
            free_slots = nlp.find_free_slots(mock_events, start, end, duration_hours=2)
            print(f"✅ Free slots detection: {len(free_slots)} slots found")
            
            mock_tasks = [
                {'title': 'Test task', 'status': 'needsAction'},
                {'title': 'Done task', 'status': 'completed'}
            ]
            
            summary = nlp.generate_summary(mock_events, mock_tasks, "test period")
            print(f"✅ Summary generation: {len(summary)} characters")
            
            return True
            
        except Exception as e:
            print(f"❌ NLP test failed: {e}")
            import traceback
            traceback.print_exc()
            return False

def test_utilities():
    """Test utility functions."""
    print("\nTesting utility functions...")
    
    try:
        from app.utils.validation import validate_phone_number, sanitize_text_input
        from app.utils.rate_limiter import RateLimiter
        
        valid = validate_phone_number("whatsapp:+1234567890")
        print(f"✅ Phone validation: {valid}")
        
        clean = sanitize_text_input("Hello <script>alert('test')</script>")
        print(f"✅ Text sanitization: '{clean}'")
        
        limiter = RateLimiter()
        allowed = limiter.is_allowed("test", 5, 60)
        print(f"✅ Rate limiter: {allowed}")
        
        return True
        
    except Exception as e:
        print(f"❌ Utilities test failed: {e}")
        return False

def main():
    """Run isolated tests."""
    print("🧪 Isolated Test - Enhanced Features")
    print("=" * 40)
    
    tests = [test_nlp_without_config, test_utilities]
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
        print("🎉 All isolated tests passed!")
        return True
    else:
        print("💥 Some tests failed!")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
