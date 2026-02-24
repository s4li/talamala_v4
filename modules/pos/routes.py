"""
POS Module - API Routes (Customer-Facing POS)
===============================================
Stateless JSON API for POS devices (customer-facing mode).
Auth: X-API-Key header (same as dealer API).

Endpoints:
  GET  /api/pos/categories          - Product categories with stock
  GET  /api/pos/products            - Products with pricing + stock count
  POST /api/pos/reserve             - Reserve a bar before card payment
  POST /api/pos/confirm             - Confirm sale after payment
  POST /api/pos/cancel              - Cancel reservation (payment failed)
  GET  /api/pos/receipt/{sale_id}   - Receipt data for printing
"""

import re
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from config.database import get_db
from config.settings import OTP_EXPIRE_MINUTES
from common.security import generate_otp, hash_otp, check_otp_rate_limit, check_otp_verify_rate_limit
from common.sms import sms_sender
from modules.user.models import User
from modules.dealer.auth_deps import get_dealer_by_api_key
from modules.dealer.service import dealer_service
from modules.pos.service import pos_service
from common.helpers import now_utc


router = APIRouter(prefix="/api/pos", tags=["pos-api"])


# ==========================================
# Schemas
# ==========================================

class ReserveRequest(BaseModel):
    product_id: int = Field(..., gt=0)


class ConfirmRequest(BaseModel):
    bar_id: int = Field(..., gt=0)
    payment_ref: str = Field("", max_length=100)
    payment_amount: int = Field(0, ge=0)
    customer_name: str = Field("", max_length=100)
    customer_mobile: str = Field("", max_length=11)
    customer_national_id: str = Field("", max_length=10)


class CancelRequest(BaseModel):
    bar_id: int = Field(..., gt=0)


class ActivationRequest(BaseModel):
    mobile: str = Field(..., min_length=11, max_length=11)


class ActivationVerify(BaseModel):
    mobile: str = Field(..., min_length=11, max_length=11)
    otp_code: str = Field(..., min_length=4, max_length=4)


# ==========================================
# POST /api/pos/request-activation (no auth)
# ==========================================

@router.post("/request-activation")
async def pos_request_activation(
    body: ActivationRequest,
    db: Session = Depends(get_db),
):
    """Send OTP to dealer's personal phone for POS device activation."""
    mobile = body.mobile.strip()

    # Validate Iranian mobile format
    if not re.match(r"^09\d{9}$", mobile):
        raise HTTPException(400, {"success": False, "error": "شماره موبایل نامعتبر"})

    # Find active dealer by mobile
    dealer = db.query(User).filter(
        User.mobile == mobile,
        User.is_dealer == True,
        User.is_active == True,
    ).first()
    if not dealer:
        raise HTTPException(404, {"success": False, "error": "نمایندگی با این شماره یافت نشد"})

    # Rate limit
    if not check_otp_rate_limit(mobile):
        raise HTTPException(429, {"success": False, "error": "درخواست زیاد! چند دقیقه صبر کنید."})

    # Generate & store OTP
    otp_raw = generate_otp(length=4)
    dealer.otp_code = hash_otp(mobile, otp_raw)
    dealer.otp_expiry = now_utc() + timedelta(minutes=OTP_EXPIRE_MINUTES)
    db.commit()

    # Send SMS
    display_name = dealer.first_name or "نمایندگی"
    sms_sent = sms_sender.send_otp_lookup(
        receptor=mobile,
        token=display_name,
        token2=otp_raw,
        template_name="OTP",
    )

    if not sms_sent:
        raise HTTPException(502, {"success": False, "error": "خطا در ارسال پیامک. لطفا دقایقی بعد تلاش کنید."})

    return {
        "success": True,
        "message": "کد تایید ارسال شد",
        "dealer_name": f"{dealer.first_name or ''} {dealer.last_name or ''}".strip() or "نمایندگی",
    }


# ==========================================
# POST /api/pos/verify-activation (no auth)
# ==========================================

@router.post("/verify-activation")
async def pos_verify_activation(
    body: ActivationVerify,
    db: Session = Depends(get_db),
):
    """Verify OTP and return API key for POS device activation."""
    mobile = body.mobile.strip()
    code = body.otp_code.strip()

    # Brute-force protection
    if not check_otp_verify_rate_limit(mobile):
        raise HTTPException(429, {"success": False, "error": "تعداد تلاش بیش از حد مجاز! چند دقیقه صبر کنید."})

    # Find dealer
    dealer = db.query(User).filter(
        User.mobile == mobile,
        User.is_dealer == True,
        User.is_active == True,
    ).first()
    if not dealer:
        raise HTTPException(404, {"success": False, "error": "نمایندگی یافت نشد"})

    # Verify OTP
    if not dealer.otp_code or not dealer.otp_expiry:
        raise HTTPException(400, {"success": False, "error": "ابتدا درخواست کد تایید بدهید"})

    if dealer.otp_expiry < now_utc():
        raise HTTPException(400, {"success": False, "error": "کد تایید منقضی شده. دوباره درخواست بدهید."})

    if dealer.otp_code != hash_otp(mobile, code):
        raise HTTPException(400, {"success": False, "error": "کد تایید اشتباه است"})

    # OTP valid — clear it
    dealer.otp_code = None
    dealer.otp_expiry = None

    # Ensure dealer has an API key
    if not dealer.api_key:
        dealer_service.generate_api_key(db, dealer.id)

    db.commit()

    return {
        "success": True,
        "api_key": dealer.api_key,
        "dealer_name": f"{dealer.first_name or ''} {dealer.last_name or ''}".strip() or "نمایندگی",
        "dealer_id": dealer.id,
    }


# ==========================================
# GET /api/pos/categories
# ==========================================

@router.get("/categories")
async def pos_categories(
    dealer: User = Depends(get_dealer_by_api_key),
    db: Session = Depends(get_db),
):
    """Product categories with available stock at dealer."""
    categories = pos_service.get_categories_for_dealer(db, dealer.id)
    return {"success": True, "categories": categories}


# ==========================================
# GET /api/pos/products
# ==========================================

@router.get("/products")
async def pos_products(
    category_id: Optional[int] = Query(None),
    dealer: User = Depends(get_dealer_by_api_key),
    db: Session = Depends(get_db),
):
    """Products with live pricing + stock count."""
    data = pos_service.get_products_for_pos(db, dealer.id, category_id)
    return {
        "success": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **data,
    }


# ==========================================
# POST /api/pos/reserve
# ==========================================

@router.post("/reserve")
async def pos_reserve(
    body: ReserveRequest,
    dealer: User = Depends(get_dealer_by_api_key),
    db: Session = Depends(get_db),
):
    """Reserve a bar before card payment (2-minute hold)."""
    result = pos_service.reserve_bar(db, dealer.id, body.product_id)
    if not result["success"]:
        raise HTTPException(400, {"success": False, "error": result["message"]})
    db.commit()
    return result


# ==========================================
# POST /api/pos/confirm
# ==========================================

@router.post("/confirm")
async def pos_confirm(
    body: ConfirmRequest,
    dealer: User = Depends(get_dealer_by_api_key),
    db: Session = Depends(get_db),
):
    """Confirm sale after successful card payment."""
    result = pos_service.confirm_sale(
        db=db,
        dealer_id=dealer.id,
        bar_id=body.bar_id,
        payment_ref=body.payment_ref,
        payment_amount=body.payment_amount,
        customer_name=body.customer_name,
        customer_mobile=body.customer_mobile,
        customer_national_id=body.customer_national_id,
    )
    if not result["success"]:
        raise HTTPException(400, {"success": False, "error": result["message"]})
    db.commit()
    return result


# ==========================================
# POST /api/pos/cancel
# ==========================================

@router.post("/cancel")
async def pos_cancel(
    body: CancelRequest,
    dealer: User = Depends(get_dealer_by_api_key),
    db: Session = Depends(get_db),
):
    """Cancel reservation (payment failed or cancelled)."""
    result = pos_service.cancel_reservation(db, dealer.id, body.bar_id)
    if not result["success"]:
        raise HTTPException(400, {"success": False, "error": result["message"]})
    db.commit()
    return result


# ==========================================
# GET /api/pos/receipt/{sale_id}
# ==========================================

@router.get("/receipt/{sale_id}")
async def pos_receipt(
    sale_id: int,
    dealer: User = Depends(get_dealer_by_api_key),
    db: Session = Depends(get_db),
):
    """Receipt data for printing."""
    result = pos_service.get_receipt(db, dealer.id, sale_id)
    if not result["success"]:
        raise HTTPException(404, {"success": False, "error": result["message"]})
    return result
