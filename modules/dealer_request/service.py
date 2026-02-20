"""
Dealer Request Service - Business Logic
==========================================
Handle dealer request submissions and admin management.
"""

from typing import List, Tuple, Dict, Any, Optional
from fastapi import UploadFile
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func as sa_func, or_

from modules.dealer_request.models import (
    DealerRequest, DealerRequestAttachment, DealerRequestStatus,
)
from common.upload import save_upload_file
from common.helpers import now_utc


class DealerRequestService:

    # ------------------------------------------
    # Create
    # ------------------------------------------

    def create_request(
        self,
        db: Session,
        customer_id: int,
        first_name: str,
        last_name: str,
        mobile: str,
        province_id: int,
        city_id: int,
        birth_date: str = "",
        email: str = "",
        gender: str = "",
        files: List[UploadFile] = None,
    ) -> Dict[str, Any]:
        """Create a new dealer request. Prevents duplicate PENDING requests."""

        # Check for existing PENDING or REVISION_NEEDED request
        existing = db.query(DealerRequest).filter(
            DealerRequest.customer_id == customer_id,
            DealerRequest.status.in_([
                DealerRequestStatus.PENDING.value,
                DealerRequestStatus.REVISION_NEEDED.value,
            ]),
        ).first()
        if existing:
            return {"success": False, "message": "\u0634\u0645\u0627 \u06cc\u06a9 \u062f\u0631\u062e\u0648\u0627\u0633\u062a \u062f\u0631 \u062d\u0627\u0644 \u0628\u0631\u0631\u0633\u06cc \u062f\u0627\u0631\u06cc\u062f."}

        req = DealerRequest(
            customer_id=customer_id,
            first_name=first_name.strip(),
            last_name=last_name.strip(),
            birth_date=birth_date.strip() or None,
            email=email.strip() or None,
            mobile=mobile.strip(),
            gender=gender or None,
            province_id=province_id or None,
            city_id=city_id or None,
        )
        db.add(req)
        db.flush()

        # Save attachments
        self._save_attachments(db, req.id, files or [])

        return {"success": True, "message": "\u062f\u0631\u062e\u0648\u0627\u0633\u062a \u0634\u0645\u0627 \u0628\u0627 \u0645\u0648\u0641\u0642\u06cc\u062a \u062b\u0628\u062a \u0634\u062f.", "request": req}

    # ------------------------------------------
    # Customer Queries
    # ------------------------------------------

    def get_active_request(self, db: Session, customer_id: int) -> Optional[DealerRequest]:
        """Return the customer's PENDING, REVISION_NEEDED, or most recent APPROVED request."""
        return db.query(DealerRequest).filter(
            DealerRequest.customer_id == customer_id,
            DealerRequest.status.in_([
                DealerRequestStatus.PENDING.value,
                DealerRequestStatus.APPROVED.value,
                DealerRequestStatus.REVISION_NEEDED.value,
            ]),
        ).order_by(DealerRequest.created_at.desc()).first()

    def get_request_by_customer(self, db: Session, customer_id: int) -> Optional[DealerRequest]:
        """Return the most recent request for a customer (any status)."""
        return db.query(DealerRequest).filter(
            DealerRequest.customer_id == customer_id,
        ).order_by(DealerRequest.created_at.desc()).first()

    # ------------------------------------------
    # Admin Queries
    # ------------------------------------------

    def list_requests(
        self,
        db: Session,
        page: int = 1,
        per_page: int = 30,
        status_filter: str = None,
        search: str = None,
    ) -> Tuple[List[DealerRequest], int]:
        """List dealer requests with optional filters."""
        q = db.query(DealerRequest).options(
            joinedload(DealerRequest.province),
            joinedload(DealerRequest.city),
        )

        if status_filter:
            q = q.filter(DealerRequest.status == status_filter)

        if search:
            term = f"%{search}%"
            q = q.filter(or_(
                DealerRequest.first_name.ilike(term),
                DealerRequest.last_name.ilike(term),
                DealerRequest.mobile.ilike(term),
                DealerRequest.email.ilike(term),
            ))

        total = q.count()
        items = q.order_by(DealerRequest.created_at.desc())\
            .offset((page - 1) * per_page).limit(per_page).all()

        return items, total

    def get_request(self, db: Session, request_id: int) -> Optional[DealerRequest]:
        """Get a single request with attachments."""
        return db.query(DealerRequest).options(
            joinedload(DealerRequest.attachments),
            joinedload(DealerRequest.province),
            joinedload(DealerRequest.city),
            joinedload(DealerRequest.customer),
        ).filter(DealerRequest.id == request_id).first()

    def get_stats(self, db: Session) -> Dict[str, int]:
        """Count requests by status."""
        rows = db.query(DealerRequest.status, sa_func.count())\
            .group_by(DealerRequest.status).all()
        stats = {s: 0 for s in ["Pending", "Approved", "Rejected", "RevisionNeeded"]}
        for status_val, cnt in rows:
            stats[status_val] = cnt
        stats["total"] = sum(stats.values())
        return stats

    # ------------------------------------------
    # Admin Actions
    # ------------------------------------------

    def approve_request(self, db: Session, request_id: int, admin_note: str = "") -> Dict[str, Any]:
        req = db.query(DealerRequest).filter(DealerRequest.id == request_id).first()
        if not req:
            return {"success": False, "message": "\u062f\u0631\u062e\u0648\u0627\u0633\u062a \u06cc\u0627\u0641\u062a \u0646\u0634\u062f."}
        if req.status != DealerRequestStatus.PENDING.value:
            return {"success": False, "message": "\u0641\u0642\u0637 \u062f\u0631\u062e\u0648\u0627\u0633\u062a\u200c\u0647\u0627\u06cc \u062f\u0631 \u0627\u0646\u062a\u0638\u0627\u0631 \u0642\u0627\u0628\u0644 \u062a\u0627\u06cc\u06cc\u062f \u0647\u0633\u062a\u0646\u062f."}

        req.status = DealerRequestStatus.APPROVED.value
        req.admin_note = admin_note.strip() or None
        req.updated_at = now_utc()
        db.flush()
        return {"success": True, "message": "\u062f\u0631\u062e\u0648\u0627\u0633\u062a \u062a\u0627\u06cc\u06cc\u062f \u0634\u062f."}

    def request_revision(self, db: Session, request_id: int, admin_note: str = "") -> Dict[str, Any]:
        req = db.query(DealerRequest).filter(DealerRequest.id == request_id).first()
        if not req:
            return {"success": False, "message": "\u062f\u0631\u062e\u0648\u0627\u0633\u062a \u06cc\u0627\u0641\u062a \u0646\u0634\u062f."}
        if req.status != DealerRequestStatus.PENDING.value:
            return {"success": False, "message": "\u0641\u0642\u0637 \u062f\u0631\u062e\u0648\u0627\u0633\u062a\u200c\u0647\u0627\u06cc \u062f\u0631 \u0627\u0646\u062a\u0638\u0627\u0631 \u0642\u0627\u0628\u0644 \u0627\u0631\u0633\u0627\u0644 \u0628\u0631\u0627\u06cc \u0627\u0635\u0644\u0627\u062d \u0647\u0633\u062a\u0646\u062f."}

        req.status = DealerRequestStatus.REVISION_NEEDED.value
        req.admin_note = admin_note.strip() or None
        req.updated_at = now_utc()
        db.flush()
        return {"success": True, "message": "\u062f\u0631\u062e\u0648\u0627\u0633\u062a \u0628\u0631\u0627\u06cc \u0627\u0635\u0644\u0627\u062d \u0627\u0631\u0633\u0627\u0644 \u0634\u062f."}

    def reject_request(self, db: Session, request_id: int, admin_note: str = "") -> Dict[str, Any]:
        req = db.query(DealerRequest).filter(DealerRequest.id == request_id).first()
        if not req:
            return {"success": False, "message": "\u062f\u0631\u062e\u0648\u0627\u0633\u062a \u06cc\u0627\u0641\u062a \u0646\u0634\u062f."}
        if req.status != DealerRequestStatus.PENDING.value:
            return {"success": False, "message": "\u0641\u0642\u0637 \u062f\u0631\u062e\u0648\u0627\u0633\u062a\u200c\u0647\u0627\u06cc \u062f\u0631 \u0627\u0646\u062a\u0638\u0627\u0631 \u0642\u0627\u0628\u0644 \u0631\u062f \u0647\u0633\u062a\u0646\u062f."}

        req.status = DealerRequestStatus.REJECTED.value
        req.admin_note = admin_note.strip() or None
        req.updated_at = now_utc()
        db.flush()
        return {"success": True, "message": "\u062f\u0631\u062e\u0648\u0627\u0633\u062a \u0631\u062f \u0634\u062f."}

    # ------------------------------------------
    # Customer Resubmit (edit RevisionNeeded request)
    # ------------------------------------------

    def update_request(
        self,
        db: Session,
        request_id: int,
        customer_id: int,
        first_name: str,
        last_name: str,
        mobile: str,
        province_id: int,
        city_id: int,
        birth_date: str = "",
        email: str = "",
        gender: str = "",
        files: List[UploadFile] = None,
    ) -> Dict[str, Any]:
        """Update a RevisionNeeded request and resubmit as Pending."""
        req = db.query(DealerRequest).filter(
            DealerRequest.id == request_id,
            DealerRequest.customer_id == customer_id,
            DealerRequest.status == DealerRequestStatus.REVISION_NEEDED.value,
        ).first()
        if not req:
            return {"success": False, "message": "\u062f\u0631\u062e\u0648\u0627\u0633\u062a \u0642\u0627\u0628\u0644 \u0648\u06cc\u0631\u0627\u06cc\u0634 \u06cc\u0627\u0641\u062a \u0646\u0634\u062f."}

        req.first_name = first_name.strip()
        req.last_name = last_name.strip()
        req.mobile = mobile.strip()
        req.birth_date = birth_date.strip() or None
        req.email = email.strip() or None
        req.gender = gender or None
        req.province_id = province_id or None
        req.city_id = city_id or None
        req.status = DealerRequestStatus.PENDING.value
        req.admin_note = None
        req.updated_at = now_utc()
        db.flush()

        # Save new attachments (keep existing ones)
        self._save_attachments(db, req.id, files or [])

        return {"success": True, "message": "\u062f\u0631\u062e\u0648\u0627\u0633\u062a \u0628\u0627 \u0645\u0648\u0641\u0642\u06cc\u062a \u0627\u0635\u0644\u0627\u062d \u0648 \u0627\u0631\u0633\u0627\u0644 \u0634\u062f."}

    # ------------------------------------------
    # File Attachments
    # ------------------------------------------

    def _save_attachments(self, db: Session, request_id: int, files: List[UploadFile]):
        if not files:
            return
        for f in files:
            if not f or not f.filename:
                continue
            path = save_upload_file(f, subfolder="dealer_requests")
            if path:
                db.add(DealerRequestAttachment(
                    dealer_request_id=request_id,
                    file_path=path,
                    original_filename=f.filename,
                ))
        db.flush()


dealer_request_service = DealerRequestService()
