"""
TalaMala v4 - Ticket Notification Helper
==========================================
Sends SMS notifications for ticket events.
In dev mode (no SMS_API_KEY), prints to console only.
"""

import logging
from config.settings import SMS_API_KEY

logger = logging.getLogger("talamala.notifications")


def notify_ticket_update(
    mobile: str,
    ticket_id: int,
    event_type: str,
) -> bool:
    """
    Send notification about a ticket event.

    Args:
        mobile: Recipient mobile number
        ticket_id: Ticket ID
        event_type: One of "new_reply", "status_changed", "new_ticket"

    Returns:
        True if notification sent (or logged), False on error
    """
    messages = {
        "new_reply": f"پاسخ جدیدی برای تیکت #{ticket_id} ارسال شده است. طلاملا",
        "status_changed": f"وضعیت تیکت #{ticket_id} تغییر کرد. طلاملا",
        "new_ticket": f"تیکت جدید #{ticket_id} ثبت شد. طلاملا",
    }

    text = messages.get(event_type, f"بروزرسانی تیکت #{ticket_id}")

    # Always log to console for debugging
    print(f"\n{'='*40}")
    print(f"TICKET NOTIFICATION (DEBUG)")
    print(f"  To: {mobile}")
    print(f"  Message: {text}")
    print(f"{'='*40}\n")

    if not SMS_API_KEY:
        logger.info(f"Notification skipped (no API key): {mobile} -> {text}")
        return False

    try:
        import requests
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        url = f"https://api.kavenegar.com/v1/{SMS_API_KEY}/sms/send.json"
        params = {
            "receptor": mobile,
            "message": text,
        }
        response = requests.get(url, params=params, timeout=5, verify=False)

        if response.status_code == 200:
            logger.info(f"Ticket notification sent to {mobile}")
            return True
        else:
            logger.error(f"Notification API error: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        logger.error(f"Notification failed: {e}")
        return False
