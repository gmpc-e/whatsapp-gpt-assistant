"""Test runner script for comprehensive testing."""

import subprocess
import sys
import os
from pathlib import Path


def run_command(cmd, description):
    """Run a command and return success status."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {cmd}")
    print('='*60)
    
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print("✅ SUCCESS")
        if result.stdout:
            print("STDOUT:", result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print("❌ FAILED")
        print("STDOUT:", e.stdout)
        print("STDERR:", e.stderr)
        return False


def main():
    """Run comprehensive test suite."""
    os.chdir(Path(__file__).parent)
    
    print("🧪 WhatsApp GPT Assistant - Comprehensive Test Suite")
    print("="*60)
    
    tests = [
        ("python -m pytest tests/test_enhanced_nlp.py -v", "Enhanced NLP Tests"),
        ("python -m pytest tests/test_rate_limiting.py -v", "Rate Limiting Tests"),
        ("python -m pytest tests/test_webhook_integration.py -v", "Webhook Integration Tests"),
        ("python -m pytest tests/test_integration_full.py -v", "Full Integration Tests"),
        ("python -m pytest tests/ -v --tb=short", "All Tests"),
    ]
    
    results = []
    for cmd, description in tests:
        success = run_command(cmd, description)
        results.append((description, success))
    
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    all_passed = True
    for description, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {description}")
        if not success:
            all_passed = False
    
    print("\n" + "="*60)
    if all_passed:
        print("🎉 ALL TESTS PASSED!")
        sys.exit(0)
    else:
        print("💥 SOME TESTS FAILED!")
        sys.exit(1)


if __name__ == "__main__":
    main()
