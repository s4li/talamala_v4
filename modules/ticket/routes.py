"""
Ticket Module - Routes (Customer + Dealer Facing)
=====================================================
Both Customer and Dealer share /tickets prefix,
using different templates based on user type.
"""

from typing import List, Optional
from fastapi import APIRouter, Request, Depends, Form, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from config.database import get_db
from common.templating import templates
from common.security import new_csrf_token, csrf_check
from modules.auth.deps import get_current_active_user
from modules.ticket.service import ticket_service
from modules.ticket.models import TicketPriority, TicketCategory, SenderType, TicketStatus

router = APIRouter(prefix="/tickets", tags=["tickets"])


def _get_user_info(user):
    """Determine sender type, ID, template prefix, and context key."""
    if not user:
        raise HTTPException(status_code=401, detail="login_required")

    if getattr(user, "is_dealer", False):
        return SenderType.DEALER, user.id, "dealer", "dealer", user
    elif not getattr(user, "is_staff", False):
        return SenderType.CUSTOMER, user.id, "shop", "user", user
    else:
        raise HTTPException(status_code=403, detail="از پنل مدیریت استفاده کنید")


# ==========================================
# Ticket List
# ==========================================

@router.get("", response_class=HTMLResponse)
async def ticket_list(
    request: Request,
    page: int = 1,
    user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    sender_type, sender_id, tpl_prefix, ctx_key, ctx_val = _get_user_info(user)

    if sender_type == SenderType.CUSTOMER:
        tickets, total = ticket_service.list_tickets_for_customer(db, sender_id, page=page)
    else:
        tickets, total = ticket_service.list_tickets_for_dealer(db, sender_id, page=page)

    total_pages = max(1, (total + 19) // 20)

    response = templates.TemplateResponse(f"{tpl_prefix}/tickets.html", {
        "request": request,
        ctx_key: ctx_val,
        "tickets": tickets,
        "total": total,
        "page": page,
        "total_pages": total_pages,
        "active_page": "tickets",
    })
    return response


# ==========================================
# New Ticket Form
# ==========================================

@router.get("/new", response_class=HTMLResponse)
async def ticket_new_form(
    request: Request,
    user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    sender_type, sender_id, tpl_prefix, ctx_key, ctx_val = _get_user_info(user)

    csrf = new_csrf_token()
    response = templates.TemplateResponse(f"{tpl_prefix}/ticket_new.html", {
        "request": request,
        ctx_key: ctx_val,
        "csrf_token": csrf,
        "categories": TicketCategory,
        "active_page": "tickets",
        "error": None,
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


# ==========================================
# Create Ticket (POST)
# ==========================================

@router.post("/new")
async def ticket_create(
    request: Request,
    subject: str = Form(...),
    body: str = Form(...),
    priority: str = Form("Medium"),
    category: str = Form("Other"),
    csrf_token: str = Form(""),
    files: List[UploadFile] = File(None),
    user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    csrf_check(request, csrf_token)
    sender_type, sender_id, tpl_prefix, ctx_key, ctx_val = _get_user_info(user)

    result = ticket_service.create_ticket(
        db, sender_type=sender_type, sender_id=sender_id,
        subject=subject, body=body, priority=priority,
        category=category, files=files or [],
    )

    if result["success"]:
        db.commit()
        return RedirectResponse(f"/tickets/{result['ticket'].id}", status_code=302)

    db.rollback()
    csrf = new_csrf_token()
    response = templates.TemplateResponse(f"{tpl_prefix}/ticket_new.html", {
        "request": request,
        ctx_key: ctx_val,
        "csrf_token": csrf,
        "categories": TicketCategory,
        "active_page": "tickets",
        "error": result["message"],
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


# ==========================================
# Ticket Detail + Messages
# ==========================================

@router.get("/{ticket_id}", response_class=HTMLResponse)
async def ticket_detail(
    ticket_id: int,
    request: Request,
    user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    sender_type, sender_id, tpl_prefix, ctx_key, ctx_val = _get_user_info(user)

    ticket = ticket_service.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="تیکت یافت نشد")

    # Ownership check
    if sender_type == SenderType.CUSTOMER and ticket.customer_id != sender_id:
        raise HTTPException(status_code=403, detail="دسترسی غیرمجاز")
    if sender_type == SenderType.DEALER and ticket.dealer_id != sender_id:
        raise HTTPException(status_code=403, detail="دسترسی غیرمجاز")

    csrf = new_csrf_token()
    response = templates.TemplateResponse(f"{tpl_prefix}/ticket_detail.html", {
        "request": request,
        ctx_key: ctx_val,
        "ticket": ticket,
        "csrf_token": csrf,
        "active_page": "tickets",
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


# ==========================================
# Add Message (Reply)
# ==========================================

@router.post("/{ticket_id}/message")
async def ticket_add_message(
    ticket_id: int,
    request: Request,
    body: str = Form(...),
    csrf_token: str = Form(""),
    files: List[UploadFile] = File(None),
    user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    csrf_check(request, csrf_token)
    sender_type, sender_id, tpl_prefix, ctx_key, ctx_val = _get_user_info(user)

    ticket = ticket_service.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="تیکت یافت نشد")
    if sender_type == SenderType.CUSTOMER and ticket.customer_id != sender_id:
        raise HTTPException(status_code=403, detail="دسترسی غیرمجاز")
    if sender_type == SenderType.DEALER and ticket.dealer_id != sender_id:
        raise HTTPException(status_code=403, detail="دسترسی غیرمجاز")

    sender_name = getattr(user, "full_name", "کاربر") or "کاربر"

    result = ticket_service.add_message(
        db, ticket_id, sender_type=sender_type,
        sender_name=sender_name, body=body,
        files=files or [],
    )

    if result["success"]:
        db.commit()
    else:
        db.rollback()

    return RedirectResponse(f"/tickets/{ticket_id}", status_code=302)


# ==========================================
# Close Ticket (by user)
# ==========================================

@router.post("/{ticket_id}/close")
async def ticket_close(
    ticket_id: int,
    request: Request,
    csrf_token: str = Form(""),
    user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    csrf_check(request, csrf_token)
    sender_type, sender_id, tpl_prefix, ctx_key, ctx_val = _get_user_info(user)

    ticket = ticket_service.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="تیکت یافت نشد")
    if sender_type == SenderType.CUSTOMER and ticket.customer_id != sender_id:
        raise HTTPException(status_code=403, detail="دسترسی غیرمجاز")
    if sender_type == SenderType.DEALER and ticket.dealer_id != sender_id:
        raise HTTPException(status_code=403, detail="دسترسی غیرمجاز")

    result = ticket_service.close_ticket(db, ticket_id)
    if result["success"]:
        db.commit()

    return RedirectResponse(f"/tickets/{ticket_id}", status_code=302)
