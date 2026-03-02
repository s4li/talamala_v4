"""
Ticket Service - Business Logic
==================================
Create, list, reply, and manage support tickets.
Supports file attachments, categories, internal notes, search, notifications.
"""

import logging
from typing import List, Tuple, Dict, Any, Optional
from fastapi import UploadFile
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func as sa_func, or_

from modules.ticket.models import (
    Ticket, TicketMessage, TicketAttachment,
    TicketStatus, TicketPriority, TicketCategory, SenderType,
)
from modules.user.models import User
from common.helpers import now_utc
from common.upload import save_upload_file
from modules.notification.service import notification_service
from modules.notification.models import NotificationType

logger = logging.getLogger("talamala.ticket")


def _safe_int(val: str) -> int:
    """Convert search term to int for ID matching, returns -1 if not numeric."""
    try:
        return int(val.strip())
    except (ValueError, TypeError):
        return -1


class TicketService:

    # ------------------------------------------
    # Helpers
    # ------------------------------------------

    def _get_sender_name(self, db: Session, sender_type: str, sender_id: int) -> str:
        """Look up sender name from user."""
        u = db.query(User).filter(User.id == sender_id).first()
        if not u:
            if sender_type == SenderType.CUSTOMER:
                return "مشتری"
            elif sender_type == SenderType.DEALER:
                return "نماینده"
            return "ناشناس"
        return u.full_name or ("مشتری" if sender_type == SenderType.CUSTOMER else "نماینده")

    def _save_attachments(self, db: Session, message_id: int, files: List[UploadFile]):
        """Save uploaded files as TicketAttachment records."""
        if not files:
            return
        for f in files:
            if not f or not f.filename:
                continue
            path = save_upload_file(f, subfolder="tickets")
            if path:
                db.add(TicketAttachment(message_id=message_id, file_path=path))
        db.flush()

    def _send_notification(self, ticket: Ticket, sender_type: str):
        """Send SMS + in-app notification to the other party (non-blocking)."""
        try:
            from config.database import SessionLocal
            _db = SessionLocal()
            try:
                if sender_type == SenderType.STAFF:
                    # Notify ticket owner (customer or dealer)
                    if ticket.user:
                        notification_service.send(
                            _db, ticket.user_id,
                            notification_type=NotificationType.TICKET_UPDATE,
                            title=f"پاسخ جدید تیکت #{ticket.id}",
                            body=f"پشتیبانی به تیکت «{ticket.subject}» پاسخ داد.",
                            link=f"/tickets/{ticket.id}",
                            sms_text=f"طلاملا: پاسخ جدید تیکت #{ticket.id}. talamala.com/tickets/{ticket.id}",
                            reference_type="ticket_reply", reference_id=str(ticket.id),
                        )
                elif sender_type in (SenderType.CUSTOMER, SenderType.DEALER):
                    # Notify assigned staff (if any)
                    if ticket.assigned_staff:
                        notification_service.send(
                            _db, ticket.assigned_to,
                            notification_type=NotificationType.TICKET_UPDATE,
                            title=f"پاسخ جدید تیکت #{ticket.id}",
                            body=f"کاربر به تیکت «{ticket.subject}» پاسخ داد.",
                            link=f"/admin/tickets/{ticket.id}",
                            sms_text=f"طلاملا: پاسخ جدید تیکت #{ticket.id}",
                            reference_type="ticket_reply_staff", reference_id=str(ticket.id),
                        )
                _db.commit()
            finally:
                _db.close()
        except Exception as e:
            logger.error(f"Notification error: {e}")

    # ------------------------------------------
    # Create Ticket
    # ------------------------------------------

    def create_ticket(
        self, db: Session,
        sender_type: str,
        sender_id: int,
        subject: str,
        body: str,
        priority: str = TicketPriority.MEDIUM,
        category: str = TicketCategory.OTHER,
        files: List[UploadFile] = None,
    ) -> Dict[str, Any]:
        if not subject.strip() or not body.strip():
            return {"success": False, "message": "موضوع و متن تیکت الزامی است"}

        ticket = Ticket(
            subject=subject.strip(),
            body=body.strip(),
            sender_type=sender_type,
            priority=priority,
            category=category,
            status=TicketStatus.OPEN,
            user_id=sender_id,
        )

        if sender_type not in (SenderType.CUSTOMER, SenderType.DEALER):
            return {"success": False, "message": "نوع فرستنده نامعتبر"}

        db.add(ticket)
        db.flush()

        # Create initial message (for attachments support)
        sender_name = self._get_sender_name(db, sender_type, sender_id)
        initial_msg = TicketMessage(
            ticket_id=ticket.id,
            sender_type=sender_type,
            sender_name=sender_name,
            body=body.strip(),
            is_initial=True,
            is_internal=False,
        )
        db.add(initial_msg)
        db.flush()

        # Save attachments on initial message
        if files:
            self._save_attachments(db, initial_msg.id, files)

        return {
            "success": True,
            "message": f"تیکت #{ticket.id} با موفقیت ایجاد شد",
            "ticket": ticket,
        }

    # ------------------------------------------
    # List Tickets (Customer)
    # ------------------------------------------

    def list_tickets_for_customer(
        self, db: Session, customer_id: int,
        page: int = 1, per_page: int = 20,
    ) -> Tuple[List[Ticket], int]:
        q = db.query(Ticket).filter(Ticket.user_id == customer_id, Ticket.sender_type == SenderType.CUSTOMER)
        total = q.count()
        tickets = (
            q.order_by(Ticket.updated_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        return tickets, total

    # ------------------------------------------
    # List Tickets (Dealer)
    # ------------------------------------------

    def list_tickets_for_dealer(
        self, db: Session, dealer_id: int,
        page: int = 1, per_page: int = 20,
    ) -> Tuple[List[Ticket], int]:
        q = db.query(Ticket).filter(Ticket.user_id == dealer_id, Ticket.sender_type == SenderType.DEALER)
        total = q.count()
        tickets = (
            q.order_by(Ticket.updated_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        return tickets, total

    # ------------------------------------------
    # List Tickets (Admin) — with search + category filter
    # ------------------------------------------

    def list_tickets_admin(
        self, db: Session,
        page: int = 1, per_page: int = 30,
        status_filter: str = None,
        sender_type_filter: str = None,
        category_filter: str = None,
        search: str = None,
    ) -> Tuple[List[Ticket], int]:
        q = db.query(Ticket).options(
            joinedload(Ticket.user),
            joinedload(Ticket.assigned_staff),
        )
        if status_filter:
            q = q.filter(Ticket.status == status_filter)
        if sender_type_filter:
            q = q.filter(Ticket.sender_type == sender_type_filter)
        if category_filter:
            q = q.filter(Ticket.category == category_filter)

        if search and search.strip():
            term = f"%{search.strip()}%"
            search_id = _safe_int(search)
            q = q.outerjoin(User, Ticket.user_id == User.id)
            q = q.filter(
                or_(
                    Ticket.id == search_id,
                    Ticket.subject.ilike(term),
                    User.first_name.ilike(term),
                    User.last_name.ilike(term),
                    User.mobile.ilike(term),
                )
            )

        total = q.count()
        tickets = (
            q.order_by(Ticket.updated_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        return tickets, total

    # ------------------------------------------
    # Get Ticket Detail
    # ------------------------------------------

    def get_ticket(self, db: Session, ticket_id: int) -> Optional[Ticket]:
        return (
            db.query(Ticket)
            .options(
                joinedload(Ticket.messages).joinedload(TicketMessage.attachments),
                joinedload(Ticket.user),
                joinedload(Ticket.assigned_staff),
            )
            .filter(Ticket.id == ticket_id)
            .first()
        )

    # ------------------------------------------
    # Add Message (Reply) — with files + internal notes
    # ------------------------------------------

    def add_message(
        self, db: Session,
        ticket_id: int,
        sender_type: str,
        sender_name: str,
        body: str,
        files: List[UploadFile] = None,
        is_internal: bool = False,
    ) -> Dict[str, Any]:
        ticket = db.query(Ticket).options(
            joinedload(Ticket.user),
            joinedload(Ticket.assigned_staff),
        ).filter(Ticket.id == ticket_id).first()
        if not ticket:
            return {"success": False, "message": "تیکت یافت نشد"}
        if ticket.status == TicketStatus.CLOSED:
            return {"success": False, "message": "این تیکت بسته شده و امکان ارسال پیام نیست"}
        if not body.strip():
            return {"success": False, "message": "متن پیام نمی‌تواند خالی باشد"}

        msg = TicketMessage(
            ticket_id=ticket_id,
            sender_type=sender_type,
            sender_name=sender_name.strip(),
            body=body.strip(),
            is_internal=is_internal,
        )
        db.add(msg)
        db.flush()

        # Save attachments
        if files:
            self._save_attachments(db, msg.id, files)

        # Auto-update ticket status (only for non-internal messages)
        if not is_internal:
            if sender_type == SenderType.STAFF:
                ticket.status = TicketStatus.ANSWERED
            elif sender_type in (SenderType.CUSTOMER, SenderType.DEALER):
                if ticket.status == TicketStatus.ANSWERED:
                    ticket.status = TicketStatus.OPEN

        ticket.updated_at = now_utc()
        db.flush()

        # Send notification (non-internal only)
        if not is_internal:
            self._send_notification(ticket, sender_type)

        return {"success": True, "message": "پیام ارسال شد", "ticket_message": msg}

    # ------------------------------------------
    # Update Status
    # ------------------------------------------

    def update_status(
        self, db: Session,
        ticket_id: int,
        new_status: str,
    ) -> Dict[str, Any]:
        ticket = db.query(Ticket).options(
            joinedload(Ticket.user),
        ).filter(Ticket.id == ticket_id).first()
        if not ticket:
            return {"success": False, "message": "تیکت یافت نشد"}

        ticket.status = new_status
        if new_status == TicketStatus.CLOSED:
            ticket.closed_at = now_utc()
        else:
            ticket.updated_at = now_utc()

        db.flush()

        # Notify ticket owner of status change
        try:
            if ticket.user:
                notification_service.send(
                    db, ticket.user_id,
                    notification_type=NotificationType.TICKET_UPDATE,
                    title=f"تغییر وضعیت تیکت #{ticket.id}",
                    body=f"وضعیت تیکت «{ticket.subject}» تغییر کرد.",
                    link=f"/tickets/{ticket.id}",
                    sms_text=f"طلاملا: وضعیت تیکت #{ticket.id} تغییر کرد. talamala.com/tickets/{ticket.id}",
                    reference_type="ticket_status", reference_id=str(ticket.id),
                )
        except Exception as e:
            logger.error(f"Notification error on status change for ticket #{ticket_id}: {e}")

        return {"success": True, "message": "وضعیت تیکت بروزرسانی شد"}

    # ------------------------------------------
    # Close Ticket
    # ------------------------------------------

    def close_ticket(self, db: Session, ticket_id: int) -> Dict[str, Any]:
        return self.update_status(db, ticket_id, TicketStatus.CLOSED)

    # ------------------------------------------
    # Assign Ticket
    # ------------------------------------------

    def assign_ticket(
        self, db: Session,
        ticket_id: int,
        staff_id: int,
    ) -> Dict[str, Any]:
        ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
        if not ticket:
            return {"success": False, "message": "تیکت یافت نشد"}

        ticket.assigned_to = staff_id
        if ticket.status == TicketStatus.OPEN:
            ticket.status = TicketStatus.IN_PROGRESS
        ticket.updated_at = now_utc()
        db.flush()
        return {"success": True, "message": "تیکت تخصیص داده شد"}

    # ------------------------------------------
    # Change Category (Department Transfer)
    # ------------------------------------------

    def change_category(
        self, db: Session,
        ticket_id: int,
        new_category: str,
    ) -> Dict[str, Any]:
        ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
        if not ticket:
            return {"success": False, "message": "تیکت یافت نشد"}

        # Validate category
        valid = [c.value for c in TicketCategory]
        if new_category not in valid:
            return {"success": False, "message": "دپارتمان نامعتبر"}

        if ticket.category == new_category:
            return {"success": True, "message": "دپارتمان تغییری نکرد"}

        # Category label for message
        labels = {
            TicketCategory.FINANCIAL: "مالی",
            TicketCategory.TECHNICAL: "فنی",
            TicketCategory.SALES: "فروش",
            TicketCategory.COMPLAINTS: "شکایات",
            TicketCategory.OTHER: "سایر",
        }
        old_label = labels.get(ticket.category, ticket.category)
        new_label = labels.get(new_category, new_category)

        ticket.category = new_category
        ticket.updated_at = now_utc()

        # Log internal note for audit trail
        note = TicketMessage(
            ticket_id=ticket.id,
            sender_type=SenderType.STAFF,
            sender_name="سیستم",
            body=f"تیکت از دپارتمان «{old_label}» به «{new_label}» منتقل شد.",
            is_internal=True,
        )
        db.add(note)

        # Notify ticket owner
        try:
            if ticket.user:
                notification_service.send(
                    db, ticket.user_id,
                    notification_type=NotificationType.TICKET_UPDATE,
                    title=f"انتقال تیکت #{ticket.id}",
                    body=f"تیکت «{ticket.subject}» به دپارتمان «{new_label}» منتقل شد.",
                    link=f"/tickets/{ticket.id}",
                    sms_text=f"طلاملا: تیکت #{ticket.id} به دپارتمان جدید منتقل شد.",
                    reference_type="ticket_category", reference_id=str(ticket.id),
                )
        except Exception as e:
            logger.error(f"Notification error on category change for ticket #{ticket_id}: {e}")

        db.flush()
        return {"success": True, "message": f"تیکت به دپارتمان «{new_label}» منتقل شد"}

    # ------------------------------------------
    # Admin Stats
    # ------------------------------------------

    def get_admin_stats(self, db: Session) -> Dict[str, Any]:
        total = db.query(Ticket).count()
        open_count = db.query(Ticket).filter(Ticket.status == TicketStatus.OPEN).count()
        in_progress = db.query(Ticket).filter(Ticket.status == TicketStatus.IN_PROGRESS).count()
        answered = db.query(Ticket).filter(Ticket.status == TicketStatus.ANSWERED).count()
        closed = db.query(Ticket).filter(Ticket.status == TicketStatus.CLOSED).count()
        customer_count = db.query(Ticket).filter(Ticket.sender_type == SenderType.CUSTOMER).count()
        dealer_count = db.query(Ticket).filter(Ticket.sender_type == SenderType.DEALER).count()

        cat_counts = {}
        for cat in TicketCategory:
            cat_counts[cat.value] = db.query(Ticket).filter(Ticket.category == cat).count()

        return {
            "total": total,
            "open": open_count,
            "in_progress": in_progress,
            "answered": answered,
            "closed": closed,
            "customer_count": customer_count,
            "dealer_count": dealer_count,
            "categories": cat_counts,
        }


ticket_service = TicketService()
