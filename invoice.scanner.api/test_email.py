#!/usr/bin/env python3
"""
Test script to verify email service functionality.
Run: python test_email.py
"""

import sys
import os

# Add parent directory to path to import lib modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lib.email_service import send_email, send_password_reset_email
from dotenv import load_dotenv

load_dotenv()


def test_basic_email():
    """Test basic email sending."""
    print("\n" + "="*60)
    print("TEST 1: Basic Email")
    print("="*60)
    
    result = send_email(
        to_email="rickard@strawbay.io",
        subject="🧪 Test Email from Strawbay",
        html_body="""
        <html>
            <body style="font-family: Arial, sans-serif;">
                <h1>Hello Rickard!</h1>
                <p>This is a test email from the Strawbay Invoice Scanner.</p>
                <p style="color: #5b7cff; font-weight: bold;">If you received this, the email service is working! ✅</p>
            </body>
        </html>
        """,
        text_body="Hello Rickard!\n\nThis is a test email from Strawbay. If you received this, the email service is working!"
    )
    
    print(f"Result: {'✅ SUCCESS' if result else '❌ FAILED'}\n")
    return result


def test_password_reset_email():
    """Test password reset email."""
    print("="*60)
    print("TEST 2: Password Reset Email")
    print("="*60)
    
    result = send_password_reset_email(
        to_email="rickard@strawbay.io",
        name="Rickard",
        reset_link="http://localhost:3000/reset-password/abc123xyz"
    )
    
    print(f"Result: {'✅ SUCCESS' if result else '❌ FAILED'}\n")
    return result


def main():
    """Run all email tests."""
    print("\n")
    print("╔" + "="*58 + "╗")
    print("║" + " "*58 + "║")
    print("║" + "  STRAWBAY EMAIL SERVICE TEST".center(58) + "║")
    print("║" + " "*58 + "║")
    print("╚" + "="*58 + "╝")
    
    # Check environment variables
    print("\n🔍 Checking environment variables...")
    gmail_sender = os.getenv("GMAIL_SENDER")
    gmail_password = os.getenv("GMAIL_PASSWORD")
    
    if not gmail_sender or not gmail_password:
        print("❌ Missing GMAIL_SENDER or GMAIL_PASSWORD in .env")
        print(f"   GMAIL_SENDER: {gmail_sender or 'NOT SET'}")
        print(f"   GMAIL_PASSWORD: {'SET' if gmail_password else 'NOT SET'}")
        sys.exit(1)
    
    print(f"✅ GMAIL_SENDER: {gmail_sender}")
    print(f"✅ GMAIL_PASSWORD: {'*' * 4 + '...' + gmail_password[-4:]}")
    
    # Run tests
    results = {
        "Basic Email": test_basic_email(),
        "Password Reset Email": test_password_reset_email(),
    }
    
    # Summary
    print("="*60)
    print("TEST SUMMARY")
    print("="*60)
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name:<30} {status}")
    
    total_passed = sum(results.values())
    total_tests = len(results)
    print(f"\nTotal: {total_passed}/{total_tests} tests passed")
    
    if total_passed == total_tests:
        print("\n🎉 All tests passed! Email service is working correctly.\n")
    else:
        print("\n⚠️  Some tests failed. Check the logs above.\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
