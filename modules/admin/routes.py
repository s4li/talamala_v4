"""
Admin Module - Settings & Logs Routes
========================================
System settings management + Request audit log viewer.
"""

from typing import Optional, List
from fastapi import APIRouter, Request, Depends, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session

from config.database import get_db
from common.templating import templates
from common.security import csrf_check, new_csrf_token
from modules.auth.deps import require_permission
from modules.admin.models import SystemSetting, RequestLog
from modules.pricing.models import Asset, GOLD_18K, SILVER
from modules.pricing.service import update_asset_price

router = APIRouter(tags=["admin-settings"])


@router.get("/admin/settings", response_class=HTMLResponse)
async def settings_page(request: Request, db: Session = Depends(get_db), user=Depends(require_permission("settings"))):
    settings = db.query(SystemSetting).all()
    settings_dict = {s.key: s for s in settings}

    # Load asset prices
    assets = db.query(Asset).order_by(Asset.id).all()
    assets_dict = {a.asset_code: a for a in assets}

    csrf = new_csrf_token()
    response = templates.TemplateResponse("admin/settings.html", {
        "request": request,
        "user": user,
        "settings": settings_dict,
        "assets": assets_dict,
        "csrf_token": csrf,
        "active_page": "settings",
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


@router.post("/admin/settings/update")
async def update_settings(
    request: Request,
    csrf_token: Optional[str] = Form(None),
    # Asset prices
    gold_price: str = Form("0"),
    gold_auto_update: Optional[str] = Form(None),
    gold_stale_minutes: str = Form("15"),
    gold_update_interval: str = Form("5"),
    silver_price: str = Form("0"),
    silver_auto_update: Optional[str] = Form(None),
    silver_stale_minutes: str = Form("30"),
    silver_update_interval: str = Form("30"),
    # Other settings
    tax_percent: str = Form("9"),
    support_phone: str = Form(""),
    support_telegram: str = Form(""),
    reservation_minutes: str = Form("15"),
    shipping_cost: str = Form("500000"),
    insurance_percent: str = Form("1.5"),
    insurance_cap: str = Form("500000000"),
    enabled_gateways: List[str] = Form(["sepehr"]),
    shahkar_enabled: Optional[str] = Form(None),
    shahkar_api_token: str = Form(""),
    db: Session = Depends(get_db),
    user=Depends(require_permission("settings")),
):
    csrf_check(request, csrf_token)

    from common.helpers import now_utc

    # Update asset prices
    for asset_code, price_val, auto_update_val, stale_min, update_int in [
        (GOLD_18K, gold_price, gold_auto_update, gold_stale_minutes, gold_update_interval),
        (SILVER, silver_price, silver_auto_update, silver_stale_minutes, silver_update_interval),
    ]:
        asset = db.query(Asset).filter(Asset.asset_code == asset_code).first()
        if asset:
            new_price = int(price_val) if price_val.isdigit() else 0
            if new_price != asset.price_per_gram and new_price > 0:
                asset.price_per_gram = new_price
                asset.updated_at = now_utc()
                asset.updated_by = f"admin:{user.full_name}"
            asset.auto_update = (auto_update_val == "on")
            asset.stale_after_minutes = int(stale_min) if stale_min.isdigit() else 15
            asset.update_interval_minutes = int(update_int) if update_int.isdigit() else 5

    # Update other system settings (not prices)
    updates = {
        "tax_percent": tax_percent,
        "support_phone": support_phone,
        "support_telegram": support_telegram,
        "reservation_minutes": reservation_minutes,
        "shipping_cost": shipping_cost,
        "insurance_percent": insurance_percent,
        "insurance_cap": insurance_cap,
        "enabled_gateways": ",".join(enabled_gateways) if enabled_gateways else "sepehr",
        "shahkar_enabled": "true" if shahkar_enabled == "on" else "false",
        "shahkar_api_token": shahkar_api_token,
    }

    for key, value in updates.items():
        setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()
        if setting:
            setting.value = value
        else:
            db.add(SystemSetting(key=key, value=value))

    db.commit()
    return RedirectResponse("/admin/settings?msg=saved", status_code=303)


@router.post("/admin/settings/fetch-price")
async def fetch_price_ajax(
    request: Request,
    asset_code: str = Form("gold_18k"),
    csrf_token: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    user=Depends(require_permission("settings")),
):
    """AJAX: manually trigger price fetch from external API."""
    csrf_check(request, csrf_token)

    from common.helpers import now_utc

    asset = db.query(Asset).filter(Asset.asset_code == asset_code).first()
    if not asset:
        return JSONResponse({"success": False, "error": "دارایی یافت نشد"}, status_code=404)

    try:
        if asset_code == GOLD_18K:
            from modules.pricing.feed_service import fetch_gold_price_goldis
            new_price = fetch_gold_price_goldis()
        else:
            return JSONResponse({"success": False, "error": "منبع قیمت برای این دارایی تعریف نشده"})

        asset.price_per_gram = new_price
        asset.updated_at = now_utc()
        asset.updated_by = f"admin:{user.full_name}"
        db.commit()

        return JSONResponse({
            "success": True,
            "new_price": new_price,
            "new_price_toman": new_price // 10,
            "updated_by": asset.updated_by,
        })
    except Exception as e:
        return JSONResponse({"success": False, "error": f"خطا در دریافت قیمت: {str(e)}"})


# ==========================================
# 📋 Request Audit Log
# ==========================================

@router.get("/admin/logs", response_class=HTMLResponse)
async def admin_logs(
    request: Request,
    page: int = 1,
    method: str = Query(None),
    status_group: str = Query(None),
    path_search: str = Query(None),
    user_type: str = Query(None),
    ip: str = Query(None),
    db: Session = Depends(get_db),
    user=Depends(require_permission("logs")),
):
    per_page = 50
    q = db.query(RequestLog)

    # Filters
    if method:
        q = q.filter(RequestLog.method == method.upper())
    if status_group:
        if status_group == "2xx":
            q = q.filter(RequestLog.status_code >= 200, RequestLog.status_code < 300)
        elif status_group == "3xx":
            q = q.filter(RequestLog.status_code >= 300, RequestLog.status_code < 400)
        elif status_group == "4xx":
            q = q.filter(RequestLog.status_code >= 400, RequestLog.status_code < 500)
        elif status_group == "5xx":
            q = q.filter(RequestLog.status_code >= 500)
    if path_search:
        q = q.filter(RequestLog.path.ilike(f"%{path_search}%"))
    if user_type:
        q = q.filter(RequestLog.user_type == user_type)
    if ip:
        q = q.filter(RequestLog.ip_address == ip)

    total = q.count()
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = min(page, total_pages)

    logs = q.order_by(RequestLog.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

    # Quick stats
    from sqlalchemy import func as sa_func
    stats = {
        "total": db.query(sa_func.count(RequestLog.id)).scalar() or 0,
        "today": db.query(sa_func.count(RequestLog.id)).filter(
            sa_func.date(RequestLog.created_at) == sa_func.current_date()
        ).scalar() or 0,
        "errors": db.query(sa_func.count(RequestLog.id)).filter(
            RequestLog.status_code >= 400
        ).scalar() or 0,
    }

    return templates.TemplateResponse("admin/logs/list.html", {
        "request": request,
        "user": user,
        "logs": logs,
        "stats": stats,
        "page": page,
        "total": total,
        "total_pages": total_pages,
        "method_filter": method or "",
        "status_filter": status_group or "",
        "path_search": path_search or "",
        "user_type_filter": user_type or "",
        "ip_filter": ip or "",
        "active_page": "logs",
    })
