"""
Dealer Request Module - Admin Routes
=======================================
Admin manages dealer requests: list, detail, approve, reject, request revision.
"""

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from config.database import get_db
from common.templating import templates
from common.security import new_csrf_token, csrf_check
from modules.auth.deps import require_permission
from modules.dealer_request.service import dealer_request_service
from modules.dealer_request.models import DealerRequestStatus

router = APIRouter(prefix="/admin/dealer-requests", tags=["admin-dealer-requests"])


# ==========================================
# List
# ==========================================

@router.get("", response_class=HTMLResponse)
async def admin_dealer_request_list(
    request: Request,
    page: int = 1,
    status: str = None,
    search: str = None,
    db: Session = Depends(get_db),
    user=Depends(require_permission("dealers")),
):
    items, total = dealer_request_service.list_requests(
        db, page=page, status_filter=status, search=search,
    )
    total_pages = max(1, (total + 29) // 30)
    stats = dealer_request_service.get_stats(db)

    csrf = new_csrf_token()
    response = templates.TemplateResponse("admin/dealer_requests/list.html", {
        "request": request,
        "user": user,
        "items": items,
        "total": total,
        "page": page,
        "total_pages": total_pages,
        "stats": stats,
        "current_status": status,
        "search": search or "",
        "csrf_token": csrf,
        "active_page": "dealer_requests",
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


# ==========================================
# Detail
# ==========================================

@router.get("/{req_id}", response_class=HTMLResponse)
async def admin_dealer_request_detail(
    req_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_permission("dealers")),
):
    dealer_req = dealer_request_service.get_request(db, req_id)
    if not dealer_req:
        return RedirectResponse("/admin/dealer-requests", status_code=302)

    csrf = new_csrf_token()
    response = templates.TemplateResponse("admin/dealer_requests/detail.html", {
        "request": request,
        "user": user,
        "dealer_request": dealer_req,
        "csrf_token": csrf,
        "active_page": "dealer_requests",
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


# ==========================================
# Approve
# ==========================================

@router.post("/{req_id}/approve")
async def admin_dealer_request_approve(
    req_id: int,
    request: Request,
    admin_note: str = Form(""),
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
    user=Depends(require_permission("dealers", level="full")),
):
    csrf_check(request, csrf_token)
    result = dealer_request_service.approve_request(db, req_id, admin_note)
    if result["success"]:
        try:
            from modules.notification.service import notification_service
            from modules.notification.models import NotificationType
            from modules.dealer_request.models import DealerRequest
            dr = db.query(DealerRequest).filter(DealerRequest.id == req_id).first()
            if dr:
                notification_service.send(
                    db, dr.user_id,
                    notification_type=NotificationType.DEALER_REQUEST,
                    title="درخواست نمایندگی تأیید شد",
                    body="درخواست نمایندگی شما تأیید شد. به پنل نمایندگی خوش آمدید!",
                    link="/dealer/dashboard",
                    sms_text="طلاملا: درخواست نمایندگی شما تأیید شد! talamala.com/dealer/dashboard",
                    reference_type="dealer_request_approved", reference_id=str(req_id),
                )
        except Exception:
            pass
        db.commit()
    else:
        db.rollback()
    return RedirectResponse(f"/admin/dealer-requests/{req_id}", status_code=302)


# ==========================================
# Request Revision
# ==========================================

@router.post("/{req_id}/revision")
async def admin_dealer_request_revision(
    req_id: int,
    request: Request,
    admin_note: str = Form(""),
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
    user=Depends(require_permission("dealers", level="edit")),
):
    csrf_check(request, csrf_token)
    result = dealer_request_service.request_revision(db, req_id, admin_note)
    if result["success"]:
        try:
            from modules.notification.service import notification_service
            from modules.notification.models import NotificationType
            from modules.dealer_request.models import DealerRequest
            dr = db.query(DealerRequest).filter(DealerRequest.id == req_id).first()
            if dr:
                notification_service.send(
                    db, dr.user_id,
                    notification_type=NotificationType.DEALER_REQUEST,
                    title="درخواست نمایندگی نیاز به اصلاح دارد",
                    body="درخواست نمایندگی شما نیاز به اصلاح دارد. لطفاً اطلاعات را بررسی و مجدداً ارسال کنید." + (f" توضیح: {admin_note}" if admin_note else ""),
                    link="/dealer-request?edit=1",
                    sms_text="طلاملا: درخواست نمایندگی شما نیاز به اصلاح دارد. talamala.com/dealer-request?edit=1",
                    reference_type="dealer_request_revision", reference_id=str(req_id),
                )
        except Exception:
            pass
        db.commit()
    else:
        db.rollback()
    return RedirectResponse(f"/admin/dealer-requests/{req_id}", status_code=302)


# ==========================================
# Reject
# ==========================================

@router.post("/{req_id}/reject")
async def admin_dealer_request_reject(
    req_id: int,
    request: Request,
    admin_note: str = Form(""),
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
    user=Depends(require_permission("dealers", level="full")),
):
    csrf_check(request, csrf_token)
    result = dealer_request_service.reject_request(db, req_id, admin_note)
    if result["success"]:
        try:
            from modules.notification.service import notification_service
            from modules.notification.models import NotificationType
            from modules.dealer_request.models import DealerRequest
            dr = db.query(DealerRequest).filter(DealerRequest.id == req_id).first()
            if dr:
                notification_service.send(
                    db, dr.user_id,
                    notification_type=NotificationType.DEALER_REQUEST,
                    title="درخواست نمایندگی رد شد",
                    body="متأسفانه درخواست نمایندگی شما رد شد." + (f" توضیح: {admin_note}" if admin_note else ""),
                    link="/dealer-request",
                    sms_text="طلاملا: درخواست نمایندگی شما رد شد.",
                    reference_type="dealer_request_rejected", reference_id=str(req_id),
                )
        except Exception:
            pass
        db.commit()
    else:
        db.rollback()
    return RedirectResponse(f"/admin/dealer-requests/{req_id}", status_code=302)
