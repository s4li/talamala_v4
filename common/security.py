"""
TalaMala v4 - Security Utilities
==================================
JWT tokens, CSRF protection, OTP hashing, and rate limiting.

NOTE: Unified auth — single JWT token for all user types (customer/dealer/admin).
"""

import hmac
import hashlib
import logging
import secrets
from datetime import timedelta
from typing import Optional
from collections import defaultdict

from fastapi import Request, HTTPException
from jose import jwt

from config.settings import (
    SECRET_KEY, OTP_SECRET, ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES, CSRF_ENABLED,
    OTP_MAX_ATTEMPTS, OTP_RATE_LIMIT_WINDOW,
)
from common.helpers import now_utc

logger = logging.getLogger("talamala.security")


# ==========================================
# In-memory rate limiter storage
# ==========================================
_otp_attempts: dict[str, list] = defaultdict(list)
_otp_verify_attempts: dict[str, list] = defaultdict(list)

OTP_VERIFY_MAX_ATTEMPTS = 5   # max verify tries per mobile
OTP_VERIFY_WINDOW = 10        # minutes


# ==========================================
# OTP
# ==========================================

def hash_otp(mobile: str, otp: str) -> str:
    """Create HMAC-SHA256 hash of OTP combined with mobile and secret."""
    msg = f"{mobile}:{otp}".encode("utf-8")
    return hmac.new(OTP_SECRET.encode("utf-8"), msg, hashlib.sha256).hexdigest()


def generate_otp(length: int = 6) -> str:
    """Generate a random numeric OTP code. In DEBUG mode returns fixed code for local dev."""
    from config.settings import DEBUG
    if DEBUG:
        logger.warning("DEBUG OTP: %s (set DEBUG=false for production)", "1" * length)
        return "1" * length
    lower = 10 ** (length - 1)
    upper = 10 ** length - 1
    return str(secrets.randbelow(upper - lower) + lower)


def check_otp_rate_limit(mobile: str) -> bool:
    """
    Check if mobile number has exceeded OTP request limit.
    Returns True if allowed, False if rate limited.
    """
    now = now_utc()
    cutoff = now - timedelta(minutes=OTP_RATE_LIMIT_WINDOW)

    # Clean old entries
    _otp_attempts[mobile] = [t for t in _otp_attempts[mobile] if t > cutoff]

    if len(_otp_attempts[mobile]) >= OTP_MAX_ATTEMPTS:
        return False

    _otp_attempts[mobile].append(now)
    return True


def check_otp_verify_rate_limit(mobile: str) -> bool:
    """
    Check if mobile number has exceeded OTP verification attempts.
    Returns True if allowed, False if rate limited.
    """
    now = now_utc()
    cutoff = now - timedelta(minutes=OTP_VERIFY_WINDOW)

    _otp_verify_attempts[mobile] = [t for t in _otp_verify_attempts[mobile] if t > cutoff]

    if len(_otp_verify_attempts[mobile]) >= OTP_VERIFY_MAX_ATTEMPTS:
        return False

    _otp_verify_attempts[mobile].append(now)
    return True


# ==========================================
# JWT Tokens (Unified — single secret for all user types)
# ==========================================

def create_token(data: dict) -> str:
    """Create JWT token for any user type."""
    to_encode = data.copy()
    to_encode["exp"] = now_utc() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    """Decode a JWT token. Returns payload or None."""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except Exception:
        return None


# Backward compat aliases
create_staff_token = create_token
create_customer_token = create_token
create_dealer_token = create_token
decode_staff_token = decode_token
decode_customer_token = decode_token
decode_dealer_token = decode_token


# ==========================================
# Cookie Helpers
# ==========================================

def get_cookie_kwargs() -> dict:
    """Standard cookie settings for auth tokens."""
    from config.settings import COOKIE_SECURE, COOKIE_SAMESITE
    return dict(
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


# ==========================================
# CSRF
# ==========================================

def new_csrf_token() -> str:
    """Generate a new random CSRF token."""
    return secrets.token_urlsafe(32)


def csrf_check(request: Request, form_token: Optional[str] = None):
    """
    Verify CSRF token from cookie matches the one in header or form.
    Raises HTTPException(403) on mismatch.
    """
    if not CSRF_ENABLED:
        return

    cookie_token = request.cookies.get("csrf_token")
    header_token = request.headers.get("X-CSRF-Token")
    token = header_token or form_token

    if not cookie_token or not token or cookie_token != token:
        raise HTTPException(403, "CSRF token missing or invalid")
