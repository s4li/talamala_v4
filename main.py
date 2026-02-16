"""
TalaMala v4 - Application Entry Point
=======================================
FastAPI app initialization, middleware, and router registration.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from apscheduler.schedulers.background import BackgroundScheduler

from config import settings
from config.database import get_db, SessionLocal
from common.templating import templates
from modules.auth.deps import require_permission

scheduler_logger = logging.getLogger("talamala.scheduler")


# ==========================================
# Exception handler: 401 → redirect to login
# ==========================================
from starlette.exceptions import HTTPException as StarletteHTTPException

async def auth_exception_handler(request: Request, exc: StarletteHTTPException):
    """Redirect 401 to login, render custom 404 for browser requests."""
    is_html = "text/html" in request.headers.get("accept", "")
    if exc.status_code == 401 and is_html:
        import urllib.parse
        # For POST requests (form submissions), use Referer as return URL
        if request.method == "POST":
            referer = request.headers.get("referer", "/")
            # Extract path from full referer URL
            from urllib.parse import urlparse
            parsed = urlparse(referer)
            next_url = parsed.path
            if parsed.query:
                next_url += "?" + parsed.query
        else:
            next_url = str(request.url.path)
            if request.url.query:
                next_url += "?" + str(request.url.query)
        return RedirectResponse(f"/auth/login?next={urllib.parse.quote(next_url, safe='')}", status_code=302)
    if exc.status_code == 404 and is_html:
        db = SessionLocal()
        try:
            user, cart_count, gold_price, csrf = _static_page_ctx(request, db)
            return templates.TemplateResponse("shop/404.html", {
                "request": request, "user": user, "cart_count": cart_count,
                "gold_price": gold_price, "csrf_token": csrf,
            }, status_code=404)
        finally:
            db.close()
    # Default behavior for all other HTTP exceptions
    from fastapi.responses import JSONResponse
    return JSONResponse(
        {"detail": exc.detail},
        status_code=exc.status_code,
    )


def _static_page_ctx(request: Request, db: Session):
    """Lightweight context builder (used by exception handler and static page routes)."""
    from modules.auth.deps import get_current_active_user
    from modules.cart.service import cart_service
    from modules.shop.service import shop_service
    from common.security import new_csrf_token

    user = get_current_active_user(request, db)
    cart_count = 0
    if user and not getattr(user, "is_staff", False):
        _, cart_count = cart_service.get_cart_map(db, user.id)
    gold_price = None
    try:
        gold_price = shop_service.get_gold_price(db)
    except Exception:
        pass
    csrf = new_csrf_token()
    return user, cart_count, gold_price, csrf

# ==========================================
# Import ALL models so Alembic/Base can see them
# ==========================================
from modules.admin.models import SystemUser, SystemSetting, RequestLog  # noqa: F401
from modules.customer.models import Customer  # noqa: F401
from modules.customer.address_models import GeoProvince, GeoCity, GeoDistrict, CustomerAddress  # noqa: F401
from modules.catalog.models import (  # noqa: F401
    ProductCategory, ProductCategoryLink, Product, ProductImage, CardDesign, CardDesignImage,
    PackageType, PackageTypeImage, Batch, BatchImage, ProductTierWage,
)
from modules.inventory.models import Bar, BarImage, OwnershipHistory, DealerTransfer, BarTransfer  # noqa: F401
from modules.cart.models import Cart, CartItem  # noqa: F401
from modules.order.models import Order, OrderItem  # noqa: F401
from modules.wallet.models import Account, LedgerEntry, WalletTopup, WithdrawalRequest  # noqa: F401
from modules.coupon.models import Coupon, CouponMobile, CouponUsage, CouponCategory  # noqa: F401
from modules.dealer.models import Dealer, DealerTier, DealerSale, BuybackRequest  # noqa: F401
from modules.ticket.models import Ticket, TicketMessage, TicketAttachment  # noqa: F401

# ==========================================
# Import routers
# ==========================================
from modules.auth.routes import router as auth_router
from modules.catalog.admin_routes import router as catalog_admin_router
from modules.inventory.admin_routes import router as inventory_admin_router
from modules.shop.routes import router as shop_router
from modules.admin.routes import router as admin_settings_router
from modules.cart.routes import router as cart_router
from modules.order.admin_routes import router as order_admin_router
from modules.wallet.routes import router as wallet_router
from modules.wallet.admin_routes import router as wallet_admin_router
from modules.coupon.admin_routes import router as coupon_admin_router
from modules.coupon.routes import router as coupon_api_router
from modules.payment.routes import router as payment_router
from modules.customer.routes import router as customer_router
from modules.customer.admin_routes import router as customer_admin_router
from modules.verification.routes import router as verification_router
from modules.dealer.routes import router as dealer_router
from modules.dealer.admin_routes import router as dealer_admin_router
from modules.dealer.api_routes import router as dealer_api_router
from modules.dealer.wallet_routes import router as dealer_wallet_router
from modules.ticket.routes import router as ticket_router
from modules.ticket.admin_routes import router as ticket_admin_router
from modules.ownership.routes import router as ownership_router
from modules.admin.staff_routes import router as staff_admin_router


# ==========================================
# Background Scheduler: Expired Order Cleanup
# ==========================================
def _cleanup_expired_orders():
    """Background job: release expired reserved orders every 60 seconds."""
    db = SessionLocal()
    try:
        from modules.order.service import order_service
        count = order_service.release_expired_orders(db)
        if count:
            db.commit()
            scheduler_logger.info(f"Released {count} expired orders")
    except Exception as e:
        db.rollback()
        scheduler_logger.error(f"Cleanup error: {e}")
    finally:
        db.close()

def _cleanup_old_request_logs():
    """Background job: delete request logs older than 30 days."""
    db = SessionLocal()
    try:
        from datetime import datetime, timedelta, timezone
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        deleted = db.query(RequestLog).filter(RequestLog.created_at < cutoff).delete()
        if deleted:
            db.commit()
            scheduler_logger.info(f"Deleted {deleted} old request logs (>30 days)")
    except Exception as e:
        db.rollback()
        scheduler_logger.error(f"Log cleanup error: {e}")
    finally:
        db.close()


scheduler = BackgroundScheduler()


@asynccontextmanager
async def lifespan(app):
    scheduler.add_job(_cleanup_expired_orders, 'interval', seconds=60, id='expired_orders')
    scheduler.add_job(_cleanup_old_request_logs, 'interval', hours=6, id='log_cleanup')
    scheduler.start()
    scheduler_logger.info("Background scheduler started (orders: 60s, logs: 6h)")
    yield
    scheduler.shutdown()
    scheduler_logger.info("Background scheduler stopped")


# ==========================================
# Create App
# ==========================================
app = FastAPI(
    title="TalaMala v4",
    description="سیستم مدیریت شمش طلا",
    version="4.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url=None,
    lifespan=lifespan,
)

# ==========================================
# Static Files
# ==========================================
app.mount("/static", StaticFiles(directory="static"), name="static")

# Register 401 handler for HTML redirects
app.add_exception_handler(StarletteHTTPException, auth_exception_handler)


# ==========================================
# Middleware: CSRF Cookie Refresh
# ==========================================
@app.middleware("http")
async def csrf_cookie_refresh(request: Request, call_next):
    """Ensure every GET response has a fresh CSRF cookie to prevent idle expiry (BUG-4 fix)."""
    response = await call_next(request)
    if request.method == "GET" and "text/html" in response.headers.get("content-type", ""):
        existing = request.cookies.get("csrf_token")
        if not existing:
            # Only add if route handler didn't already set csrf_token cookie
            already_set = any(
                b"csrf_token" in value
                for name, value in response.headers.raw
                if name == b"set-cookie"
            )
            if not already_set:
                from common.security import new_csrf_token
                csrf = new_csrf_token()
                response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


# ==========================================
# Middleware: No-Cache for Admin/Dealer pages
# ==========================================
_NO_CACHE_PREFIXES = ("/admin/", "/dealer/")

@app.middleware("http")
async def no_cache_admin(request: Request, call_next):
    """Prevent browser caching on admin/dealer panel pages so stats are always fresh."""
    response = await call_next(request)
    path = request.url.path
    if any(path.startswith(p) for p in _NO_CACHE_PREFIXES):
        ct = response.headers.get("content-type", "")
        if "text/html" in ct or "application/json" in ct:
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
    return response


# ==========================================
# Middleware: Maintenance Mode
# ==========================================
@app.middleware("http")
async def maintenance_check(request: Request, call_next):
    if settings.MAINTENANCE_MODE:
        path = request.url.path
        bypass = request.cookies.get("maintenance_bypass")

        # Allow static files & bypass cookie
        if path.startswith("/static") or bypass == settings.MAINTENANCE_SECRET:
            return await call_next(request)

        return HTMLResponse(
            "<div style='text-align:center;padding:100px;font-family:sans-serif;'>"
            "<h1>🔧 سیستم در حال بروزرسانی</h1>"
            "<p>لطفاً چند دقیقه دیگر مراجعه فرمایید.</p>"
            "</div>",
            status_code=503,
        )
    return await call_next(request)


# ==========================================
# Middleware: Request Audit Log
# ==========================================
import time as _time
import re as _re
from urllib.parse import unquote_plus as _unquote

_SKIP_PATHS = ("/static/", "/health", "/favicon.ico")
_SENSITIVE_KEYS = _re.compile(
    r'(password|otp_code|csrf_token|api_key|secret|token)=[^&]*',
    _re.IGNORECASE,
)


def _identify_user(request: Request):
    """Identify user from JWT cookies without DB query. Returns (user_type, user_display)."""
    from common.security import decode_staff_token, decode_customer_token, decode_dealer_token

    # Staff / Admin
    admin_tok = request.cookies.get("auth_token")
    if admin_tok:
        payload = decode_staff_token(admin_tok)
        if payload:
            return "admin", payload.get("sub", "?")

    # Dealer
    dealer_tok = request.cookies.get("dealer_token")
    if dealer_tok:
        payload = decode_dealer_token(dealer_tok)
        if payload:
            return "dealer", payload.get("sub", "?")

    # Customer
    cust_tok = request.cookies.get("customer_token")
    if cust_tok:
        payload = decode_customer_token(cust_tok)
        if payload:
            return "customer", payload.get("sub", "?")

    return "anonymous", None


def _mask_body(raw: bytes, content_type: str) -> str | None:
    """Parse request body, mask sensitive fields, truncate."""
    if not raw:
        return None

    ct = (content_type or "").lower()

    # Multipart (file uploads) — just note it, don't store binary
    if "multipart/form-data" in ct:
        return "[multipart/form-data — file upload]"

    # URL-encoded form or JSON
    try:
        text = raw[:10_000].decode("utf-8", errors="replace")
    except Exception:
        return None

    # Mask sensitive fields
    text = _SENSITIVE_KEYS.sub(lambda m: m.group(0).split("=")[0] + "=***", text)

    return text[:2000] if text else None


@app.middleware("http")
async def request_logger(request: Request, call_next):
    """Log every HTTP request to the database for audit purposes."""
    path = request.url.path

    # Skip noisy paths
    if any(path.startswith(p) for p in _SKIP_PATHS):
        return await call_next(request)

    start = _time.time()

    # Read body for POST/PUT/PATCH before call_next (caches internally)
    body_preview = None
    if request.method in ("POST", "PUT", "PATCH"):
        try:
            raw = await request.body()
            body_preview = _mask_body(raw, request.headers.get("content-type"))
        except Exception:
            body_preview = "[error reading body]"

    response = await call_next(request)

    elapsed_ms = int((_time.time() - start) * 1000)
    user_type, user_display = _identify_user(request)

    # Write log in a separate session (fire-and-forget, don't block response)
    try:
        log_db = SessionLocal()
        log_entry = RequestLog(
            method=request.method,
            path=path[:500],
            query_string=str(request.url.query)[:2000] if request.url.query else None,
            status_code=response.status_code,
            ip_address=(request.client.host if request.client else None),
            user_agent=(request.headers.get("user-agent") or "")[:500],
            user_type=user_type,
            user_display=user_display,
            body_preview=body_preview,
            response_time_ms=elapsed_ms,
        )
        log_db.add(log_entry)
        log_db.commit()
        log_db.close()
    except Exception:
        pass  # Never let logging break the actual request

    return response


# ==========================================
# Register Routers
# ==========================================
app.include_router(auth_router)
app.include_router(catalog_admin_router)
app.include_router(inventory_admin_router)
app.include_router(admin_settings_router)
app.include_router(order_admin_router)
app.include_router(cart_router)
app.include_router(shop_router)
app.include_router(wallet_router)
app.include_router(wallet_admin_router)
app.include_router(coupon_admin_router)
app.include_router(coupon_api_router)
app.include_router(payment_router)
app.include_router(customer_router)
app.include_router(customer_admin_router)
app.include_router(verification_router)
app.include_router(dealer_router)
app.include_router(dealer_admin_router)
app.include_router(dealer_api_router)
app.include_router(dealer_wallet_router)
app.include_router(ticket_router)
app.include_router(ticket_admin_router)
app.include_router(ownership_router)
app.include_router(staff_admin_router)


# ==========================================
# Health check
# ==========================================
@app.get("/health")
async def health():
    return {"status": "ok", "version": "4.0.0"}


# ==========================================
# Static Pages (About, FAQ, Contact, Terms)
# ==========================================
@app.get("/about", response_class=HTMLResponse)
async def about_page(request: Request, db: Session = Depends(get_db)):
    user, cart_count, gold_price, csrf = _static_page_ctx(request, db)
    response = templates.TemplateResponse("shop/about.html", {
        "request": request, "user": user, "cart_count": cart_count,
        "gold_price": gold_price, "csrf_token": csrf,
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


@app.get("/faq", response_class=HTMLResponse)
async def faq_page(request: Request, db: Session = Depends(get_db)):
    user, cart_count, gold_price, csrf = _static_page_ctx(request, db)
    response = templates.TemplateResponse("shop/faq.html", {
        "request": request, "user": user, "cart_count": cart_count,
        "gold_price": gold_price, "csrf_token": csrf,
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


@app.get("/contact", response_class=HTMLResponse)
async def contact_page(request: Request, db: Session = Depends(get_db)):
    user, cart_count, gold_price, csrf = _static_page_ctx(request, db)
    response = templates.TemplateResponse("shop/contact.html", {
        "request": request, "user": user, "cart_count": cart_count,
        "gold_price": gold_price, "csrf_token": csrf,
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


@app.get("/terms", response_class=HTMLResponse)
async def terms_page(request: Request, db: Session = Depends(get_db)):
    user, cart_count, gold_price, csrf = _static_page_ctx(request, db)
    response = templates.TemplateResponse("shop/terms.html", {
        "request": request, "user": user, "cart_count": cart_count,
        "gold_price": gold_price, "csrf_token": csrf,
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


# ==========================================
# Admin Dashboard (comprehensive stats)
# ==========================================
@app.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_permission("dashboard")),
):
    from modules.admin.dashboard_service import dashboard_service

    stats = dashboard_service.get_overview_stats(db)
    recent_orders = dashboard_service.get_recent_orders(db, limit=8)
    daily_revenue = dashboard_service.get_daily_revenue(db, days=30)
    inventory_status = dashboard_service.get_inventory_by_status(db)

    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request,
        "user": user,
        "stats": stats,
        "recent_orders": recent_orders,
        "daily_revenue": daily_revenue,
        "inventory_status": inventory_status,
        "active_page": "dashboard",
    })


@app.get("/admin/dashboard/api/stats")
async def dashboard_stats_api(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_permission("dashboard")),
):
    """JSON API for dashboard stats (for AJAX refresh)."""
    from modules.admin.dashboard_service import dashboard_service
    return dashboard_service.get_overview_stats(db)
