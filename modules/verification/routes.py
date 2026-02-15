"""
Verification Module - Authenticity Check + QR Code
=====================================================
Public QR code verification: anyone can scan a bar's QR to verify authenticity.
Phase 10: Added QR generation, ownership history, enhanced API.
"""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse, Response
from sqlalchemy.orm import Session

from config.database import get_db
from common.templating import templates
from modules.inventory.models import Bar, BarStatus, OwnershipHistory
from modules.verification.service import verification_service

router = APIRouter(prefix="/verify", tags=["verification"])


def _bar_to_result(bar: Bar, db: Session) -> dict:
    """Build a result dict from a Bar ORM object, including ownership history."""
    history = (
        db.query(OwnershipHistory)
        .filter(OwnershipHistory.bar_id == bar.id)
        .order_by(OwnershipHistory.transfer_date.desc())
        .all()
    )

    history_list = []
    for h in history:
        history_list.append({
            "date": h.transfer_date,
            "description": h.description or "انتقال مالکیت",
            "from_owner": h.previous_owner.full_name if h.previous_owner else "طلاملا",
            "to_owner": h.new_owner.full_name if h.new_owner else "—",
        })

    return {
        "valid": True,
        "serial": bar.serial_code,
        "product_name": bar.product.name if bar.product else "—",
        "weight": str(bar.product.weight) if bar.product else "—",
        "purity": float(bar.product.purity) if bar.product else "—",
        "status": bar.status,
        "status_label": bar.status_label,
        "status_color": bar.status_color,
        "location": bar.dealer_location.full_name if bar.dealer_location else "—",
        "batch_code": bar.batch.batch_number if bar.batch else "—",
        "created_at": bar.created_at,
        "history": history_list,
        "has_image": bool(bar.first_image),
        "image_path": bar.first_image,
    }


@router.get("", response_class=HTMLResponse)
async def verify_page(request: Request, code: str = ""):
    """Public verification page — scan QR or enter serial code."""
    return templates.TemplateResponse("public/verify.html", {
        "request": request,
        "code": code,
        "result": None,
    })


@router.get("/check", response_class=HTMLResponse)
async def verify_check(
    request: Request,
    code: str = "",
    db: Session = Depends(get_db),
):
    """Check serial code and return result with ownership history."""
    result = None
    if code.strip():
        bar = db.query(Bar).filter(Bar.serial_code == code.strip().upper()).first()
        if bar:
            result = _bar_to_result(bar, db)
        else:
            result = {"valid": False, "serial": code.strip().upper()}

    return templates.TemplateResponse("public/verify.html", {
        "request": request,
        "code": code.strip(),
        "result": result,
    })


# ==========================================
# QR Code Image Endpoint
# ==========================================

@router.get("/qr/{serial_code}.png")
async def qr_code_image(serial_code: str, db: Session = Depends(get_db)):
    """Generate and return QR code PNG for a bar's serial code."""
    bar = db.query(Bar).filter(Bar.serial_code == serial_code.upper()).first()
    if not bar:
        return Response(status_code=404, content=b"Not found")

    png_bytes = verification_service.generate_qr_bytes(bar.serial_code)
    return Response(
        content=png_bytes,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=86400"},
    )


# ==========================================
# JSON API for QR Scanner Apps (Enhanced)
# ==========================================

@router.get("/api/check")
async def api_verify_check(code: str = "", db: Session = Depends(get_db)):
    """JSON API for QR scanner apps — enhanced with ownership history."""
    if not code.strip():
        return JSONResponse({"valid": False, "message": "کد سریال وارد نشده"})

    bar = db.query(Bar).filter(Bar.serial_code == code.strip().upper()).first()
    if not bar:
        return JSONResponse({"valid": False, "message": "شمش با این کد سریال یافت نشد"})

    history = (
        db.query(OwnershipHistory)
        .filter(OwnershipHistory.bar_id == bar.id)
        .order_by(OwnershipHistory.transfer_date.desc())
        .all()
    )

    return JSONResponse({
        "valid": True,
        "serial": bar.serial_code,
        "product": bar.product.name if bar.product else None,
        "weight": str(bar.product.weight) if bar.product else None,
        "purity": float(bar.product.purity) if bar.product else None,
        "status": bar.status,
        "status_label": bar.status_label,
        "location": bar.dealer_location.full_name if bar.dealer_location else None,
        "batch": bar.batch.batch_number if bar.batch else None,
        "qr_url": f"/verify/qr/{bar.serial_code}.png",
        "history": [
            {
                "date": h.transfer_date.isoformat() if h.transfer_date else None,
                "description": h.description or "انتقال مالکیت",
            }
            for h in history
        ],
    })
