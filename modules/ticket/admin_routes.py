"""
Ticket Module - Admin Routes
================================
Admin management of support tickets: list, reply, status, close, assign, internal notes.
"""

from typing import List, Optional
from fastapi import APIRouter, Request, Depends, Form, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from config.database import get_db
from common.templating import templates
from common.security import new_csrf_token, csrf_check
from modules.auth.deps import require_permission
from modules.ticket.service import ticket_service
from modules.ticket.models import TicketStatus, TicketCategory, SenderType
from modules.admin.models import SystemUser

router = APIRouter(prefix="/admin/tickets", tags=["admin-ticket"])


# ==========================================
# Ticket List (Admin) — with search + category filter
# ==========================================

@router.get("", response_class=HTMLResponse)
async def admin_ticket_list(
    request: Request,
    page: int = 1,
    status: str = None,
    sender_type: str = None,
    category: str = None,
    search: str = None,
    user=Depends(require_permission("tickets")),
    db: Session = Depends(get_db),
):
    tickets, total = ticket_service.list_tickets_admin(
        db, page=page, per_page=30,
        status_filter=status,
        sender_type_filter=sender_type,
        category_filter=category,
        search=search,
    )
    total_pages = max(1, (total + 29) // 30)
    stats = ticket_service.get_admin_stats(db)

    csrf = new_csrf_token()
    response = templates.TemplateResponse("admin/tickets/list.html", {
        "request": request,
        "user": user,
        "tickets": tickets,
        "total": total,
        "page": page,
        "total_pages": total_pages,
        "stats": stats,
        "status_filter": status,
        "sender_type_filter": sender_type,
        "category_filter": category,
        "search_query": search or "",
        "categories": TicketCategory,
        "csrf_token": csrf,
        "active_page": "tickets",
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


# ==========================================
# Ticket Detail (Admin)
# ==========================================

@router.get("/{ticket_id}", response_class=HTMLResponse)
async def admin_ticket_detail(
    ticket_id: int,
    request: Request,
    user=Depends(require_permission("tickets")),
    db: Session = Depends(get_db),
):
    ticket = ticket_service.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="تیکت یافت نشد")

    staff_list = db.query(SystemUser).order_by(SystemUser.full_name).all()

    csrf = new_csrf_token()
    response = templates.TemplateResponse("admin/tickets/detail.html", {
        "request": request,
        "user": user,
        "ticket": ticket,
        "staff_list": staff_list,
        "csrf_token": csrf,
        "categories": TicketCategory,
        "active_page": "tickets",
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


# ==========================================
# Admin Reply
# ==========================================

@router.post("/{ticket_id}/reply")
async def admin_ticket_reply(
    ticket_id: int,
    request: Request,
    body: str = Form(...),
    csrf_token: str = Form(""),
    files: List[UploadFile] = File(None),
    user=Depends(require_permission("tickets")),
    db: Session = Depends(get_db),
):
    csrf_check(request, csrf_token)

    sender_name = getattr(user, "full_name", "پشتیبانی") or "پشتیبانی"
    result = ticket_service.add_message(
        db, ticket_id,
        sender_type=SenderType.STAFF,
        sender_name=sender_name,
        body=body,
        files=files or [],
    )

    if result["success"]:
        ticket = ticket_service.get_ticket(db, ticket_id)
        if ticket and not ticket.assigned_to:
            ticket_service.assign_ticket(db, ticket_id, user.id)
        db.commit()
    else:
        db.rollback()

    return RedirectResponse(f"/admin/tickets/{ticket_id}", status_code=302)


# ==========================================
# Internal Note (Staff-only, invisible to customer/dealer)
# ==========================================

@router.post("/{ticket_id}/internal-note")
async def admin_ticket_internal_note(
    ticket_id: int,
    request: Request,
    body: str = Form(...),
    csrf_token: str = Form(""),
    files: List[UploadFile] = File(None),
    user=Depends(require_permission("tickets")),
    db: Session = Depends(get_db),
):
    csrf_check(request, csrf_token)

    sender_name = getattr(user, "full_name", "پشتیبانی") or "پشتیبانی"
    result = ticket_service.add_message(
        db, ticket_id,
        sender_type=SenderType.STAFF,
        sender_name=sender_name,
        body=body,
        files=files or [],
        is_internal=True,
    )

    if result["success"]:
        db.commit()
    else:
        db.rollback()

    return RedirectResponse(f"/admin/tickets/{ticket_id}", status_code=302)


# ==========================================
# Change Status
# ==========================================

@router.post("/{ticket_id}/status")
async def admin_ticket_status(
    ticket_id: int,
    request: Request,
    new_status: str = Form(...),
    csrf_token: str = Form(""),
    user=Depends(require_permission("tickets")),
    db: Session = Depends(get_db),
):
    csrf_check(request, csrf_token)

    result = ticket_service.update_status(db, ticket_id, new_status)
    if result["success"]:
        db.commit()
    return RedirectResponse(f"/admin/tickets/{ticket_id}", status_code=302)


# ==========================================
# Close Ticket (Admin)
# ==========================================

@router.post("/{ticket_id}/close")
async def admin_ticket_close(
    ticket_id: int,
    request: Request,
    csrf_token: str = Form(""),
    user=Depends(require_permission("tickets")),
    db: Session = Depends(get_db),
):
    csrf_check(request, csrf_token)

    result = ticket_service.close_ticket(db, ticket_id)
    if result["success"]:
        db.commit()
    return RedirectResponse(f"/admin/tickets/{ticket_id}", status_code=302)


# ==========================================
# Change Category (Department Transfer)
# ==========================================

@router.post("/{ticket_id}/category")
async def admin_ticket_category(
    ticket_id: int,
    request: Request,
    new_category: str = Form(...),
    csrf_token: str = Form(""),
    user=Depends(require_permission("tickets")),
    db: Session = Depends(get_db),
):
    csrf_check(request, csrf_token)

    result = ticket_service.change_category(db, ticket_id, new_category)
    if result["success"]:
        db.commit()
    return RedirectResponse(f"/admin/tickets/{ticket_id}", status_code=302)


# ==========================================
# Assign Ticket
# ==========================================

@router.post("/{ticket_id}/assign")
async def admin_ticket_assign(
    ticket_id: int,
    request: Request,
    staff_id: str = Form(...),
    csrf_token: str = Form(""),
    user=Depends(require_permission("tickets")),
    db: Session = Depends(get_db),
):
    csrf_check(request, csrf_token)

    sid = int(staff_id) if staff_id.strip() else None
    if sid:
        result = ticket_service.assign_ticket(db, ticket_id, sid)
        if result["success"]:
            db.commit()

    return RedirectResponse(f"/admin/tickets/{ticket_id}", status_code=302)
