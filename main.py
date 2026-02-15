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
from modules.admin.models import SystemUser, SystemSetting  # noqa: F401
from modules.customer.models import Customer  # noqa: F401
from modules.customer.address_models import GeoProvince, GeoCity, GeoDistrict, CustomerAddress  # noqa: F401
from modules.catalog.models import (  # noqa: F401
    ProductCategory, ProductCategoryLink, Product, ProductImage, CardDesign, CardDesignImage,
    PackageType, PackageTypeImage, Batch, BatchImage, ProductTierWage,
)
from modules.inventory.models import Bar, BarImage, OwnershipHistory, Location, LocationTransfer, BarTransfer  # noqa: F401
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
from modules.verification.routes import router as verification_router
from modules.dealer.routes import router as dealer_router
from modules.dealer.admin_routes import router as dealer_admin_router
from modules.dealer.api_routes import router as dealer_api_router
from modules.dealer.wallet_routes import router as dealer_wallet_router
from modules.ticket.routes import router as ticket_router
from modules.ticket.admin_routes import router as ticket_admin_router
from modules.ownership.routes import router as ownership_router


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

scheduler = BackgroundScheduler()


@asynccontextmanager
async def lifespan(app):
    scheduler.add_job(_cleanup_expired_orders, 'interval', seconds=60, id='expired_orders')
    scheduler.start()
    scheduler_logger.info("Background scheduler started (expired order cleanup every 60s)")
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
app.include_router(verification_router)
app.include_router(dealer_router)
app.include_router(dealer_admin_router)
app.include_router(dealer_api_router)
app.include_router(dealer_wallet_router)
app.include_router(ticket_router)
app.include_router(ticket_admin_router)
app.include_router(ownership_router)


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
async def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    from modules.auth.deps import get_current_active_user
    from modules.admin.dashboard_service import dashboard_service
    user = get_current_active_user(request, db)
    if not user or not getattr(user, "is_staff", False):
        return RedirectResponse("/auth/login", status_code=302)

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
async def dashboard_stats_api(request: Request, db: Session = Depends(get_db)):
    """JSON API for dashboard stats (for AJAX refresh)."""
    from modules.auth.deps import get_current_active_user
    from modules.admin.dashboard_service import dashboard_service
    user = get_current_active_user(request, db)
    if not user or not getattr(user, "is_staff", False):
        return {"error": "unauthorized"}
    return dashboard_service.get_overview_stats(db)
