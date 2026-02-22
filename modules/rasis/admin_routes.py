"""
Rasis POS Admin Panel
========================
Dedicated admin page to manage Rasis POS sync for all dealers.
"""

import urllib.parse

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session

from config.database import get_db
from common.templating import templates
from common.security import csrf_check, new_csrf_token
from modules.auth.deps import require_permission
from modules.user.models import User
from modules.inventory.models import Bar, BarStatus
from modules.rasis.models import RasisReceipt
from modules.rasis.service import rasis_service

router = APIRouter(prefix="/admin/rasis", tags=["admin-rasis"])


@router.get("", response_class=HTMLResponse)
async def rasis_panel(
    request: Request,
    msg: str = None,
    error: str = None,
    user=Depends(require_permission("dealers")),
    db: Session = Depends(get_db),
):
    """Rasis POS management panel — show dealers with sync status + recent receipts."""

    # Get all active dealers
    dealers = (
        db.query(User)
        .filter(User.is_dealer == True, User.is_active == True)
        .order_by(User.first_name, User.last_name)
        .all()
    )

    # Count ASSIGNED bars per dealer
    bar_counts = dict(
        db.query(Bar.dealer_id, sa_func.count(Bar.id))
        .filter(Bar.status == BarStatus.ASSIGNED, Bar.product_id.isnot(None))
        .group_by(Bar.dealer_id)
        .all()
    )

    # Enrich dealers with bar count
    dealer_list = []
    for d in dealers:
        dealer_list.append({
            "id": d.id,
            "full_name": d.full_name,
            "mobile": d.mobile,
            "tier_name": d.tier_name,
            "rasis_sharepoint": d.rasis_sharepoint,
            "rasis_last_record_version": d.rasis_last_record_version,
            "bar_count": bar_counts.get(d.id, 0),
        })

    # Recent receipts (last 50)
    recent_receipts = (
        db.query(RasisReceipt)
        .order_by(RasisReceipt.id.desc())
        .limit(50)
        .all()
    )

    csrf = new_csrf_token()
    response = templates.TemplateResponse("admin/rasis/panel.html", {
        "request": request,
        "user": user,
        "active_page": "rasis",
        "csrf_token": csrf,
        "dealers": dealer_list,
        "recent_receipts": recent_receipts,
        "msg": msg,
        "error": error,
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


@router.post("/{dealer_id}/register")
async def rasis_register_dealer(
    dealer_id: int,
    request: Request,
    csrf_token: str = Form(""),
    user=Depends(require_permission("dealers")),
    db: Session = Depends(get_db),
):
    """Register a dealer as Rasis branch."""
    csrf_check(request, csrf_token)

    dealer = db.query(User).filter(User.id == dealer_id, User.is_dealer == True).first()
    if not dealer:
        return RedirectResponse("/admin/rasis?error=" + urllib.parse.quote("نماینده یافت نشد."), status_code=303)

    result = rasis_service.register_branch(db, dealer)
    db.commit()

    if result:
        msg = urllib.parse.quote(f"نماینده {dealer.full_name} در راسیس ثبت شد — شرپوینت: {result}")
    else:
        msg = urllib.parse.quote(f"خطا در ثبت نماینده {dealer.full_name} در راسیس.")
        return RedirectResponse(f"/admin/rasis?error={msg}", status_code=303)

    return RedirectResponse(f"/admin/rasis?msg={msg}", status_code=303)


@router.post("/{dealer_id}/sync")
async def rasis_sync_dealer(
    dealer_id: int,
    request: Request,
    csrf_token: str = Form(""),
    user=Depends(require_permission("dealers")),
    db: Session = Depends(get_db),
):
    """Sync dealer's inventory to Rasis POS."""
    csrf_check(request, csrf_token)

    dealer = db.query(User).filter(User.id == dealer_id, User.is_dealer == True).first()
    if not dealer:
        return RedirectResponse("/admin/rasis?error=" + urllib.parse.quote("نماینده یافت نشد."), status_code=303)

    result = rasis_service.sync_dealer_inventory(db, dealer)
    db.commit()

    if result.get("skipped"):
        msg = urllib.parse.quote("راسیس غیرفعال است.")
        return RedirectResponse(f"/admin/rasis?error={msg}", status_code=303)

    msg = urllib.parse.quote(
        f"همگام‌سازی {dealer.full_name}: {result.get('added', 0)} اضافه، {result.get('errors', 0)} خطا"
    )
    return RedirectResponse(f"/admin/rasis?msg={msg}", status_code=303)


@router.post("/sync-all")
async def rasis_sync_all(
    request: Request,
    csrf_token: str = Form(""),
    user=Depends(require_permission("dealers")),
    db: Session = Depends(get_db),
):
    """Sync all registered dealers' inventory to Rasis POS."""
    csrf_check(request, csrf_token)

    dealers = (
        db.query(User)
        .filter(
            User.is_dealer == True,
            User.is_active == True,
            User.rasis_sharepoint.isnot(None),
        )
        .all()
    )

    total_added = 0
    total_errors = 0
    for dealer in dealers:
        result = rasis_service.sync_dealer_inventory(db, dealer)
        total_added += result.get("added", 0)
        total_errors += result.get("errors", 0)

    db.commit()
    msg = urllib.parse.quote(
        f"همگام‌سازی {len(dealers)} نماینده: {total_added} اضافه، {total_errors} خطا"
    )
    return RedirectResponse(f"/admin/rasis?msg={msg}", status_code=303)


@router.post("/fetch-receipts")
async def rasis_fetch_receipts(
    request: Request,
    csrf_token: str = Form(""),
    user=Depends(require_permission("dealers")),
    db: Session = Depends(get_db),
):
    """Manually fetch receipts from Rasis for all dealers."""
    csrf_check(request, csrf_token)

    result = rasis_service.process_all_receipts(db)

    if result.get("skipped"):
        msg = urllib.parse.quote("راسیس غیرفعال است.")
        return RedirectResponse(f"/admin/rasis?error={msg}", status_code=303)

    msg = urllib.parse.quote(
        f"واکشی فروش: {result.get('receipts_found', 0)} فاکتور، {result.get('sales_created', 0)} فروش ثبت شد"
    )
    return RedirectResponse(f"/admin/rasis?msg={msg}", status_code=303)
