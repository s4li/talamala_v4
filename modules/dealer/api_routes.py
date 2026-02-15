"""
Dealer Module - REST API Routes (POS Device)
===============================================
Stateless JSON API for POS devices.
Auth: X-API-Key header (no cookies, no CSRF).

Endpoints:
  GET  /api/dealer/info     — Dealer health check
  GET  /api/dealer/products — Product list + pricing + bar serials
  POST /api/dealer/sale     — Register POS sale by serial_code
  GET  /api/dealer/sales    — Sales history (paginated)
"""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy.orm import Session

from config.database import get_db
from modules.dealer.models import Dealer
from modules.dealer.service import dealer_service


router = APIRouter(prefix="/api/dealer", tags=["dealer-api"])


# ==========================================
# Auth Dependency
# ==========================================

def get_dealer_by_api_key(
    x_api_key: str = Header(..., alias="X-API-Key"),
    db: Session = Depends(get_db),
) -> Dealer:
    """Authenticate dealer via X-API-Key header."""
    dealer = dealer_service.get_dealer_by_api_key(db, x_api_key)
    if not dealer:
        raise HTTPException(
            status_code=401,
            detail={"success": False, "error": "کلید API نامعتبر", "code": 401},
        )
    return dealer


# ==========================================
# Schemas
# ==========================================

class SaleRequest(BaseModel):
    serial_code: str = Field(..., min_length=1)
    sale_price: int = Field(..., gt=0)
    customer_name: Optional[str] = ""
    customer_mobile: Optional[str] = ""
    customer_national_id: Optional[str] = ""
    payment_ref: Optional[str] = ""
    description: Optional[str] = ""


# ==========================================
# GET /api/dealer/info
# ==========================================

@router.get("/info")
async def dealer_info(
    dealer: Dealer = Depends(get_dealer_by_api_key),
):
    """Health check / dealer identity."""
    return {
        "success": True,
        "dealer_id": dealer.id,
        "name": dealer.full_name,
        "location": dealer.full_name,
        "is_active": dealer.is_active,
    }


# ==========================================
# GET /api/dealer/products
# ==========================================

@router.get("/products")
async def dealer_products(
    dealer: Dealer = Depends(get_dealer_by_api_key),
    db: Session = Depends(get_db),
):
    """Product catalog with live pricing + available bar serials."""
    data = dealer_service.get_products_for_dealer(db, dealer.id)
    return {
        "success": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **data,
    }


# ==========================================
# POST /api/dealer/sale
# ==========================================

@router.post("/sale")
async def dealer_sale(
    body: SaleRequest,
    dealer: Dealer = Depends(get_dealer_by_api_key),
    db: Session = Depends(get_db),
):
    """Register a POS sale after successful card payment."""
    result = dealer_service.create_pos_sale_by_serial(
        db=db,
        dealer_id=dealer.id,
        serial_code=body.serial_code,
        sale_price=body.sale_price,
        customer_name=body.customer_name or "",
        customer_mobile=body.customer_mobile or "",
        customer_national_id=body.customer_national_id or "",
        payment_ref=body.payment_ref or "",
        description=body.description or "",
    )

    if not result["success"]:
        raise HTTPException(
            status_code=400,
            detail={"success": False, "error": result["message"], "code": 400},
        )

    db.commit()

    sale = result["sale"]
    return {
        "success": True,
        "sale_id": sale.id,
        "bar_serial": body.serial_code.upper(),
        "claim_code": result.get("claim_code"),
        "gold_profit_mg": result.get("gold_profit_mg", 0),
        "message": result["message"],
    }


# ==========================================
# GET /api/dealer/sales
# ==========================================

@router.get("/sales")
async def dealer_sales(
    page: int = 1,
    per_page: int = 20,
    dealer: Dealer = Depends(get_dealer_by_api_key),
    db: Session = Depends(get_db),
):
    """Paginated sales history."""
    per_page = min(per_page, 100)
    sales, total = dealer_service.get_dealer_sales(db, dealer.id, page=page, per_page=per_page)

    return {
        "success": True,
        "page": page,
        "per_page": per_page,
        "total": total,
        "sales": [
            {
                "sale_id": s.id,
                "bar_serial": s.bar.serial_code if s.bar else None,
                "product_name": s.bar.product.name if s.bar and s.bar.product else None,
                "customer_name": s.customer_name,
                "customer_mobile": s.customer_mobile,
                "sale_price": s.sale_price,
                "gold_profit_mg": s.gold_profit_mg,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in sales
        ],
    }
