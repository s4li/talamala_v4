"""
Profile & Address Routes
==========================
Customer profile view/edit + address book CRUD.
"""

import urllib.parse
from typing import Optional

from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session

from config.database import get_db
from common.templating import templates
from common.security import csrf_check, new_csrf_token
from modules.auth.deps import require_customer
from modules.customer.models import Customer
from modules.customer.address_models import CustomerAddress, GeoProvince, GeoCity, GeoDistrict

router = APIRouter(tags=["profile"])


# ==========================================
# 👤 Profile
# ==========================================

@router.get("/profile", response_class=HTMLResponse)
async def profile_page(
    request: Request,
    msg: str = None,
    error: str = None,
    db: Session = Depends(get_db),
    me=Depends(require_customer),
):
    csrf = new_csrf_token()
    response = templates.TemplateResponse("shop/profile.html", {
        "request": request,
        "user": me,
        "cart_count": 0,
        "csrf_token": csrf,
        "msg": msg,
        "error": error,
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


@router.post("/profile")
async def profile_update(
    request: Request,
    birth_date: str = Form(""),
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
    me=Depends(require_customer),
):
    """Update editable profile fields only (name/national_id locked for shahkar)."""
    csrf_check(request, csrf_token)

    if birth_date:
        me.birth_date = birth_date.strip()
    db.commit()

    msg = urllib.parse.quote("اطلاعات پروفایل بروزرسانی شد.")
    return RedirectResponse(f"/profile?msg={msg}", status_code=303)


# ==========================================
# 📬 Addresses
# ==========================================

@router.get("/addresses", response_class=HTMLResponse)
async def address_list(
    request: Request,
    msg: str = None,
    db: Session = Depends(get_db),
    me=Depends(require_customer),
):
    addresses = db.query(CustomerAddress).filter(
        CustomerAddress.customer_id == me.id
    ).order_by(CustomerAddress.is_default.desc(), CustomerAddress.id.desc()).all()

    provinces = db.query(GeoProvince).order_by(GeoProvince.sort_order, GeoProvince.name).all()

    csrf = new_csrf_token()
    response = templates.TemplateResponse("shop/addresses.html", {
        "request": request,
        "user": me,
        "addresses": addresses,
        "provinces": provinces,
        "cart_count": 0,
        "csrf_token": csrf,
        "msg": msg,
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


@router.post("/addresses")
async def address_add(
    request: Request,
    title: str = Form(...),
    province_id: int = Form(...),
    city_id: int = Form(...),
    district_id: str = Form(""),
    address: str = Form(...),
    postal_code: str = Form(""),
    receiver_name: str = Form(""),
    receiver_phone: str = Form(""),
    is_default: str = Form(""),
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
    me=Depends(require_customer),
):
    csrf_check(request, csrf_token)

    dist_id = int(district_id) if district_id.strip().isdigit() else None

    if is_default == "on":
        db.query(CustomerAddress).filter(CustomerAddress.customer_id == me.id).update({"is_default": False})

    addr = CustomerAddress(
        customer_id=me.id,
        title=title.strip(),
        province_id=province_id,
        city_id=city_id,
        district_id=dist_id,
        address=address.strip(),
        postal_code=postal_code.strip() or None,
        receiver_name=receiver_name.strip() or None,
        receiver_phone=receiver_phone.strip() or None,
        is_default=(is_default == "on"),
    )
    db.add(addr)
    db.commit()

    msg = urllib.parse.quote("آدرس جدید ذخیره شد.")
    return RedirectResponse(f"/addresses?msg={msg}", status_code=303)


@router.post("/addresses/{addr_id}/delete")
async def address_delete(
    request: Request,
    addr_id: int,
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
    me=Depends(require_customer),
):
    csrf_check(request, csrf_token)
    addr = db.query(CustomerAddress).filter(
        CustomerAddress.id == addr_id, CustomerAddress.customer_id == me.id
    ).first()
    if addr:
        db.delete(addr)
        db.commit()
    msg = urllib.parse.quote("آدرس حذف شد.")
    return RedirectResponse(f"/addresses?msg={msg}", status_code=303)


@router.post("/addresses/{addr_id}/default")
async def address_set_default(
    request: Request,
    addr_id: int,
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
    me=Depends(require_customer),
):
    csrf_check(request, csrf_token)
    db.query(CustomerAddress).filter(CustomerAddress.customer_id == me.id).update({"is_default": False})
    addr = db.query(CustomerAddress).filter(
        CustomerAddress.id == addr_id, CustomerAddress.customer_id == me.id
    ).first()
    if addr:
        addr.is_default = True
        db.commit()
    return RedirectResponse("/addresses", status_code=303)


# ==========================================
# 🌍 Geo API (for AJAX in address form)
# ==========================================

@router.get("/api/geo/cities")
async def api_geo_cities(province_id: int, db: Session = Depends(get_db)):
    cities = db.query(GeoCity).filter(GeoCity.province_id == province_id).order_by(GeoCity.sort_order, GeoCity.name).all()
    return [{"id": c.id, "name": c.name} for c in cities]


@router.get("/api/geo/districts")
async def api_geo_districts(city_id: int, db: Session = Depends(get_db)):
    districts = db.query(GeoDistrict).filter(GeoDistrict.city_id == city_id).order_by(GeoDistrict.name).all()
    return [{"id": d.id, "name": d.name} for d in districts]
