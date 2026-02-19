"""
Dealer Request Module - Admin Routes
=======================================
Admin manages dealer requests: list, detail, approve, reject.
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
    user=Depends(require_permission("dealers")),
):
    csrf_check(request, csrf_token)
    result = dealer_request_service.approve_request(db, req_id, admin_note)
    if result["success"]:
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
    user=Depends(require_permission("dealers")),
):
    csrf_check(request, csrf_token)
    result = dealer_request_service.reject_request(db, req_id, admin_note)
    if result["success"]:
        db.commit()
    else:
        db.rollback()
    return RedirectResponse(f"/admin/dealer-requests/{req_id}", status_code=302)
