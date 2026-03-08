"""
TalaMala v4 - SMS Diagnostic Script
====================================
Tests SMS sending and reports detailed errors.

Usage:
    python scripts/test_sms.py
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from config.settings import (
    SMS_API_KEY,
    SMSIR_API_KEY,
    SMSIR_LINE_NUMBER,
    SMSIR_TEMPLATE_ID,
)


def main():
    print("=" * 60)
    print("  TalaMala SMS Diagnostic")
    print("=" * 60)

    # --- 1. Check env vars ---
    print("\n[1] Checking environment variables...")

    print(f"  SMS_API_KEY (Kavenegar):  {'SET ✓' if SMS_API_KEY else 'NOT SET ✗'}")
    print(f"  SMSIR_API_KEY:            {'SET ✓' if SMSIR_API_KEY else 'NOT SET ✗'}")
    print(f"  SMSIR_LINE_NUMBER:        {SMSIR_LINE_NUMBER or 'NOT SET ✗'}")
    print(f"  SMSIR_TEMPLATE_ID:        {SMSIR_TEMPLATE_ID or 'NOT SET (will use bulk)'}")

    # --- 2. Check active provider from DB ---
    print("\n[2] Checking active SMS provider (DB setting)...")
    try:
        from config.database import SessionLocal
        from modules.admin.models import SystemSetting
        session = SessionLocal()
        setting = session.query(SystemSetting).filter(
            SystemSetting.key == "sms_provider"
        ).first()
        provider = setting.value if setting else "smsir (default)"
        print(f"  Active provider: {provider}")
        session.close()
    except Exception as e:
        print(f"  ERROR reading DB: {e}")
        provider = "unknown"

    # --- 3. Check sms.ir credit ---
    if SMSIR_API_KEY:
        print("\n[3] Checking sms.ir credit...")
        try:
            import requests
            url = "https://api.sms.ir/v1/credit"
            headers = {"Accept": "text/plain", "X-API-KEY": SMSIR_API_KEY}
            response = requests.get(url, headers=headers, timeout=10)
            print(f"  HTTP Status: {response.status_code}")
            print(f"  Response: {response.text}")
            data = response.json()
            if response.status_code == 200 and data.get("status") == 1:
                print(f"  Credit: {data.get('data', '?')}")
            else:
                print(f"  ERROR: {data.get('message', response.text)}")
        except Exception as e:
            print(f"  ERROR: {e}")
    else:
        print("\n[3] Skipping sms.ir credit check (no API key)")

    # --- 4. Check Kavenegar credit ---
    if SMS_API_KEY:
        print("\n[4] Checking Kavenegar credit...")
        try:
            import requests
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            url = f"https://api.kavenegar.com/v1/{SMS_API_KEY}/account/info.json"
            response = requests.get(url, timeout=10, verify=False)
            print(f"  HTTP Status: {response.status_code}")
            print(f"  Response: {response.text}")
        except Exception as e:
            print(f"  ERROR: {e}")
    else:
        print("\n[4] Skipping Kavenegar check (no API key)")

    # --- 5. Test send ---
    print("\n[5] Test SMS send...")
    mobile = input("  Enter mobile number to test (or press Enter to skip): ").strip()
    if not mobile:
        print("  Skipped.")
        print("\n" + "=" * 60)
        print("  Diagnostic complete.")
        print("=" * 60)
        return

    print(f"  Sending test SMS to {mobile}...")
    from common.sms import sms_sender

    # Test OTP
    print("\n  --- OTP Test ---")
    try:
        result = sms_sender.send_otp_lookup(
            receptor=mobile,
            token="Test",
            token2="12345",
        )
        print(f"  Result: {'SUCCESS ✓' if result else 'FAILED ✗'}")
    except Exception as e:
        print(f"  EXCEPTION: {type(e).__name__}: {e}")

    # Test plain text
    print("\n  --- Plain Text Test ---")
    try:
        result = sms_sender.send_plain_text(
            receptor=mobile,
            message="طلاملا - تست ارسال پیامک",
        )
        print(f"  Result: {'SUCCESS ✓' if result else 'FAILED ✗'}")
    except Exception as e:
        print(f"  EXCEPTION: {type(e).__name__}: {e}")

    print("\n" + "=" * 60)
    print("  Diagnostic complete.")
    print("=" * 60)


if __name__ == "__main__":
    main()
