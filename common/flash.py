"""
Flash Messages
================
Cookie-based flash message system for FastAPI + Jinja2.
Messages survive one redirect, then are automatically cleared.

Usage in routes:
    flash(request, "پیام موفقیت", "success")
    return RedirectResponse("/page", status_code=303)

Usage in templates (auto-available via Jinja2 globals):
    {% for msg in get_flashed_messages() %}
        <div class="alert alert-{{ msg.category }}">{{ msg.text }}</div>
    {% endfor %}
"""

import json
import urllib.parse
from typing import List
from fastapi import Request, Response


FLASH_COOKIE = "_flash"


def flash(request: Request, message: str, category: str = "info"):
    """Queue a flash message to be shown after the next redirect."""
    existing = _get_raw_messages(request)
    existing.append({"text": message, "category": category})
    # Store in request.state so middleware can set the cookie
    request.state._flash_messages = existing


def get_flashed_messages(request: Request) -> List[dict]:
    """Read flash messages from the incoming cookie (consumed on read)."""
    cookie_val = request.cookies.get(FLASH_COOKIE, "")
    if not cookie_val:
        return []
    try:
        decoded = urllib.parse.unquote(cookie_val)
        return json.loads(decoded)
    except (json.JSONDecodeError, ValueError):
        return []


def _get_raw_messages(request: Request) -> list:
    """Get pending flash messages (both from cookie and from this request)."""
    if hasattr(request.state, "_flash_messages"):
        return request.state._flash_messages
    return []


def set_flash_cookie(response: Response, messages: list):
    """Set the flash cookie on a response."""
    if messages:
        encoded = urllib.parse.quote(json.dumps(messages, ensure_ascii=False))
        response.set_cookie(FLASH_COOKIE, encoded, httponly=True, samesite="lax", max_age=60)
    else:
        response.delete_cookie(FLASH_COOKIE)


def clear_flash_cookie(response: Response):
    """Clear the flash cookie (called after messages are displayed)."""
    response.delete_cookie(FLASH_COOKIE)
