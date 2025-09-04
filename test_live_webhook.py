#!/usr/bin/env python3
"""
Test the live webhook with the exact failing scenario.
"""

import requests
import json
import time

def test_live_webhook_parsing():
    """Test the live webhook with 'create a task to do shopping'."""
    print("🧪 Testing Live Webhook Parsing Fix")
    print("=" * 45)
    
    time.sleep(2)
    
    webhook_data = {
        'From': 'whatsapp:+1234567890',
        'To': 'whatsapp:+14155238886',
        'Body': 'create a task to do shopping',
        'NumMedia': '0'
    }
    
    try:
        print(f"Sending webhook request to http://127.0.0.1:8000/whatsapp")
        print(f"Request data: {webhook_data}")
        
        response = requests.post(
            'http://127.0.0.1:8000/whatsapp',
            data=webhook_data,
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            timeout=10
        )
        
        print(f"Response status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        print(f"Response body: {response.text}")
        
        if response.status_code == 200:
            print("✅ Webhook request successful")
            
            if '<Response>' in response.text or 'xml' in response.headers.get('content-type', '').lower():
                print("✅ Response appears to be valid TwiML")
            else:
                print("⚠️  Response doesn't appear to be TwiML format")
                
            return True
        else:
            print(f"❌ Webhook request failed with status {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server - is it running on port 8000?")
        return False
    except requests.exceptions.Timeout:
        print("❌ Request timed out")
        return False
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return False

def main():
    """Run the live webhook test."""
    print("🔧 Testing Live Webhook for TaskUpdate Validation Fix")
    print("=" * 60)
    
    success = test_live_webhook_parsing()
    
    if success:
        print(f"\n🎯 Live webhook test completed!")
        print("\nKey verification:")
        print("✅ Server responded to webhook request")
        print("✅ No connection errors")
        print("✅ Check server logs for TaskUpdate validation errors")
        
        print(f"\nNext steps:")
        print("1. Check the server logs for any TaskUpdate validation errors")
        print("2. If no validation errors appear, the fix is working")
        print("3. If validation errors still appear, need further debugging")
    else:
        print(f"\n❌ Live webhook test failed")
        print("Check that the server is running on port 8000")

if __name__ == "__main__":
    main()
