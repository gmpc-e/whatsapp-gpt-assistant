"""Manual testing script for enhanced features."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "app"))

from app.connectors.enhanced_nlp import EnhancedNLPProcessor
from app.models import IntentResult
from datetime import datetime, timedelta


async def test_enhanced_nlp():
    """Test enhanced NLP processing."""
    print("🧪 Testing Enhanced NLP Processing")
    print("=" * 50)
    
    nlp = EnhancedNLPProcessor()
    
    test_queries = [
        "show me events tomorrow",
        "show me events next week", 
        "show me events next sunday",
        "give me free slots next week",
        "show me task summary"
    ]
    
    for query in test_queries:
        print(f"\nQuery: '{query}'")
        try:
            start, end = nlp.parse_date_range(query)
            print(f"  Date range: {start.strftime('%Y-%m-%d %H:%M')} to {end.strftime('%Y-%m-%d %H:%M')}")
            
            status = nlp.extract_task_status_filter(query)
            if status:
                print(f"  Task status filter: {status}")
                
        except Exception as e:
            print(f"  Error: {e}")
    
    print(f"\n🏖️ Testing Free Slot Detection")
    print("-" * 30)
    
    now = datetime.now(nlp.timezone)
    start_time = now.replace(hour=9, minute=0, second=0, microsecond=0)
    end_time = start_time.replace(hour=17)
    
    events = [
        {
            'start': {'dateTime': start_time.replace(hour=10).isoformat()},
            'end': {'dateTime': start_time.replace(hour=11).isoformat()}
        },
        {
            'start': {'dateTime': start_time.replace(hour=14).isoformat()},
            'end': {'dateTime': start_time.replace(hour=15).isoformat()}
        }
    ]
    
    free_slots = nlp.find_free_slots(events, start_time, end_time, duration_hours=2)
    print(f"Found {len(free_slots)} free slots:")
    for slot in free_slots:
        print(f"  - {slot['suggestion']}")
    
    print(f"\n📊 Testing Summary Generation")
    print("-" * 30)
    
    mock_tasks = [
        {'title': 'Complete project', 'status': 'needsAction'},
        {'title': 'Review code', 'status': 'completed'},
        {'title': 'Call client', 'status': 'needsAction'}
    ]
    
    summary = nlp.generate_summary(events, mock_tasks, "test period")
    print(summary)


def test_validation_functions():
    """Test validation functions."""
    print("\n🔍 Testing Validation Functions")
    print("=" * 50)
    
    from app.utils.validation import validate_phone_number, sanitize_text_input
    
    test_phones = [
        "whatsapp:+1234567890",
        "+1234567890", 
        "invalid-phone",
        ""
    ]
    
    for phone in test_phones:
        valid = validate_phone_number(phone)
        print(f"Phone '{phone}': {'✅ Valid' if valid else '❌ Invalid'}")
    
    test_texts = [
        "Normal text",
        "Text with <script>alert('xss')</script>",
        "Text with\nnewlines\tand\ttabs",
        ""
    ]
    
    for text in test_texts:
        sanitized = sanitize_text_input(text)
        print(f"Text '{text}' -> '{sanitized}'")


def test_rate_limiter():
    """Test rate limiting."""
    print("\n⏱️ Testing Rate Limiter")
    print("=" * 50)
    
    from app.utils.rate_limiter import RateLimiter
    
    limiter = RateLimiter()
    
    for i in range(7):
        allowed = limiter.is_allowed("test_key", 5, 60)
        print(f"Request {i+1}: {'✅ Allowed' if allowed else '❌ Blocked'}")
        
        if not allowed:
            wait_time = limiter.wait_time("test_key", 5, 60)
            print(f"  Wait time: {wait_time:.1f} seconds")


async def main():
    """Run all manual tests."""
    print("🚀 WhatsApp GPT Assistant - Manual Testing")
    print("=" * 60)
    
    try:
        await test_enhanced_nlp()
        test_validation_functions()
        test_rate_limiter()
        
        print("\n" + "=" * 60)
        print("✅ All manual tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
