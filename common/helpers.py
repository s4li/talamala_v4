"""
TalaMala v4 - Shared Helpers
=============================
Pure utility functions with NO database or module dependencies.
"""

import secrets
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional


def now_utc() -> datetime:
    """Returns current UTC datetime (timezone-aware)."""
    return datetime.now(timezone.utc)


def safe_int(value: Optional[str]) -> Optional[int]:
    """Safely convert a string to int. Returns None on failure."""
    if value is None:
        return None
    try:
        return int(str(value).strip())
    except (ValueError, TypeError):
        return None


def format_toman(value) -> str:
    """Format Rial value as Toman with comma separators. (Rial ÷ 10 = Toman)"""
    if value is None:
        return "0"
    try:
        v = int(value) // 10
        return "{:,}".format(v)
    except (ValueError, TypeError):
        return str(value)


def format_weight(value) -> str:
    """Format weight, removing unnecessary trailing zeros."""
    if value is None:
        return ""
    try:
        d = Decimal(str(value))
        normalized = d.normalize()
        if normalized.as_tuple().exponent > 0:
            return str(int(d))
        return "{:f}".format(normalized)
    except Exception:
        return str(value)


def get_real_ip(request) -> str:
    """Extract real client IP from request (handles X-Forwarded-For proxy header)."""
    x_forwarded = request.headers.get("X-Forwarded-For")
    if x_forwarded:
        return x_forwarded.split(",")[0].strip()
    return request.client.host


# ==========================================
# Jalali Date & Persian Number Filters
# ==========================================

_PERSIAN_DIGITS = str.maketrans("0123456789", "\u06f0\u06f1\u06f2\u06f3\u06f4\u06f5\u06f6\u06f7\u06f8\u06f9")


def persian_number(value) -> str:
    """Convert English digits to Persian digits."""
    return str(value).translate(_PERSIAN_DIGITS)


def format_gold_gram(mg) -> str:
    """Convert milligrams (int) to formatted Persian gram string with 3 decimals."""
    if mg is None:
        mg = 0
    try:
        gram = int(mg) / 1000
        formatted = f"{gram:,.3f}"
        return persian_number(formatted) + " گرم"
    except (ValueError, TypeError):
        return "۰ گرم"


# ==========================================
# Claim Code Generator
# ==========================================

_CLAIM_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"  # no O/0/I/1/L


def generate_claim_code(length: int = 6) -> str:
    """Generate a short, human-readable claim code."""
    return "".join(secrets.choice(_CLAIM_ALPHABET) for _ in range(length))


def generate_unique_claim_code(db, length: int = 6, max_retries: int = 10) -> str:
    """Generate a unique claim code (checks DB for collision)."""
    from modules.inventory.models import Bar
    for _ in range(max_retries):
        code = generate_claim_code(length)
        exists = db.query(Bar.id).filter(Bar.claim_code == code).first()
        if not exists:
            return code
    raise RuntimeError("Failed to generate unique claim code after retries")


def format_jdate(value, fmt=None) -> str:
    """Convert a datetime to Jalali (Shamsi) date string.

    Default format: '۲۵ بهمن ۱۴۰۴  ۱۴:۳۰'
    """
    if value is None:
        return ""
    try:
        import jdatetime
        if isinstance(value, datetime):
            jd = jdatetime.datetime.fromgregorian(datetime=value)
            if fmt:
                return persian_number(jd.strftime(fmt))
            day = persian_number(str(jd.day))
            months = [
                '', 'فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور',
                'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند',
            ]
            month = months[jd.month]
            year = persian_number(str(jd.year))
            time_str = persian_number(jd.strftime("%H:%M"))
            return f"{day} {month} {year}  {time_str}"
        return str(value)
    except Exception:
        return str(value)
