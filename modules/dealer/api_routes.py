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
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy.orm import Session

from config.database import get_db
from modules.user.models import User
from modules.dealer.service import dealer_service
from modules.dealer.auth_deps import get_dealer_by_api_key


router = APIRouter(prefix="/api/dealer", tags=["dealer-api"])


# ==========================================
# Schemas
# ==========================================

class SaleRequest(BaseModel):
    serial_code: str = Field(..., min_length=1)
    sale_price: int = Field(..., gt=0)
    discount_wage_percent: Optional[float] = Field(0.0, ge=0)
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
    dealer: User = Depends(get_dealer_by_api_key),
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
    dealer: User = Depends(get_dealer_by_api_key),
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
    dealer: User = Depends(get_dealer_by_api_key),
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
        discount_wage_percent=body.discount_wage_percent or 0.0,
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
        "metal_profit_mg": result.get("metal_profit_mg", 0),
        "discount_wage_percent": float(sale.discount_wage_percent) if sale.discount_wage_percent else 0,
        "message": result["message"],
    }


# ==========================================
# GET /api/dealer/sales
# ==========================================

@router.get("/sales")
async def dealer_sales(
    page: int = 1,
    per_page: int = 20,
    dealer: User = Depends(get_dealer_by_api_key),
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
                "metal_profit_mg": s.metal_profit_mg,
                "metal_type": s.metal_type,
                "discount_wage_percent": float(s.discount_wage_percent) if s.discount_wage_percent else 0,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in sales
        ],
    }
