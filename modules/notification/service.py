"""
TalaMala v4 - Notification Service
=====================================
Central dispatcher for all notifications: in-app + SMS (async) + email (stub).
Respects per-user preferences. SMS is sent via BackgroundTasks to avoid blocking.
"""

import logging
from typing import Optional, Tuple, List, Dict

from sqlalchemy.orm import Session
from sqlalchemy import desc

from modules.notification.models import (
    Notification, NotificationPreference,
    NotificationType, NotificationChannel, NOTIFICATION_TYPE_LABELS,
)

logger = logging.getLogger("talamala.notification")


class NotificationService:

    # ------------------------------------------------------------------
    # Core: Send Notification
    # ------------------------------------------------------------------

    def send(
        self,
        db: Session,
        user_id: int,
        notification_type: str,
        title: str,
        body: str,
        link: str = None,
        sms_text: str = None,
        sms_mobile: str = None,
        reference_type: str = None,
        reference_id: str = None,
        metadata: dict = None,
        background_tasks=None,
    ) -> Optional[Notification]:
        """
        Central dispatcher. Creates in-app notification (sync) and sends SMS (async).

        Args:
            db: DB session (caller manages commit)
            user_id: Target user
            notification_type: NotificationType enum value (string)
            title: Short title (shown in list)
            body: Full message body
            link: URL to navigate on click (nullable)
            sms_text: SMS message text (if None, SMS is skipped)
            sms_mobile: Override mobile (default: user's mobile from DB)
            reference_type: For dedup ("order", "ticket", etc.)
            reference_id: For dedup ("123")
            metadata: Extra JSON data
            background_tasks: FastAPI BackgroundTasks (SMS runs async if provided)

        Returns:
            Notification object or None
        """
        # 1. Check preferences
        prefs = self._get_preferences(db, user_id, notification_type)

        # 2. Create IN_APP notification (synchronous — participates in caller's transaction)
        notif = None
        if prefs["in_app"]:
            notif = Notification(
                user_id=user_id,
                notification_type=notification_type,
                title=title,
                body=body,
                link=link,
                channel=NotificationChannel.IN_APP,
                reference_type=reference_type,
                reference_id=reference_id,
                metadata_json=metadata,
            )
            db.add(notif)
            db.flush()

        # 3. Send SMS (async via BackgroundTasks, or sync fallback)
        if prefs["sms"] and sms_text:
            mobile = sms_mobile
            if not mobile:
                from modules.user.models import User
                user = db.query(User).filter(User.id == user_id).first()
                mobile = user.mobile if user else None

            if mobile:
                if background_tasks is not None:
                    background_tasks.add_task(self._send_sms, mobile, sms_text)
                else:
                    self._send_sms(mobile, sms_text)

        # 4. Email stub (log only — no SMTP configured)
        if prefs["email"]:
            logger.info(f"[EMAIL STUB] To user #{user_id}: {title}")

        return notif

    # ------------------------------------------------------------------
    # Preferences
    # ------------------------------------------------------------------

    def _get_preferences(self, db: Session, user_id: int, notification_type: str) -> Dict[str, bool]:
        """Get user's channel preferences for a notification type."""
        pref = db.query(NotificationPreference).filter(
            NotificationPreference.user_id == user_id,
            NotificationPreference.notification_type == notification_type,
        ).first()

        if pref:
            return {
                "sms": pref.sms_enabled,
                "in_app": pref.in_app_enabled,
                "email": pref.email_enabled,
            }

        # Default: SMS + In-app enabled, email disabled
        return {"sms": True, "in_app": True, "email": False}

    def get_all_preferences(self, db: Session, user_id: int) -> Dict[str, Dict[str, bool]]:
        """Get all preferences for settings page."""
        existing = db.query(NotificationPreference).filter(
            NotificationPreference.user_id == user_id,
        ).all()

        pref_map = {}
        for p in existing:
            pref_map[p.notification_type] = {
                "sms": p.sms_enabled,
                "in_app": p.in_app_enabled,
                "email": p.email_enabled,
            }

        result = {}
        for nt in NotificationType:
            if nt.value in pref_map:
                result[nt.value] = pref_map[nt.value]
            else:
                result[nt.value] = {"sms": True, "in_app": True, "email": False}

        return result

    def save_preferences(self, db: Session, user_id: int, prefs: Dict[str, Dict[str, bool]]):
        """Save bulk preferences from settings form."""
        for type_val, channels in prefs.items():
            existing = db.query(NotificationPreference).filter(
                NotificationPreference.user_id == user_id,
                NotificationPreference.notification_type == type_val,
            ).first()

            if existing:
                existing.sms_enabled = channels.get("sms", True)
                existing.in_app_enabled = channels.get("in_app", True)
                existing.email_enabled = channels.get("email", False)
            else:
                db.add(NotificationPreference(
                    user_id=user_id,
                    notification_type=type_val,
                    sms_enabled=channels.get("sms", True),
                    in_app_enabled=channels.get("in_app", True),
                    email_enabled=channels.get("email", False),
                ))
        db.flush()

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_unread_count(self, db: Session, user_id: int) -> int:
        """Count of unread in-app notifications (for badge)."""
        return db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.is_read == False,
        ).count()

    def list_notifications(
        self, db: Session, user_id: int,
        page: int = 1, per_page: int = 20,
    ) -> Tuple[List[Notification], int]:
        """Paginated notification list for notification center."""
        q = db.query(Notification).filter(Notification.user_id == user_id)
        total = q.count()
        items = (
            q.order_by(desc(Notification.created_at))
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        return items, total

    def mark_as_read(self, db: Session, user_id: int, notification_id: int) -> bool:
        """Mark a single notification as read."""
        notif = db.query(Notification).filter(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        ).first()
        if notif and not notif.is_read:
            notif.is_read = True
            db.flush()
            return True
        return False

    def mark_all_read(self, db: Session, user_id: int) -> int:
        """Mark all unread notifications as read. Returns count updated."""
        count = db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.is_read == False,
        ).update({"is_read": True})
        db.flush()
        return count

    # ------------------------------------------------------------------
    # SMS Helper (runs in BackgroundTasks)
    # ------------------------------------------------------------------

    def _send_sms(self, mobile: str, text: str):
        """Send transactional SMS via the active SMS provider."""
        try:
            from common.sms import sms_sender
            sms_sender.send_plain_text(mobile, text)
        except Exception as e:
            logger.error(f"SMS send failed to {mobile}: {e}")


# Singleton
notification_service = NotificationService()
