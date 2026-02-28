"""
TalaMala v4 - Ticket Notification Helper
==========================================
Sends SMS notifications for ticket events via the active SMS provider.
Uses sms_sender.send_plain_text() (dynamic provider: sms.ir / Kavenegar).
"""

import logging

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
        "new_reply": f"طلاملا: پاسخ جدید برای تیکت #{ticket_id}",
        "status_changed": f"طلاملا: وضعیت تیکت #{ticket_id} تغییر کرد",
        "new_ticket": f"طلاملا: تیکت جدید #{ticket_id} ثبت شد",
    }

    text = messages.get(event_type, f"طلاملا: بروزرسانی تیکت #{ticket_id}")

    try:
        from common.sms import sms_sender
        return sms_sender.send_plain_text(mobile, text)
    except Exception as e:
        logger.error(f"Notification failed: {e}")
        return False
