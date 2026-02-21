"""
Shahkar Identity Verification Service
========================================
Calls Zohal API to verify mobile + national_code match via Shahkar.
Admin can enable/disable from settings page.
"""

import httpx
from sqlalchemy.orm import Session

from common.templating import get_setting_from_db
from config.settings import SHAHKAR_API_TOKEN

ZOHAL_API_URL = "https://service.zohal.io/api/v0/services/inquiry/shahkar"


def verify_shahkar(db: Session, mobile: str, national_code: str) -> dict:
    """
    Verify mobile + national_code via Shahkar (Zohal API).

    Returns:
        {"matched": True}  — verification successful
        {"matched": False, "error": "..."}  — mismatch or API error
        {"skip": True}  — service disabled
    """
    enabled = get_setting_from_db(db, "shahkar_enabled", "false")
    if enabled != "true":
        return {"skip": True}

    token = SHAHKAR_API_TOKEN
    if not token:
        return {"matched": False, "error": "توکن API شاهکار تنظیم نشده است."}

    try:
        resp = httpx.post(
            ZOHAL_API_URL,
            json={"mobile": mobile, "national_code": national_code},
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            timeout=15,
        )

        if resp.status_code != 200:
            return {"matched": False, "error": f"خطای سرویس شاهکار (کد {resp.status_code})"}

        data = resp.json()

        # Zohal API returns matched status in response
        matched = data.get("matched", False)
        if matched:
            return {"matched": True}
        else:
            return {"matched": False, "error": "موبایل و کد ملی وارد شده مطابقت ندارند."}

    except httpx.TimeoutException:
        return {"matched": False, "error": "سرویس شاهکار پاسخ نداد. لطفاً دوباره تلاش کنید."}
    except Exception:
        return {"matched": False, "error": "خطا در ارتباط با سرویس شاهکار."}
