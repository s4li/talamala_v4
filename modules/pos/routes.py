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

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from config.database import get_db
from modules.dealer.models import Dealer
from modules.dealer.auth_deps import get_dealer_by_api_key
from modules.pos.service import pos_service


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


# ==========================================
# GET /api/pos/categories
# ==========================================

@router.get("/categories")
async def pos_categories(
    dealer: Dealer = Depends(get_dealer_by_api_key),
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
    dealer: Dealer = Depends(get_dealer_by_api_key),
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
    dealer: Dealer = Depends(get_dealer_by_api_key),
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
    dealer: Dealer = Depends(get_dealer_by_api_key),
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
    dealer: Dealer = Depends(get_dealer_by_api_key),
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
    dealer: Dealer = Depends(get_dealer_by_api_key),
    db: Session = Depends(get_db),
):
    """Receipt data for printing."""
    result = pos_service.get_receipt(db, dealer.id, sale_id)
    if not result["success"]:
        raise HTTPException(404, {"success": False, "error": result["message"]})
    return result
