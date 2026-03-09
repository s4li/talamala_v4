"""
Admin Testimonial Routes
=========================
CRUD for landing page VIP testimonials.
"""

from typing import Optional
from fastapi import (
    APIRouter, Request, Depends, Form, File, UploadFile, Query,
)
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from config.database import get_db
from common.templating import templates
from common.security import csrf_check, new_csrf_token
from common.upload import save_upload_file
from modules.auth.deps import require_permission
from modules.admin.models import Testimonial

router = APIRouter(prefix="/admin/testimonials", tags=["admin-testimonials"])


def _ctx(request, user, **extra):
    csrf = new_csrf_token(request)
    data = {
        "request": request, "user": user, "csrf_token": csrf,
        "active_page": "testimonials", **extra,
    }
    return data, csrf


# ==========================================
# List
# ==========================================

@router.get("", response_class=HTMLResponse)
async def testimonial_list(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_permission("settings")),
):
    items = (
        db.query(Testimonial)
        .order_by(Testimonial.sort_order, Testimonial.id)
        .all()
    )
    data, csrf = _ctx(request, user, items=items)
    response = templates.TemplateResponse("admin/testimonials.html", data)
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


# ==========================================
# Create
# ==========================================

@router.post("/new", response_class=RedirectResponse)
async def testimonial_create(
    request: Request,
    person_name: str = Form(...),
    person_title: str = Form(...),
    body: str = Form(...),
    sort_order: int = Form(0),
    is_active: Optional[str] = Form(None),
    avatar: UploadFile = File(None),
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
    user=Depends(require_permission("settings", level="create")),
):
    csrf_check(request, csrf_token)

    avatar_path = None
    if avatar and avatar.filename:
        avatar_path = save_upload_file(avatar, max_size=(300, 300), subfolder="testimonials")

    item = Testimonial(
        person_name=person_name.strip(),
        person_title=person_title.strip(),
        body=body.strip(),
        avatar_path=avatar_path,
        sort_order=sort_order,
        is_active=is_active == "on",
    )
    db.add(item)
    db.commit()
    return RedirectResponse("/admin/testimonials", status_code=303)


# ==========================================
# Edit
# ==========================================

@router.post("/{item_id}/edit", response_class=RedirectResponse)
async def testimonial_edit(
    request: Request,
    item_id: int,
    person_name: str = Form(...),
    person_title: str = Form(...),
    body: str = Form(...),
    sort_order: int = Form(0),
    is_active: Optional[str] = Form(None),
    avatar: UploadFile = File(None),
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
    user=Depends(require_permission("settings", level="edit")),
):
    csrf_check(request, csrf_token)

    item = db.query(Testimonial).get(item_id)
    if not item:
        return RedirectResponse("/admin/testimonials", status_code=303)

    item.person_name = person_name.strip()
    item.person_title = person_title.strip()
    item.body = body.strip()
    item.sort_order = sort_order
    item.is_active = is_active == "on"

    if avatar and avatar.filename:
        item.avatar_path = save_upload_file(avatar, max_size=(300, 300), subfolder="testimonials")

    db.commit()
    return RedirectResponse("/admin/testimonials", status_code=303)


# ==========================================
# Delete
# ==========================================

@router.post("/{item_id}/delete", response_class=RedirectResponse)
async def testimonial_delete(
    request: Request,
    item_id: int,
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
    user=Depends(require_permission("settings", level="full")),
):
    csrf_check(request, csrf_token)

    item = db.query(Testimonial).get(item_id)
    if item:
        db.delete(item)
        db.commit()
    return RedirectResponse("/admin/testimonials", status_code=303)
