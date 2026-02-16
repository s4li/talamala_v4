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
from modules.customer.models import Customer
from modules.dealer.models import Dealer
from common.helpers import now_utc
from common.upload import save_upload_file
from common.notifications import notify_ticket_update

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
        """Look up sender name from customer/dealer."""
        if sender_type == SenderType.CUSTOMER:
            c = db.query(Customer).filter(Customer.id == sender_id).first()
            return (c.full_name or "مشتری") if c else "مشتری"
        elif sender_type == SenderType.DEALER:
            d = db.query(Dealer).filter(Dealer.id == sender_id).first()
            return d.full_name if d else "نماینده"
        return "ناشناس"

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
        """Send SMS notification to the other party (non-blocking)."""
        try:
            if sender_type == SenderType.STAFF:
                # Notify customer or dealer
                if ticket.sender_type == SenderType.CUSTOMER and ticket.customer:
                    notify_ticket_update(ticket.customer.mobile, ticket.id, "new_reply")
                elif ticket.sender_type == SenderType.DEALER and ticket.dealer:
                    notify_ticket_update(ticket.dealer.mobile, ticket.id, "new_reply")
            elif sender_type in (SenderType.CUSTOMER, SenderType.DEALER):
                # Notify assigned staff (if any)
                if ticket.assigned_staff and getattr(ticket.assigned_staff, "mobile", None):
                    notify_ticket_update(ticket.assigned_staff.mobile, ticket.id, "new_reply")
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
        )

        if sender_type == SenderType.CUSTOMER:
            ticket.customer_id = sender_id
        elif sender_type == SenderType.DEALER:
            ticket.dealer_id = sender_id
        else:
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
        q = db.query(Ticket).filter(Ticket.customer_id == customer_id)
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
        q = db.query(Ticket).filter(Ticket.dealer_id == dealer_id)
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
            joinedload(Ticket.customer),
            joinedload(Ticket.dealer),
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
            q = q.outerjoin(Customer, Ticket.customer_id == Customer.id)
            q = q.outerjoin(Dealer, Ticket.dealer_id == Dealer.id)
            q = q.filter(
                or_(
                    Ticket.id == search_id,
                    Ticket.subject.ilike(term),
                    Customer.full_name.ilike(term),
                    Customer.mobile.ilike(term),
                    Dealer.full_name.ilike(term),
                    Dealer.mobile.ilike(term),
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
                joinedload(Ticket.customer),
                joinedload(Ticket.dealer),
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
            joinedload(Ticket.customer),
            joinedload(Ticket.dealer),
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
            joinedload(Ticket.customer),
            joinedload(Ticket.dealer),
        ).filter(Ticket.id == ticket_id).first()
        if not ticket:
            return {"success": False, "message": "تیکت یافت نشد"}

        ticket.status = new_status
        if new_status == TicketStatus.CLOSED:
            ticket.closed_at = now_utc()
        else:
            ticket.updated_at = now_utc()

        db.flush()

        # Notify customer/dealer of status change
        try:
            if ticket.sender_type == SenderType.CUSTOMER and ticket.customer:
                notify_ticket_update(ticket.customer.mobile, ticket.id, "status_changed")
            elif ticket.sender_type == SenderType.DEALER and ticket.dealer:
                notify_ticket_update(ticket.dealer.mobile, ticket.id, "status_changed")
        except Exception:
            pass

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

        ticket.category = new_category
        ticket.updated_at = now_utc()
        db.flush()
        return {"success": True, "message": "دپارتمان تیکت تغییر کرد"}

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
