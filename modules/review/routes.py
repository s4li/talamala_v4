"""
Review Module - Customer Routes
==================================
Submit reviews (from order page), add comments/Q&A (from product page).
"""

from typing import Optional, List

from fastapi import APIRouter, Request, Depends, Form, UploadFile, File
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from config.database import get_db
from common.security import csrf_check
from modules.auth.deps import require_customer, get_current_active_user
from modules.review.service import review_service
from modules.review.models import CommentSenderType

router = APIRouter(tags=["reviews"])


# ==========================================
# Submit Review (from order detail page)
# ==========================================

@router.post("/reviews/submit")
async def submit_review(
    request: Request,
    order_item_id: int = Form(...),
    product_id: int = Form(...),
    order_id: int = Form(...),
    rating: int = Form(...),
    body: str = Form(""),
    csrf_token: str = Form(""),
    files: List[UploadFile] = File(default=[]),
    me=Depends(require_customer),
    db: Session = Depends(get_db),
):
    csrf_check(request, csrf_token)

    result = review_service.create_review(
        db,
        customer_id=me.id,
        order_item_id=order_item_id,
        product_id=product_id,
        rating=rating,
        body=body,
        files=files if files else None,
    )

    if result["success"]:
        db.commit()
        return RedirectResponse(f"/orders/{order_id}?msg=نظر+شما+ثبت+شد", status_code=302)

    db.rollback()
    return RedirectResponse(f"/orders/{order_id}?error={result['message']}", status_code=302)


# ==========================================
# Add Comment on Product Page
# ==========================================

@router.post("/product/{product_id}/comment")
async def add_product_comment(
    request: Request,
    product_id: int,
    me=Depends(require_customer),
    db: Session = Depends(get_db),
):
    form_data = await request.form()
    csrf_token = form_data.get("csrf_token", "")
    csrf_check(request, csrf_token)

    body = form_data.get("body", "")
    parent_id_raw = form_data.get("parent_id")
    parent_id = int(parent_id_raw) if parent_id_raw else None

    # Only buyers can upload images
    has_purchased = review_service.customer_has_purchased(db, me.id, product_id)
    upload_files = None
    if has_purchased:
        raw_files = form_data.getlist("files")
        valid = [f for f in raw_files if isinstance(f, UploadFile) and f.filename]
        upload_files = valid or None

    sender_name = me.full_name or "مشتری"

    result = review_service.add_comment(
        db,
        product_id=product_id,
        customer_id=me.id,
        sender_name=sender_name,
        body=body,
        sender_type=CommentSenderType.CUSTOMER,
        parent_id=parent_id,
        files=upload_files,
    )

    if result["success"]:
        db.commit()
    else:
        db.rollback()

    return RedirectResponse(f"/product/{product_id}#comments", status_code=302)
