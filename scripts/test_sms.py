"""
TalaMala v4 - SMS Diagnostic Script
====================================
Tests SMS sending via sms.ir Verify API.

Usage:
    python scripts/test_sms.py
    python scripts/test_sms.py 09121234567
    python scripts/test_sms.py 09121234567 123456   (with template ID)
"""

import sys
import os
import json
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from config.settings import (
    SMSIR_API_KEY,
    SMSIR_LINE_NUMBER,
    SMSIR_TEMPLATE_ID,
)

API_URL = "https://api.sms.ir/v1/send/verify"
HEADERS = {
    "Content-Type": "application/json",
    "Accept": "text/plain",
    "X-API-KEY": SMSIR_API_KEY,
}


def send_verify(mobile, template_id, params):
    """Send via sms.ir Verify and print full response."""
    payload = {
        "mobile": mobile,
        "templateId": int(template_id),
        "parameters": params,
    }
    print(f"  templateId: {template_id}")
    print(f"  parameters: {json.dumps(params, ensure_ascii=False)}")
    try:
        response = requests.post(API_URL, json=payload, headers=HEADERS, timeout=15)
        print(f"  HTTP {response.status_code}: {response.text}")
        return response
    except Exception as e:
        print(f"  ERROR: {e}")
        return None


def main():
    print("=" * 60)
    print("  TalaMala SMS Test (sms.ir Verify only)")
    print("=" * 60)

    # Get mobile from arg or input
    mobile = sys.argv[1] if len(sys.argv) > 1 else input("  Mobile: ").strip()
    template_id = sys.argv[2] if len(sys.argv) > 2 else SMSIR_TEMPLATE_ID
    if not mobile:
        print("  No mobile provided. Exiting.")
        return

    print(f"\n  Target: {mobile}")
    print(f"  API Key: {'SET' if SMSIR_API_KEY else 'NOT SET'}")

    # Test 1: Verify with custom template (if available)
    if template_id:
        print(f"\n[1] Verify with custom template (ID={template_id})...")
        send_verify(mobile, template_id, [
            {"name": "NAME", "value": "Test"},
            {"name": "CODE", "value": "12345"},
        ])
    else:
        print("\n[1] Skipped — no SMSIR_TEMPLATE_ID set")

    # Test 2: Verify with templateId=0
    print("\n[2] Verify with templateId=0 (system default)...")
    send_verify(mobile, 0, [
        {"name": "CODE", "value": "12345"},
    ])

    # Test 3: Verify with common system IDs
    print("\n[3] Trying common system template IDs...")
    for tid in [1, 2, 100000]:
        print(f"\n  --- templateId={tid} ---")
        resp = send_verify(mobile, tid, [
            {"name": "CODE", "value": "12345"},
        ])
        if resp and resp.status_code == 200:
            try:
                data = resp.json()
                if data.get("status") == 1:
                    print(f"\n  >>> SUCCESS with templateId={tid} <<<")
                    break
            except Exception:
                pass

    print("\n" + "=" * 60)
    print("  Done. Check your phone.")
    print("=" * 60)


if __name__ == "__main__":
    main()
