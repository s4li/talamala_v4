"""
Auth Module - Routes
=====================
Login page, OTP send/verify, logout.
"""

from fastapi import APIRouter, Request, Depends, Form, Response
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session

from config.database import get_db
from common.templating import templates
from common.security import new_csrf_token, csrf_check, get_cookie_kwargs
from common.sms import sms_sender
from common.exceptions import OTPError, AuthenticationError
from modules.auth.service import auth_service
from modules.auth.deps import get_current_active_user

router = APIRouter(prefix="/auth", tags=["auth"])


def _safe_next_url(url: str) -> str:
    """Only allow relative paths as redirect targets (prevent open redirect)."""
    if not url or not url.startswith("/"):
        return "/"
    return url


def _reg_context(**kwargs) -> dict:
    """Build template context dict with all registration fields (defaults to empty)."""
    defaults = {
        "first_name": "", "last_name": "", "ref_code": "",
        "reg_national_id": "", "reg_birth_date": "", "reg_customer_type": "real",
        "reg_company_name": "", "reg_economic_code": "",
        "reg_phone": "", "reg_postal_code": "", "reg_address": "",
    }
    defaults.update(kwargs)
    return defaults


@router.get("/login", response_class=HTMLResponse)
async def login_page(
    request: Request,
    next: str = "",
    ref: str = "",
    user=Depends(get_current_active_user),
):
    """Show login page (redirect if already logged in)."""
    if user:
        if getattr(user, "is_staff", False):
            return RedirectResponse("/admin/dashboard", status_code=302)
        if getattr(user, "is_dealer", False):
            return RedirectResponse("/dealer/dashboard", status_code=302)
        return RedirectResponse(_safe_next_url(next), status_code=302)

    # If ref code is provided (from invite link), default to register tab
    mode = "register" if ref else "login"

    csrf = new_csrf_token()
    response = templates.TemplateResponse("auth/login.html", {
        "request": request,
        "csrf_token": csrf,
        "step": "mobile",
        "error": None,
        "mobile": "",
        "next_url": next,
        "mode": mode,
        **_reg_context(ref_code=ref.strip().upper()),
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


@router.post("/send-otp")
async def send_otp(
    request: Request,
    mobile: str = Form(...),
    next_url: str = Form(""),
    csrf_token: str = Form(""),
    mode: str = Form("login"),
    first_name: str = Form(""),
    last_name: str = Form(""),
    ref_code: str = Form(""),
    # Profile fields (register mode only)
    national_id: str = Form(""),
    birth_date: str = Form(""),
    customer_type: str = Form("real"),
    company_name: str = Form(""),
    economic_code: str = Form(""),
    phone: str = Form(""),
    postal_code: str = Form(""),
    address: str = Form(""),
    db: Session = Depends(get_db),
):
    """Send OTP to mobile number."""
    csrf_check(request, csrf_token)

    ref_code = ref_code.strip().upper()

    # Collect all reg fields for re-rendering on error
    reg_fields = _reg_context(
        first_name=first_name.strip(),
        last_name=last_name.strip(),
        ref_code=ref_code,
        reg_national_id=national_id.strip(),
        reg_birth_date=birth_date.strip(),
        reg_customer_type=customer_type.strip(),
        reg_company_name=company_name.strip(),
        reg_economic_code=economic_code.strip(),
        reg_phone=phone.strip(),
        reg_postal_code=postal_code.strip(),
        reg_address=address.strip(),
    )

    def _error_response(error_msg: str):
        csrf = new_csrf_token()
        resp = templates.TemplateResponse("auth/login.html", {
            "request": request,
            "csrf_token": csrf,
            "step": "mobile",
            "mobile": mobile,
            "error": error_msg,
            "next_url": next_url,
            "mode": "register",
            **reg_fields,
        })
        resp.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
        return resp

    # Registration mode: validate fields
    if mode == "register":
        first_name = first_name.strip()
        last_name = last_name.strip()
        national_id = national_id.strip()
        postal_code = postal_code.strip()
        address = address.strip()

        if not first_name or not last_name:
            return _error_response("لطفاً نام و نام خانوادگی را وارد کنید.")

        if not national_id:
            return _error_response("لطفاً کد ملی را وارد کنید.")

        if not postal_code:
            return _error_response("لطفاً کد پستی را وارد کنید.")

        if not address:
            return _error_response("لطفاً نشانی را وارد کنید.")

        if customer_type == "legal" and not company_name.strip():
            return _error_response("لطفاً نام شرکت را وارد کنید.")

        # Check if mobile already exists
        from modules.customer.models import Customer
        existing = db.query(Customer).filter(Customer.mobile == mobile.strip()).first()
        if existing:
            return _error_response("این شماره قبلاً ثبت نام شده است. لطفاً از بخش ورود استفاده کنید.")

        # Check if national_id already exists
        existing_nid = db.query(Customer).filter(Customer.national_id == national_id).first()
        if existing_nid:
            return _error_response("این کد ملی قبلاً ثبت شده است.")

        # Validate referral code if provided
        if ref_code:
            referrer = db.query(Customer).filter(Customer.referral_code == ref_code).first()
            if not referrer:
                return _error_response("کد معرف نامعتبر است.")

    try:
        profile_data = {}
        if mode == "register":
            profile_data = {
                "national_id": national_id.strip(),
                "birth_date": birth_date.strip(),
                "customer_type": customer_type.strip(),
                "company_name": company_name.strip(),
                "economic_code": economic_code.strip(),
                "phone": phone.strip(),
                "postal_code": postal_code.strip(),
                "address": address.strip(),
            }

        otp_raw, display_name = auth_service.send_otp(
            db, mobile,
            first_name=first_name.strip() if mode == "register" else "",
            last_name=last_name.strip() if mode == "register" else "",
            ref_code=ref_code if mode == "register" else "",
            profile_data=profile_data if mode == "register" else {},
        )

        # Send SMS (debug mode prints to console)
        sms_sender.send_otp_lookup(
            receptor=mobile,
            token=display_name,
            token2=otp_raw,
            template_name="OTP",
        )

        csrf = new_csrf_token()
        response = templates.TemplateResponse("auth/login.html", {
            "request": request,
            "csrf_token": csrf,
            "step": "verify",
            "mobile": mobile,
            "error": None,
            "next_url": next_url,
            "ref_code": ref_code,
        })
        response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
        return response

    except OTPError as e:
        csrf = new_csrf_token()
        response = templates.TemplateResponse("auth/login.html", {
            "request": request,
            "csrf_token": csrf,
            "step": "mobile",
            "mobile": mobile,
            "error": e.message,
            "next_url": next_url,
            "mode": mode,
            **reg_fields,
        })
        response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
        return response


@router.post("/verify-otp")
async def verify_otp(
    request: Request,
    mobile: str = Form(...),
    code: str = Form(...),
    next_url: str = Form(""),
    csrf_token: str = Form(""),
    ref_code: str = Form(""),
    db: Session = Depends(get_db),
):
    """Verify OTP and login."""
    csrf_check(request, csrf_token)

    try:
        token, cookie_name, redirect_url = auth_service.verify_otp(db, mobile, code)

        # Referral reward: credit referrer's wallet (only once per customer)
        if cookie_name == "customer_token" and ref_code:
            _process_referral_reward(db, mobile, ref_code.strip().upper())

        # For customers, use next_url if provided (return to original page)
        if next_url and cookie_name == "customer_token":
            redirect_url = _safe_next_url(next_url)

        # If customer profile is incomplete, redirect to profile page
        if cookie_name == "customer_token" and not next_url:
            from modules.customer.models import Customer
            customer = db.query(Customer).filter(Customer.mobile == mobile.strip()).first()
            if customer and not customer.is_profile_complete:
                redirect_url = "/profile"

        response = RedirectResponse(redirect_url, status_code=302)
        response.set_cookie(cookie_name, token, **get_cookie_kwargs())
        return response

    except AuthenticationError as e:
        csrf = new_csrf_token()
        response = templates.TemplateResponse("auth/login.html", {
            "request": request,
            "csrf_token": csrf,
            "step": "verify",
            "mobile": mobile,
            "error": e.message,
            "next_url": next_url,
            "ref_code": ref_code,
        })
        response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
        return response


def _process_referral_reward(db: Session, new_mobile: str, ref_code: str):
    """Credit referrer's wallet if this is a new registration with valid referral code."""
    from modules.customer.models import Customer
    from modules.wallet.service import wallet_service

    REFERRAL_REWARD_RIAL = 500_000  # 50,000 toman = 500,000 rial

    # Find the new customer
    customer = db.query(Customer).filter(Customer.mobile == new_mobile.strip()).first()
    if not customer or customer.referral_rewarded:
        return  # Already rewarded or not found

    if not customer.referred_by:
        return  # No referrer set

    # Find the referrer
    referrer = db.query(Customer).filter(Customer.id == customer.referred_by).first()
    if not referrer:
        return

    # Credit referrer's wallet
    try:
        wallet_service.deposit(
            db,
            owner_id=referrer.id,
            amount=REFERRAL_REWARD_RIAL,
            reference_type="referral",
            reference_id=str(customer.id),
            description=f"پاداش معرفی کاربر جدید ({customer.full_name})",
            idempotency_key=f"referral_reward:{customer.id}",
        )
        customer.referral_rewarded = True
        db.commit()
    except Exception:
        db.rollback()


@router.get("/logout")
async def logout(request: Request):
    """Clear auth cookies and redirect to login."""
    response = RedirectResponse("/auth/login", status_code=302)
    response.delete_cookie("auth_token")
    response.delete_cookie("customer_token")
    response.delete_cookie("dealer_token")
    response.delete_cookie("csrf_token")
    return response
