"""
TalaMala v4 - Notification Admin Routes
=========================================
Admin can send broadcast notifications to users/groups.
"""

from fastapi import APIRouter, Request, Depends, Form, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from config.database import get_db
from common.templating import templates
from common.security import csrf_check, new_csrf_token
from modules.auth.deps import require_permission
from modules.notification.service import notification_service
from modules.notification.models import NotificationType

router = APIRouter(prefix="/admin/notifications", tags=["admin-notifications"])


# ------------------------------------------------------------------
# GET /admin/notifications/send — Broadcast form
# ------------------------------------------------------------------
@router.get("/send", response_class=HTMLResponse)
async def admin_send_notification_form(
    request: Request,
    msg: str = "",
    count: int = 0,
    db: Session = Depends(get_db),
    user=Depends(require_permission("notifications", level="create")),
):
    notification_count = notification_service.get_unread_count(db, user.id)

    csrf = new_csrf_token()
    response = templates.TemplateResponse("admin/notifications/send.html", {
        "request": request,
        "user": user,
        "csrf_token": csrf,
        "active_page": "notifications",
        "notification_count": notification_count,
        "msg": msg,
        "count": count,
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


# ------------------------------------------------------------------
# POST /admin/notifications/send — Send broadcast
# ------------------------------------------------------------------
@router.post("/send")
async def admin_send_notification(
    request: Request,
    background_tasks: BackgroundTasks,
    target_type: str = Form(...),
    target_mobile: str = Form(""),
    title: str = Form(...),
    body: str = Form(...),
    send_sms: str = Form(""),
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
    user=Depends(require_permission("notifications", level="create")),
):
    csrf_check(request, csrf_token)
    from modules.user.models import User

    targets = []
    if target_type == "user" and target_mobile:
        u = db.query(User).filter(User.mobile == target_mobile.strip()).first()
        if u:
            targets = [u]
    elif target_type == "all_customers":
        targets = db.query(User).filter(User.is_active == True).all()
    elif target_type == "all_dealers":
        targets = db.query(User).filter(User.is_dealer == True, User.is_active == True).all()

    sms_text = body if send_sms else None
    count = 0
    for t in targets:
        notification_service.send(
            db, t.id,
            notification_type=NotificationType.SYSTEM,
            title=title,
            body=body,
            sms_text=sms_text,
            sms_mobile=t.mobile,
            reference_type="admin_broadcast",
            background_tasks=background_tasks,
        )
        count += 1

    db.commit()
    return RedirectResponse(f"/admin/notifications/send?msg=sent&count={count}", status_code=302)
