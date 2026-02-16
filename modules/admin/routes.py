"""
Admin Module - Settings & Logs Routes
========================================
System settings management + Request audit log viewer.
"""

from typing import Optional
from fastapi import APIRouter, Request, Depends, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from config.database import get_db
from common.templating import templates
from common.security import csrf_check, new_csrf_token
from modules.auth.deps import require_permission
from modules.admin.models import SystemSetting, RequestLog

router = APIRouter(tags=["admin-settings"])


@router.get("/admin/settings", response_class=HTMLResponse)
async def settings_page(request: Request, db: Session = Depends(get_db), user=Depends(require_permission("settings"))):
    settings = db.query(SystemSetting).all()
    settings_dict = {s.key: s for s in settings}

    csrf = new_csrf_token()
    response = templates.TemplateResponse("admin/settings.html", {
        "request": request,
        "user": user,
        "settings": settings_dict,
        "csrf_token": csrf,
        "active_page": "settings",
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


@router.post("/admin/settings/update")
async def update_settings(
    request: Request,
    csrf_token: Optional[str] = Form(None),
    gold_price: str = Form("0"),
    silver_price: str = Form("0"),
    tax_percent: str = Form("9"),
    support_phone: str = Form(""),
    support_telegram: str = Form(""),
    reservation_minutes: str = Form("15"),
    shipping_cost: str = Form("500000"),
    insurance_percent: str = Form("1.5"),
    insurance_cap: str = Form("500000000"),
    db: Session = Depends(get_db),
    user=Depends(require_permission("settings")),
):
    csrf_check(request, csrf_token)

    updates = {
        "gold_price": gold_price,
        "silver_price": silver_price,
        "tax_percent": tax_percent,
        "support_phone": support_phone,
        "support_telegram": support_telegram,
        "reservation_minutes": reservation_minutes,
        "shipping_cost": shipping_cost,
        "insurance_percent": insurance_percent,
        "insurance_cap": insurance_cap,
    }

    for key, value in updates.items():
        setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()
        if setting:
            setting.value = value
        else:
            db.add(SystemSetting(key=key, value=value))

    db.commit()
    return RedirectResponse("/admin/settings?msg=saved", status_code=303)


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
