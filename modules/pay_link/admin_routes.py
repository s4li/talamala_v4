"""
Pay Link — admin routes
  GET  /admin/payment-links          — list all links
  GET  /admin/payment-links/new      — create form
  POST /admin/payment-links/new      — save new link
  GET  /admin/payment-links/{id}     — detail
  POST /admin/payment-links/{id}/cancel — cancel link
"""

import urllib.parse
from fastapi import APIRouter, Request, Depends, Form, Query
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session

from config.database import get_db
from common.security import csrf_check, new_csrf_token
from common.templating import templates
from common.helpers import now_utc
from modules.auth.deps import require_permission
from modules.pay_link.service import pay_link_service
from modules.payment.gateways import get_all_gateway_names

router = APIRouter(prefix="/admin/payment-links", tags=["admin_pay_links"])

GATEWAYS = ["sepehr", "zibal", "top", "parsian"]
GATEWAY_LABELS = {"sepehr": "سپهر", "zibal": "زیبال", "top": "تاپ", "parsian": "پارسیان"}


# ── List ──────────────────────────────────────────────────────────────────────

@router.get("")
async def list_links(
    request: Request,
    page: int = Query(1, ge=1),
    status: str = Query(""),
    search: str = Query(""),
    db: Session = Depends(get_db),
    user=Depends(require_permission("pay_links")),
):
    links, total = pay_link_service.list_links(
        db, page=page, per_page=20,
        status=status or None,
        search=search or None,
    )
    stats = pay_link_service.stats(db)
    total_pages = max(1, (total + 19) // 20)

    csrf = new_csrf_token()
    resp = templates.TemplateResponse("admin/pay_links/list.html", {
        "request": request,
        "user": user,
        "active_page": "pay_links",
        "links": links,
        "total": total,
        "page": page,
        "total_pages": total_pages,
        "status_filter": status,
        "search": search,
        "stats": stats,
        "csrf_token": csrf,
    })
    resp.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return resp


# ── Create ────────────────────────────────────────────────────────────────────

@router.get("/new")
async def new_link_form(
    request: Request,
    user_id: int = Query(0),
    db: Session = Depends(get_db),
    user=Depends(require_permission("pay_links", level="create")),
):
    prefill_user = None
    if user_id:
        from modules.user.models import User
        prefill_user = db.query(User).filter(User.id == user_id).first()

    csrf = new_csrf_token()
    resp = templates.TemplateResponse("admin/pay_links/new.html", {
        "request": request,
        "user": user,
        "active_page": "pay_links",
        "gateways": GATEWAYS,
        "gateway_labels": GATEWAY_LABELS,
        "prefill_user": prefill_user,
        "csrf_token": csrf,
    })
    resp.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return resp


@router.post("/new")
async def create_link(
    request: Request,
    csrf_token: str = Form(""),
    user_mobile: str = Form(""),
    amount_toman: str = Form(""),
    description: str = Form(""),
    gateway: str = Form("sepehr"),
    expires_days: str = Form(""),
    notes: str = Form(""),
    db: Session = Depends(get_db),
    user=Depends(require_permission("pay_links", level="create")),
):
    csrf_check(request, csrf_token)

    # Resolve user by mobile
    from modules.user.models import User
    target_user = db.query(User).filter(User.mobile == user_mobile.strip()).first()
    if not target_user:
        error = urllib.parse.quote("کاربر با این موبایل یافت نشد")
        return RedirectResponse(f"/admin/payment-links/new?error={error}", status_code=303)

    # Validate amount
    if not amount_toman.strip().isdigit():
        error = urllib.parse.quote("مبلغ نامعتبر")
        return RedirectResponse(f"/admin/payment-links/new?error={error}", status_code=303)
    amount_irr = int(amount_toman.strip()) * 10

    if amount_irr <= 0:
        error = urllib.parse.quote("مبلغ باید بزرگ‌تر از صفر باشد")
        return RedirectResponse(f"/admin/payment-links/new?error={error}", status_code=303)

    if not description.strip():
        error = urllib.parse.quote("توضیحات الزامی است")
        return RedirectResponse(f"/admin/payment-links/new?error={error}", status_code=303)

    if gateway not in GATEWAYS:
        error = urllib.parse.quote("درگاه نامعتبر")
        return RedirectResponse(f"/admin/payment-links/new?error={error}", status_code=303)

    # Optional expiry
    expires_at = None
    if expires_days.strip().isdigit() and int(expires_days) > 0:
        from datetime import timedelta
        expires_at = now_utc() + timedelta(days=int(expires_days))

    link = pay_link_service.create(
        db,
        user_id=target_user.id,
        amount_irr=amount_irr,
        description=description.strip(),
        gateway=gateway,
        created_by=user.id,
        expires_at=expires_at,
        notes=notes.strip() or None,
    )
    db.commit()

    msg = urllib.parse.quote("لینک پرداخت با موفقیت ایجاد شد")
    return RedirectResponse(f"/admin/payment-links/{link.id}?msg={msg}", status_code=303)


# ── User lookup (AJAX) ───────────────────────────────────────────────────────

@router.get("/api/user-lookup", include_in_schema=False)
async def user_lookup(
    mobile: str = Query(""),
    db: Session = Depends(get_db),
    user=Depends(require_permission("pay_links")),
):
    from modules.user.models import User
    u = db.query(User).filter(User.mobile == mobile.strip()).first()
    if u:
        return JSONResponse({"found": True, "name": u.display_name, "mobile": u.mobile, "id": u.id})
    return JSONResponse({"found": False})


# ── Detail ────────────────────────────────────────────────────────────────────

@router.get("/{link_id}")
async def detail(
    request: Request,
    link_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_permission("pay_links")),
):
    link = pay_link_service.get_by_id(db, link_id)
    if not link:
        return RedirectResponse("/admin/payment-links?error=لینک+یافت+نشد", status_code=303)

    from config.settings import BASE_URL
    pay_url = f"{BASE_URL}/pay/{link.token}"

    csrf = new_csrf_token()
    resp = templates.TemplateResponse("admin/pay_links/detail.html", {
        "request": request,
        "user": user,
        "active_page": "pay_links",
        "link": link,
        "pay_url": pay_url,
        "csrf_token": csrf,
    })
    resp.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return resp


# ── Cancel ────────────────────────────────────────────────────────────────────

@router.post("/{link_id}/cancel")
async def cancel_link(
    request: Request,
    link_id: int,
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
    user=Depends(require_permission("pay_links", level="edit")),
):
    csrf_check(request, csrf_token)

    link = pay_link_service.get_by_id(db, link_id)
    if not link:
        return RedirectResponse("/admin/payment-links?error=لینک+یافت+نشد", status_code=303)

    if link.is_paid:
        error = urllib.parse.quote("لینک پرداخت شده قابل لغو نیست")
        return RedirectResponse(f"/admin/payment-links/{link_id}?error={error}", status_code=303)

    pay_link_service.cancel(db, link)
    db.commit()

    msg = urllib.parse.quote("لینک پرداخت لغو شد")
    return RedirectResponse(f"/admin/payment-links/{link_id}?msg={msg}", status_code=303)
