"""
Admin Staff Management Routes
================================
CRUD for admin/operator users and their permissions.
"""

from typing import Optional
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from config.database import get_db
from common.templating import templates
from common.security import csrf_check, new_csrf_token
from modules.auth.deps import require_permission
from modules.admin.staff_service import staff_service
from modules.admin.permissions import PERMISSION_REGISTRY, ALL_PERMISSION_KEYS

router = APIRouter(prefix="/admin/staff", tags=["admin-staff"])


# ==========================================
# Staff List
# ==========================================

@router.get("", response_class=HTMLResponse)
async def staff_list(
    request: Request,
    msg: str = None,
    db: Session = Depends(get_db),
    user=Depends(require_permission("staff")),
):
    staff_users = staff_service.list_staff(db)

    csrf = new_csrf_token()
    response = templates.TemplateResponse("admin/staff/list.html", {
        "request": request,
        "user": user,
        "staff_users": staff_users,
        "csrf_token": csrf,
        "msg": msg,
        "permissions_registry": PERMISSION_REGISTRY,
        "active_page": "staff",
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


# ==========================================
# Create Staff
# ==========================================

@router.get("/create", response_class=HTMLResponse)
async def create_staff_form(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_permission("staff")),
):
    csrf = new_csrf_token()
    response = templates.TemplateResponse("admin/staff/form.html", {
        "request": request,
        "user": user,
        "staff_user": None,
        "permissions_registry": PERMISSION_REGISTRY,
        "csrf_token": csrf,
        "active_page": "staff",
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


@router.post("/create")
async def create_staff(
    request: Request,
    mobile: str = Form(...),
    full_name: str = Form(...),
    role: str = Form("operator"),
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
    user=Depends(require_permission("staff")),
):
    csrf_check(request, csrf_token)

    # Check duplicate
    if staff_service.get_by_mobile(db, mobile.strip()):
        csrf = new_csrf_token()
        response = templates.TemplateResponse("admin/staff/form.html", {
            "request": request,
            "user": user,
            "staff_user": None,
            "permissions_registry": PERMISSION_REGISTRY,
            "csrf_token": csrf,
            "error": "این شماره موبایل قبلا ثبت شده است.",
            "active_page": "staff",
        })
        response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
        return response

    # Extract permissions from checkboxes
    form_data = await request.form()
    perms = [key for key in ALL_PERMISSION_KEYS if form_data.get(f"perm_{key}")]

    staff_service.create_staff(
        db, mobile=mobile.strip(), full_name=full_name.strip(),
        role=role, permissions=perms,
    )
    db.commit()
    return RedirectResponse("/admin/staff?msg=created", status_code=302)


# ==========================================
# Edit Staff
# ==========================================

@router.get("/{staff_id}/edit", response_class=HTMLResponse)
async def edit_staff_form(
    request: Request,
    staff_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_permission("staff")),
):
    staff_user = staff_service.get_by_id(db, staff_id)
    if not staff_user:
        raise HTTPException(404, "کاربر یافت نشد")

    csrf = new_csrf_token()
    response = templates.TemplateResponse("admin/staff/form.html", {
        "request": request,
        "user": user,
        "staff_user": staff_user,
        "permissions_registry": PERMISSION_REGISTRY,
        "csrf_token": csrf,
        "active_page": "staff",
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


@router.post("/{staff_id}/edit")
async def edit_staff(
    request: Request,
    staff_id: int,
    full_name: str = Form(...),
    role: str = Form("operator"),
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
    user=Depends(require_permission("staff")),
):
    csrf_check(request, csrf_token)

    form_data = await request.form()
    perms = [key for key in ALL_PERMISSION_KEYS if form_data.get(f"perm_{key}")]

    staff_service.update_staff(db, staff_id, full_name=full_name.strip(), role=role)
    staff_service.update_permissions(db, staff_id, perms)
    db.commit()
    return RedirectResponse("/admin/staff?msg=updated", status_code=302)
