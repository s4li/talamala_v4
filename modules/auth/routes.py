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


@router.get("/login", response_class=HTMLResponse)
async def login_page(
    request: Request,
    next: str = "",
    user=Depends(get_current_active_user),
):
    """Show login page (redirect if already logged in)."""
    if user:
        if getattr(user, "is_staff", False):
            return RedirectResponse("/admin/dashboard", status_code=302)
        if getattr(user, "is_dealer", False):
            return RedirectResponse("/dealer/dashboard", status_code=302)
        return RedirectResponse(_safe_next_url(next), status_code=302)

    csrf = new_csrf_token()
    response = templates.TemplateResponse("auth/login.html", {
        "request": request,
        "csrf_token": csrf,
        "step": "mobile",
        "error": None,
        "mobile": "",
        "next_url": next,
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


@router.post("/send-otp")
async def send_otp(
    request: Request,
    mobile: str = Form(...),
    next_url: str = Form(""),
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
):
    """Send OTP to mobile number."""
    csrf_check(request, csrf_token)

    try:
        otp_raw, display_name = auth_service.send_otp(db, mobile)

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
    db: Session = Depends(get_db),
):
    """Verify OTP and login."""
    csrf_check(request, csrf_token)

    try:
        token, cookie_name, redirect_url = auth_service.verify_otp(db, mobile, code)

        # For customers, use next_url if provided (return to original page)
        if next_url and cookie_name == "customer_token":
            redirect_url = _safe_next_url(next_url)

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
        })
        response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
        return response


@router.get("/logout")
async def logout(request: Request):
    """Clear auth cookies and redirect to login."""
    response = RedirectResponse("/auth/login", status_code=302)
    response.delete_cookie("auth_token")
    response.delete_cookie("customer_token")
    response.delete_cookie("dealer_token")
    response.delete_cookie("csrf_token")
    return response
