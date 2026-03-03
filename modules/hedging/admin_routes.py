"""
Hedging / Position Management — Admin Routes
================================================
Dashboard, hedge recording, manual adjustment, and full ledger.
"""

import re
from typing import Optional

from fastapi import APIRouter, Request, Depends, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session

from config.database import get_db
from common.templating import templates
from common.security import csrf_check, new_csrf_token
from modules.auth.deps import require_permission
from modules.hedging.service import hedging_service

router = APIRouter(tags=["admin-hedging"])


def _parse_numeric(val: str) -> int:
    """Parse numeric string: strip commas, spaces, Persian/Arabic digits -> int."""
    if not val:
        return 0
    persian_map = str.maketrans(
        "\u06f0\u06f1\u06f2\u06f3\u06f4\u06f5\u06f6\u06f7\u06f8\u06f9"
        "\u0660\u0661\u0662\u0663\u0664\u0665\u0666\u0667\u0668\u0669",
        "01234567890123456789",
    )
    val = val.translate(persian_map)
    val = re.sub(r"[,\s\u200c]+", "", val)
    return int(val) if val.isdigit() else 0


def _parse_decimal_grams(val: str) -> int:
    """Parse decimal gram input -> milligrams (int). Supports '1.5' -> 1500."""
    if not val:
        return 0
    persian_map = str.maketrans(
        "\u06f0\u06f1\u06f2\u06f3\u06f4\u06f5\u06f6\u06f7\u06f8\u06f9"
        "\u0660\u0661\u0662\u0663\u0664\u0665\u0666\u0667\u0668\u0669",
        "01234567890123456789",
    )
    val = val.translate(persian_map).replace(",", "").replace(" ", "").replace("\u200c", "")
    try:
        grams = float(val)
        return int(grams * 1000)
    except ValueError:
        return 0


# ==========================================
# Dashboard
# ==========================================

@router.get("/admin/hedging", response_class=HTMLResponse)
async def hedging_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_permission("hedging", level="view")),
):
    positions = hedging_service.get_all_positions(db)
    gold_summary = hedging_service.get_summary(db, "gold")
    silver_summary = hedging_service.get_summary(db, "silver")
    recent_entries, total = hedging_service.get_ledger(db, per_page=20)

    # Chart data (last 30 days)
    gold_chart = hedging_service.get_chart_data(db, "gold", days=30)
    silver_chart = hedging_service.get_chart_data(db, "silver", days=30)

    csrf = new_csrf_token()
    response = templates.TemplateResponse("admin/hedging/dashboard.html", {
        "request": request,
        "user": user,
        "csrf_token": csrf,
        "active_page": "hedging",
        "positions": positions,
        "gold_summary": gold_summary,
        "silver_summary": silver_summary,
        "entries": recent_entries,
        "total": total,
        "gold_chart": gold_chart,
        "silver_chart": silver_chart,
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


# ==========================================
# Full Ledger (with filters + pagination)
# ==========================================

@router.get("/admin/hedging/ledger", response_class=HTMLResponse)
async def hedging_ledger(
    request: Request,
    metal: str = Query(""),
    source: str = Query(""),
    direction: str = Query(""),
    page: int = Query(1),
    db: Session = Depends(get_db),
    user=Depends(require_permission("hedging", level="view")),
):
    per_page = 50
    entries, total = hedging_service.get_ledger(
        db,
        metal_type=metal or None,
        source_type=source or None,
        direction=direction or None,
        page=max(1, page),
        per_page=per_page,
    )
    total_pages = max(1, (total + per_page - 1) // per_page)

    csrf = new_csrf_token()
    response = templates.TemplateResponse("admin/hedging/ledger.html", {
        "request": request,
        "user": user,
        "csrf_token": csrf,
        "active_page": "hedging",
        "entries": entries,
        "total": total,
        "page": min(max(1, page), total_pages),
        "total_pages": total_pages,
        "current_metal": metal,
        "current_source": source,
        "current_direction": direction,
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


# ==========================================
# Record Hedge Trade
# ==========================================

@router.get("/admin/hedging/record", response_class=HTMLResponse)
async def hedge_record_form(
    request: Request,
    msg: str = None,
    error: str = None,
    db: Session = Depends(get_db),
    user=Depends(require_permission("hedging", level="create")),
):
    positions = hedging_service.get_all_positions(db)

    csrf = new_csrf_token()
    response = templates.TemplateResponse("admin/hedging/record.html", {
        "request": request,
        "user": user,
        "csrf_token": csrf,
        "active_page": "hedging",
        "positions": positions,
        "msg": msg,
        "error": error,
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


@router.post("/admin/hedging/record")
async def hedge_record_submit(
    request: Request,
    metal_type: str = Form(...),
    hedge_direction: str = Form(...),
    amount_grams: str = Form(...),
    price_per_gram: str = Form(""),
    description: str = Form(""),
    csrf_token: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    user=Depends(require_permission("hedging", level="create")),
):
    csrf_check(request, csrf_token)

    # Validate inputs
    if metal_type not in ("gold", "silver"):
        return RedirectResponse("/admin/hedging/record?error=نوع فلز نامعتبر", status_code=303)
    if hedge_direction not in ("buy", "sell"):
        return RedirectResponse("/admin/hedging/record?error=جهت معامله نامعتبر", status_code=303)

    amount_mg = _parse_decimal_grams(amount_grams)
    if amount_mg <= 0:
        return RedirectResponse("/admin/hedging/record?error=مقدار باید بیشتر از صفر باشد", status_code=303)

    ppg = _parse_numeric(price_per_gram) if price_per_gram.strip() else None

    entry = hedging_service.record_hedge(
        db, metal_type, hedge_direction, amount_mg,
        metal_price_per_gram=ppg,
        description=description.strip(),
        admin_id=user.id,
    )
    db.commit()

    metal_label = "طلا" if metal_type == "gold" else "نقره"
    dir_label = "خرید از بازار" if hedge_direction == "buy" else "فروش در بازار"
    msg = f"{dir_label} {amount_mg/1000:,.3f} گرم {metal_label} ثبت شد"
    return RedirectResponse(f"/admin/hedging/record?msg={msg}", status_code=303)


# ==========================================
# Manual Adjustment / Initial Balance
# ==========================================

@router.get("/admin/hedging/adjust", response_class=HTMLResponse)
async def hedge_adjust_form(
    request: Request,
    msg: str = None,
    error: str = None,
    db: Session = Depends(get_db),
    user=Depends(require_permission("hedging", level="edit")),
):
    positions = hedging_service.get_all_positions(db)

    csrf = new_csrf_token()
    response = templates.TemplateResponse("admin/hedging/adjust.html", {
        "request": request,
        "user": user,
        "csrf_token": csrf,
        "active_page": "hedging",
        "positions": positions,
        "msg": msg,
        "error": error,
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


@router.post("/admin/hedging/adjust")
async def hedge_adjust_submit(
    request: Request,
    metal_type: str = Form(...),
    target_balance_grams: str = Form(...),
    description: str = Form(""),
    csrf_token: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    user=Depends(require_permission("hedging", level="edit")),
):
    csrf_check(request, csrf_token)

    if metal_type not in ("gold", "silver"):
        return RedirectResponse("/admin/hedging/adjust?error=نوع فلز نامعتبر", status_code=303)

    # Parse target balance (can be negative: e.g. "-1.5" means we're 1.5g short)
    target_str = target_balance_grams.strip()
    is_negative = target_str.startswith("-")
    if is_negative:
        target_str = target_str[1:]

    target_mg = _parse_decimal_grams(target_str)
    if is_negative:
        target_mg = -target_mg

    entry = hedging_service.set_initial_balance(
        db, metal_type, target_mg,
        admin_id=user.id,
        description=description.strip(),
    )
    db.commit()

    metal_label = "طلا" if metal_type == "gold" else "نقره"
    if entry:
        msg = f"بالانس {metal_label} به {target_mg/1000:,.3f} گرم تنظیم شد"
    else:
        msg = f"بالانس {metal_label} تغییری نکرد (مقدار فعلی همان است)"
    return RedirectResponse(f"/admin/hedging/adjust?msg={msg}", status_code=303)


# ==========================================
# JSON API: Current Positions (for AJAX refresh)
# ==========================================

@router.get("/admin/hedging/api/position")
async def hedge_api_position(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_permission("hedging", level="view")),
):
    positions = hedging_service.get_all_positions(db)
    return JSONResponse(positions)
