"""
TalaMala v4 - Notification Routes (Customer-facing)
=====================================================
Notification center, mark-read, preferences, AJAX badge count.
"""

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session

from config.database import get_db
from common.templating import templates
from common.security import csrf_check, new_csrf_token
from modules.auth.deps import require_login
from modules.notification.service import notification_service
from modules.notification.models import NotificationType, NOTIFICATION_TYPE_LABELS
from modules.cart.service import cart_service

router = APIRouter(tags=["notifications"])


# ------------------------------------------------------------------
# GET /notifications — Notification center page
# ------------------------------------------------------------------
@router.get("/notifications", response_class=HTMLResponse)
async def notification_list(
    request: Request,
    page: int = 1,
    db: Session = Depends(get_db),
    me=Depends(require_login),
):
    notifications, total = notification_service.list_notifications(db, me.id, page=page)
    total_pages = max(1, (total + 19) // 20)

    _, cart_count = cart_service.get_cart_map(db, me.id)
    notification_count = notification_service.get_unread_count(db, me.id)

    csrf = new_csrf_token()
    response = templates.TemplateResponse("shop/notifications.html", {
        "request": request,
        "user": me,
        "notifications": notifications,
        "total": total,
        "page": page,
        "total_pages": total_pages,
        "csrf_token": csrf,
        "cart_count": cart_count,
        "notification_count": notification_count,
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


# ------------------------------------------------------------------
# POST /notifications/{id}/read — AJAX mark single as read
# ------------------------------------------------------------------
@router.post("/notifications/{notification_id}/read")
async def mark_notification_read(
    request: Request,
    notification_id: int,
    db: Session = Depends(get_db),
    me=Depends(require_login),
):
    csrf_check(request)
    notification_service.mark_as_read(db, me.id, notification_id)
    db.commit()
    count = notification_service.get_unread_count(db, me.id)
    return JSONResponse({"success": True, "unread_count": count})


# ------------------------------------------------------------------
# POST /notifications/read-all — AJAX mark all as read
# ------------------------------------------------------------------
@router.post("/notifications/read-all")
async def mark_all_read(
    request: Request,
    db: Session = Depends(get_db),
    me=Depends(require_login),
):
    csrf_check(request)
    updated = notification_service.mark_all_read(db, me.id)
    db.commit()
    return JSONResponse({"success": True, "updated": updated, "unread_count": 0})


# ------------------------------------------------------------------
# GET /notifications/api/unread-count — AJAX polling for badge
# ------------------------------------------------------------------
@router.get("/notifications/api/unread-count")
async def unread_count_api(
    db: Session = Depends(get_db),
    me=Depends(require_login),
):
    count = notification_service.get_unread_count(db, me.id)
    return JSONResponse({"count": count})


# ------------------------------------------------------------------
# GET /notifications/settings — Preference management page
# ------------------------------------------------------------------
@router.get("/notifications/settings", response_class=HTMLResponse)
async def notification_settings_page(
    request: Request,
    msg: str = "",
    db: Session = Depends(get_db),
    me=Depends(require_login),
):
    prefs = notification_service.get_all_preferences(db, me.id)
    _, cart_count = cart_service.get_cart_map(db, me.id)
    notification_count = notification_service.get_unread_count(db, me.id)

    csrf = new_csrf_token()
    response = templates.TemplateResponse("shop/notification_settings.html", {
        "request": request,
        "user": me,
        "preferences": prefs,
        "type_labels": NOTIFICATION_TYPE_LABELS,
        "notification_types": NotificationType,
        "csrf_token": csrf,
        "cart_count": cart_count,
        "notification_count": notification_count,
        "msg": msg,
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


# ------------------------------------------------------------------
# POST /notifications/settings — Save preferences
# ------------------------------------------------------------------
@router.post("/notifications/settings")
async def save_notification_settings(
    request: Request,
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
    me=Depends(require_login),
):
    csrf_check(request, csrf_token)
    form_data = await request.form()

    prefs = {}
    for nt in NotificationType:
        prefs[nt.value] = {
            "sms": f"sms_{nt.value}" in form_data,
            "in_app": f"inapp_{nt.value}" in form_data,
            "email": f"email_{nt.value}" in form_data,
        }

    notification_service.save_preferences(db, me.id, prefs)
    db.commit()
    return RedirectResponse("/notifications/settings?msg=saved", status_code=302)
