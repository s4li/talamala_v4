"""
TalaMala v4 - SMS Diagnostic Script
====================================
Tests SMS sending via sms.ir and Kavenegar with detailed error reporting.

Usage:
    python scripts/test_sms.py
"""

import sys
import os
import json

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


def test_smsir_verify_with_template(mobile, template_id):
    """Test sms.ir Verify API with custom template."""
    import requests
    print(f"\n  --- sms.ir Verify (template={template_id}) ---")
    try:
        url = "https://api.sms.ir/v1/send/verify"
        headers = {
            "Content-Type": "application/json",
            "Accept": "text/plain",
            "X-API-KEY": SMSIR_API_KEY,
        }
        payload = {
            "mobile": mobile,
            "templateId": int(template_id),
            "parameters": [
                {"name": "NAME", "value": "Test"},
                {"name": "CODE", "value": "12345"},
            ],
        }
        print(f"  URL: {url}")
        print(f"  Payload: {json.dumps(payload, ensure_ascii=False)}")
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        print(f"  HTTP Status: {response.status_code}")
        print(f"  Response: {response.text}")
        data = response.json()
        if response.status_code == 200 and data.get("status") == 1:
            print("  Result: SUCCESS ✓")
        else:
            print(f"  Result: FAILED ✗ — {data.get('message', '')}")
    except Exception as e:
        print(f"  EXCEPTION: {type(e).__name__}: {e}")


def test_smsir_verify_no_template(mobile):
    """Test sms.ir Verify API without templateId (system default)."""
    import requests
    print("\n  --- sms.ir Verify (no template — system default) ---")
    try:
        url = "https://api.sms.ir/v1/send/verify"
        headers = {
            "Content-Type": "application/json",
            "Accept": "text/plain",
            "X-API-KEY": SMSIR_API_KEY,
        }
        # Try without templateId — maybe sms.ir uses default OTP template
        payload = {
            "mobile": mobile,
            "templateId": 0,
            "parameters": [
                {"name": "CODE", "value": "12345"},
            ],
        }
        print(f"  URL: {url}")
        print(f"  Payload: {json.dumps(payload, ensure_ascii=False)}")
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        print(f"  HTTP Status: {response.status_code}")
        print(f"  Response: {response.text}")
    except Exception as e:
        print(f"  EXCEPTION: {type(e).__name__}: {e}")


def test_smsir_livetemplates(mobile):
    """Test sms.ir with live/system template IDs (common OTP template IDs)."""
    import requests
    print("\n  --- sms.ir Verify (common system template IDs) ---")

    # Common sms.ir system template IDs for OTP
    system_ids = [100000, 200000, 1, 2, 3]

    for tid in system_ids:
        try:
            url = "https://api.sms.ir/v1/send/verify"
            headers = {
                "Content-Type": "application/json",
                "Accept": "text/plain",
                "X-API-KEY": SMSIR_API_KEY,
            }
            payload = {
                "mobile": mobile,
                "templateId": tid,
                "parameters": [
                    {"name": "CODE", "value": "12345"},
                ],
            }
            print(f"\n  Trying templateId={tid}...")
            response = requests.post(url, json=payload, headers=headers, timeout=15)
            print(f"  HTTP {response.status_code}: {response.text[:200]}")
            data = response.json()
            if response.status_code == 200 and data.get("status") == 1:
                print(f"  >>> SUCCESS with templateId={tid} <<<")
                return tid
        except Exception as e:
            print(f"  Error: {e}")

    print("  No system template worked.")
    return None


def test_smsir_bulk(mobile):
    """Test sms.ir Bulk send."""
    import requests
    print("\n  --- sms.ir Bulk (plain text) ---")
    try:
        url = "https://api.sms.ir/v1/send/bulk"
        headers = {
            "Content-Type": "application/json",
            "Accept": "text/plain",
            "X-API-KEY": SMSIR_API_KEY,
        }
        payload = {
            "lineNumber": int(SMSIR_LINE_NUMBER) if SMSIR_LINE_NUMBER else 0,
            "messageText": "طلاملا\nتست ارسال پیامک\nکد: 12345",
            "mobiles": [mobile],
        }
        print(f"  URL: {url}")
        print(f"  Payload: {json.dumps(payload, ensure_ascii=False)}")
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        print(f"  HTTP Status: {response.status_code}")
        print(f"  Response: {response.text}")
    except Exception as e:
        print(f"  EXCEPTION: {type(e).__name__}: {e}")


def test_smsir_template_list():
    """List user's templates from sms.ir API."""
    import requests
    print("\n  --- sms.ir Template List ---")
    try:
        url = "https://api.sms.ir/v1/send/verify/templates"
        headers = {"Accept": "text/plain", "X-API-KEY": SMSIR_API_KEY}
        response = requests.get(url, headers=headers, timeout=15)
        print(f"  HTTP Status: {response.status_code}")
        print(f"  Response: {response.text[:500]}")
    except Exception as e:
        print(f"  EXCEPTION: {type(e).__name__}: {e}")


def main():
    print("=" * 60)
    print("  TalaMala SMS Diagnostic v2")
    print("=" * 60)

    # --- 1. Check env vars ---
    print("\n[1] Checking environment variables...")
    print(f"  SMS_API_KEY (Kavenegar):  {'SET' if SMS_API_KEY else 'NOT SET'}")
    print(f"  SMSIR_API_KEY:            {'SET' if SMSIR_API_KEY else 'NOT SET'}")
    print(f"  SMSIR_LINE_NUMBER:        {SMSIR_LINE_NUMBER or 'NOT SET'}")
    print(f"  SMSIR_TEMPLATE_ID:        {SMSIR_TEMPLATE_ID or 'NOT SET'}")

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

    # --- 3. Check sms.ir credit ---
    if SMSIR_API_KEY:
        print("\n[3] Checking sms.ir credit...")
        try:
            import requests
            url = "https://api.sms.ir/v1/credit"
            headers = {"Accept": "text/plain", "X-API-KEY": SMSIR_API_KEY}
            response = requests.get(url, headers=headers, timeout=10)
            print(f"  HTTP Status: {response.status_code}")
            data = response.json()
            if response.status_code == 200 and data.get("status") == 1:
                print(f"  Credit: {data.get('data', '?')} rial")
            else:
                print(f"  ERROR: {response.text}")
        except Exception as e:
            print(f"  ERROR: {e}")
    else:
        print("\n[3] Skipping sms.ir (no API key)")

    # --- 4. List sms.ir templates ---
    if SMSIR_API_KEY:
        test_smsir_template_list()

    # --- 5. Test send ---
    print("\n" + "=" * 60)
    mobile = input("  Enter mobile number to test (or press Enter to skip): ").strip()
    if not mobile:
        print("  Skipped.")
        print("  Diagnostic complete.")
        return

    print(f"\n  Testing all methods for {mobile}...")

    # 5a. sms.ir Verify with custom template (if set)
    if SMSIR_API_KEY and SMSIR_TEMPLATE_ID:
        test_smsir_verify_with_template(mobile, SMSIR_TEMPLATE_ID)

    # 5b. sms.ir Verify without template
    if SMSIR_API_KEY:
        test_smsir_verify_no_template(mobile)

    # 5c. sms.ir Bulk
    if SMSIR_API_KEY:
        test_smsir_bulk(mobile)

    # 5d. Try common system template IDs
    if SMSIR_API_KEY:
        test_smsir_livetemplates(mobile)

    print("\n" + "=" * 60)
    print("  Diagnostic complete.")
    print("  Check your phone — did any SMS arrive?")
    print("=" * 60)


if __name__ == "__main__":
    main()
