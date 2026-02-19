"""
Dealer Request Module - Customer Routes
==========================================
GET /dealer-request  - Show form or status
POST /dealer-request - Submit application
"""

from typing import List
from fastapi import APIRouter, Request, Depends, Form, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from config.database import get_db
from common.templating import templates
from common.security import new_csrf_token, csrf_check
from modules.auth.deps import require_customer
from modules.customer.address_models import GeoProvince
from modules.dealer_request.service import dealer_request_service
from modules.dealer_request.models import DealerRequestStatus

router = APIRouter(tags=["dealer-request"])


# ==========================================
# GET - Form or Status
# ==========================================

@router.get("/dealer-request", response_class=HTMLResponse)
async def dealer_request_form(
    request: Request,
    msg: str = None,
    error: str = None,
    db: Session = Depends(get_db),
    me=Depends(require_customer),
):
    # Check if customer already has an active (PENDING/APPROVED) request
    active = dealer_request_service.get_active_request(db, me.id)
    if active:
        csrf = new_csrf_token()
        response = templates.TemplateResponse("shop/dealer_request_status.html", {
            "request": request,
            "user": me,
            "dealer_request": active,
            "csrf_token": csrf,
        })
        response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
        return response

    # Show the form
    provinces = db.query(GeoProvince).order_by(GeoProvince.sort_order, GeoProvince.name).all()

    csrf = new_csrf_token()
    response = templates.TemplateResponse("shop/dealer_request.html", {
        "request": request,
        "user": me,
        "provinces": provinces,
        "csrf_token": csrf,
        "msg": msg,
        "error": error,
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


# ==========================================
# POST - Submit Request
# ==========================================

@router.post("/dealer-request")
async def dealer_request_submit(
    request: Request,
    first_name: str = Form(...),
    last_name: str = Form(...),
    mobile: str = Form(...),
    province_id: int = Form(...),
    city_id: int = Form(...),
    birth_date: str = Form(""),
    email: str = Form(""),
    gender: str = Form(""),
    csrf_token: str = Form(""),
    files: List[UploadFile] = File(None),
    db: Session = Depends(get_db),
    me=Depends(require_customer),
):
    csrf_check(request, csrf_token)

    # Validate required fields
    if not first_name.strip() or not last_name.strip():
        return await _render_form_with_error(request, db, me, "\u0646\u0627\u0645 \u0648 \u0646\u0627\u0645 \u062e\u0627\u0646\u0648\u0627\u062f\u06af\u06cc \u0627\u0644\u0632\u0627\u0645\u06cc \u0627\u0633\u062a.")
    if not mobile.strip():
        return await _render_form_with_error(request, db, me, "\u0634\u0645\u0627\u0631\u0647 \u062a\u0645\u0627\u0633 \u0627\u0644\u0632\u0627\u0645\u06cc \u0627\u0633\u062a.")

    result = dealer_request_service.create_request(
        db,
        customer_id=me.id,
        first_name=first_name,
        last_name=last_name,
        mobile=mobile,
        province_id=province_id,
        city_id=city_id,
        birth_date=birth_date,
        email=email,
        gender=gender,
        files=files or [],
    )

    if result["success"]:
        db.commit()
        return RedirectResponse("/dealer-request", status_code=302)

    db.rollback()
    return await _render_form_with_error(request, db, me, result["message"])


async def _render_form_with_error(request, db, me, error_msg):
    """Re-render the form with an error message."""
    provinces = db.query(GeoProvince).order_by(GeoProvince.sort_order, GeoProvince.name).all()
    csrf = new_csrf_token()
    response = templates.TemplateResponse("shop/dealer_request.html", {
        "request": request,
        "user": me,
        "provinces": provinces,
        "csrf_token": csrf,
        "msg": None,
        "error": error_msg,
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response
