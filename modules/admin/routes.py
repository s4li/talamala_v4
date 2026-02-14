"""
Admin Module - Settings Routes
=================================
System settings management (gold price, tax, etc.).
"""

from typing import Optional
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from config.database import get_db
from common.templating import templates
from common.security import csrf_check, new_csrf_token
from modules.auth.deps import require_super_admin
from modules.admin.models import SystemSetting

router = APIRouter(tags=["admin-settings"])


@router.get("/admin/settings", response_class=HTMLResponse)
async def settings_page(request: Request, db: Session = Depends(get_db), user=Depends(require_super_admin)):
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
    user=Depends(require_super_admin),
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
