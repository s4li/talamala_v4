"""
Profile & Address Routes
==========================
Customer profile view/edit + address book CRUD.
"""

import urllib.parse
from typing import Optional

from fastapi import APIRouter, Request, Depends, Form, Query, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session

from config.database import get_db
from common.templating import templates
from common.security import csrf_check, new_csrf_token
from modules.auth.deps import require_login
from modules.user.models import User
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
    return_to: str = None,
    db: Session = Depends(get_db),
    me=Depends(require_login),
):
    from common.templating import get_setting_from_db
    shahkar_enabled = get_setting_from_db(db, "shahkar_enabled", "false") == "true"

    csrf = new_csrf_token()
    response = templates.TemplateResponse("shop/profile.html", {
        "request": request,
        "user": me,
        "cart_count": 0,
        "csrf_token": csrf,
        "msg": msg,
        "error": error,
        "next_url": return_to or "",
        "shahkar_enabled": shahkar_enabled,
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


@router.post("/profile")
async def profile_update(
    request: Request,
    first_name: str = Form(""),
    last_name: str = Form(""),
    national_id: str = Form(""),
    customer_type: str = Form("real"),
    company_name: str = Form(""),
    economic_code: str = Form(""),
    postal_code: str = Form(""),
    address: str = Form(""),
    phone: str = Form(""),
    birth_date: str = Form(""),
    csrf_token: str = Form(""),
    return_to: str = Query(None),
    db: Session = Depends(get_db),
    me=Depends(require_login),
):
    """Update profile fields (identity fields editable until Shahkar verification)."""
    csrf_check(request, csrf_token)
    from common.helpers import validate_iranian_national_id

    # Identity fields
    if first_name.strip():
        me.first_name = first_name.strip()
    if last_name.strip():
        me.last_name = last_name.strip()

    # National ID: only editable if not set yet (GUEST_ prefix or empty)
    has_real_national_id = me.national_id and not me.national_id.startswith("GUEST_")
    if national_id.strip() and not has_real_national_id:
        if not validate_iranian_national_id(national_id.strip()):
            msg = urllib.parse.quote("کد ملی نامعتبر است. لطفاً یک کد ملی ۱۰ رقمی معتبر وارد کنید.")
            return RedirectResponse(f"/profile?error={msg}", status_code=303)
        # Check uniqueness
        if national_id.strip() != me.national_id:
            existing = db.query(User).filter(
                User.national_id == national_id.strip(),
                User.id != me.id,
            ).first()
            if existing:
                msg = urllib.parse.quote("این کد ملی قبلاً ثبت شده است.")
                return RedirectResponse(f"/profile?error={msg}", status_code=303)
            me.national_id = national_id.strip()

    # Customer type
    if customer_type in ("real", "legal"):
        me.customer_type = customer_type

    # Legal entity fields
    if customer_type == "legal":
        me.company_name = company_name.strip() or None
        me.economic_code = economic_code.strip() or None
    else:
        me.company_name = None
        me.economic_code = None

    # Contact & address
    me.postal_code = postal_code.strip() or None
    me.address = address.strip() or None
    me.phone = phone.strip() or None
    if birth_date:
        me.birth_date = birth_date.strip()

    db.commit()

    msg = urllib.parse.quote("اطلاعات پروفایل بروزرسانی شد.")
    redirect_url = f"/profile?msg={msg}"
    if return_to and return_to.startswith("/"):
        redirect_url += f"&return_to={urllib.parse.quote(return_to)}"
    return RedirectResponse(redirect_url, status_code=303)


# ==========================================
# 🔐 Shahkar Verification
# ==========================================

@router.post("/profile/verify-shahkar")
async def verify_shahkar_route(
    request: Request,
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
    me=Depends(require_login),
):
    """Call Shahkar API to verify customer's mobile + national_id."""
    csrf_check(request, csrf_token)
    from common.helpers import now_utc
    from modules.customer.shahkar_service import verify_shahkar

    # Must have a real national_id set
    if not me.national_id or me.national_id.startswith("GUEST_"):
        error = urllib.parse.quote("لطفاً ابتدا کد ملی خود را در پروفایل وارد کنید.")
        return RedirectResponse(f"/profile?error={error}", status_code=303)

    result = verify_shahkar(db, me.mobile, me.national_id)

    if result.get("skip"):
        error = urllib.parse.quote("سرویس احراز هویت شاهکار غیرفعال است.")
        return RedirectResponse(f"/profile?error={error}", status_code=303)

    if result.get("matched"):
        me.shahkar_verified = True
        me.shahkar_verified_at = now_utc()
        db.commit()
        msg = urllib.parse.quote("احراز هویت شاهکار با موفقیت انجام شد.")
        return RedirectResponse(f"/profile?msg={msg}", status_code=303)
    else:
        error = urllib.parse.quote(result.get("error", "خطا در احراز هویت."))
        return RedirectResponse(f"/profile?error={error}", status_code=303)


# ==========================================
# 📬 Addresses
# ==========================================

@router.get("/addresses", response_class=HTMLResponse)
async def address_list(
    request: Request,
    msg: str = None,
    next: str = None,
    db: Session = Depends(get_db),
    me=Depends(require_login),
):
    addresses = db.query(CustomerAddress).filter(
        CustomerAddress.user_id == me.id
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
        "next_url": next,
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
    next_url: str = Form(""),
    db: Session = Depends(get_db),
    me=Depends(require_login),
):
    csrf_check(request, csrf_token)

    dist_id = int(district_id) if district_id.strip().isdigit() else None

    if is_default == "on":
        db.query(CustomerAddress).filter(CustomerAddress.user_id == me.id).update({"is_default": False})

    addr = CustomerAddress(
        user_id=me.id,
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

    # Redirect back to the page that sent us here (e.g. /checkout)
    redirect_to = next_url.strip() if next_url and next_url.strip().startswith("/") else None
    if redirect_to:
        return RedirectResponse(redirect_to, status_code=303)

    msg = urllib.parse.quote("آدرس جدید ذخیره شد.")
    return RedirectResponse(f"/addresses?msg={msg}", status_code=303)


@router.post("/addresses/{addr_id}/delete")
async def address_delete(
    request: Request,
    addr_id: int,
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
    me=Depends(require_login),
):
    csrf_check(request, csrf_token)
    addr = db.query(CustomerAddress).filter(
        CustomerAddress.id == addr_id, CustomerAddress.user_id == me.id
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
    me=Depends(require_login),
):
    csrf_check(request, csrf_token)
    db.query(CustomerAddress).filter(CustomerAddress.user_id == me.id).update({"is_default": False})
    addr = db.query(CustomerAddress).filter(
        CustomerAddress.id == addr_id, CustomerAddress.user_id == me.id
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


@router.get("/api/geo/dealers")
async def api_geo_dealers(
    province_id: Optional[int] = None,
    city_id: Optional[int] = None,
    district_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """Return active dealers filtered by province/city/district (all optional)."""
    q = db.query(User).filter(User.is_dealer == True, User.is_active == True)
    if province_id:
        q = q.filter(User.province_id == province_id)
    if city_id:
        q = q.filter(User.city_id == city_id)
    if district_id:
        q = q.filter(User.district_id == district_id)
    dealers = q.order_by(User.first_name, User.last_name).all()
    return [{"id": d.id, "full_name": d.full_name, "type_label": d.type_label} for d in dealers]


# ==========================================
# 🎁 Invite Friends (Referral)
# ==========================================

@router.get("/invite", response_class=HTMLResponse)
async def invite_page(
    request: Request,
    db: Session = Depends(get_db),
    me=Depends(require_login),
):
    from modules.user.models import generate_referral_code
    from config.settings import BASE_URL

    # Generate referral code if not set
    if not me.referral_code:
        code = None
        for _ in range(10):
            candidate = generate_referral_code()
            existing = db.query(User).filter(User.referral_code == candidate).first()
            if not existing:
                code = candidate
                break
        if not code:
            # Fallback: use longer code to avoid collision
            code = generate_referral_code(length=12)
        me.referral_code = code
        db.commit()

    referral_link = f"{BASE_URL}/auth/login?ref={me.referral_code}"

    csrf = new_csrf_token()
    response = templates.TemplateResponse("shop/invite.html", {
        "request": request,
        "user": me,
        "referral_code": me.referral_code,
        "referral_link": referral_link,
        "csrf_token": csrf,
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response
