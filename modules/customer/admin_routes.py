"""
Customer Admin Routes
=======================
Admin customer management: list, search, detail with transaction history.
"""

import urllib.parse
from fastapi import APIRouter, Request, Depends, Query, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from config.database import get_db
from common.templating import templates
from common.security import csrf_check, new_csrf_token
from modules.auth.deps import require_permission
from modules.customer.admin_service import customer_admin_service
from modules.wallet.service import wallet_service
from modules.wallet.models import AssetCode

router = APIRouter(prefix="/admin/customers", tags=["admin-customer"])


# ==========================================
# Customer List
# ==========================================

@router.get("", response_class=HTMLResponse)
async def admin_customer_list(
    request: Request,
    page: int = 1,
    search: str = Query(None),
    status: str = Query(None),
    db: Session = Depends(get_db),
    user=Depends(require_permission("customers")),
):
    per_page = 30
    customers, total = customer_admin_service.list_customers(
        db, page=page, per_page=per_page, search=search, status=status,
    )
    total_pages = max(1, (total + per_page - 1) // per_page)
    stats = customer_admin_service.get_customer_stats(db)

    csrf = new_csrf_token()
    response = templates.TemplateResponse("admin/customers/list.html", {
        "request": request,
        "user": user,
        "customers": customers,
        "total": total,
        "page": page,
        "total_pages": total_pages,
        "stats": stats,
        "search_query": search or "",
        "status_filter": status or "",
        "active_page": "customers",
        "csrf_token": csrf,
        "error": request.query_params.get("error", ""),
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


# ==========================================
# Create Customer
# ==========================================

@router.get("/create")
async def admin_customer_create_redirect():
    return RedirectResponse("/admin/customers", status_code=302)


@router.post("/create")
async def admin_customer_create(
    request: Request,
    mobile: str = Form(""),
    first_name: str = Form(""),
    last_name: str = Form(""),
    national_id: str = Form(""),
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
    user=Depends(require_permission("customers")),
):
    csrf_check(request, csrf_token)

    result = customer_admin_service.create_customer(
        db,
        mobile=mobile,
        first_name=first_name,
        last_name=last_name,
        national_id=national_id,
    )

    if not result["success"]:
        error = urllib.parse.quote(result["error"])
        return RedirectResponse(f"/admin/customers?error={error}", status_code=303)

    db.commit()
    msg = urllib.parse.quote("کاربر جدید با موفقیت ایجاد شد.")
    return RedirectResponse(
        f"/admin/customers/{result['customer'].id}?msg={msg}", status_code=303,
    )


# ==========================================
# Customer Detail (tabbed)
# ==========================================

@router.get("/{customer_id}", response_class=HTMLResponse)
async def admin_customer_detail(
    request: Request,
    customer_id: int,
    tab: str = Query("overview"),
    page: int = 1,
    msg: str = Query(None),
    error: str = Query(None),
    db: Session = Depends(get_db),
    user=Depends(require_permission("customers")),
):
    customer = customer_admin_service.get_customer_detail(db, customer_id)
    if not customer:
        raise HTTPException(404, "مشتری یافت نشد")

    summary = customer_admin_service.get_customer_summary(db, customer_id)

    per_page = 20

    # Always load balances for header cards
    balance = wallet_service.get_balance(db, customer_id)
    gold_balance = wallet_service.get_balance(
        db, customer_id, asset_code=AssetCode.XAU_MG
    )

    # Tab-specific data
    wallet_entries, wallet_total, wallet_pages = [], 0, 1
    withdrawals, wd_total, wd_pages = [], 0, 1
    orders, order_total, order_pages = [], 0, 1

    if tab == "wallet":
        wallet_entries, wallet_total = wallet_service.get_transactions(
            db, customer_id, page=page, per_page=per_page
        )
        wallet_pages = max(1, (wallet_total + per_page - 1) // per_page)

    elif tab == "withdrawals":
        withdrawals, wd_total = customer_admin_service.get_customer_withdrawals(
            db, customer_id, page=page, per_page=per_page
        )
        wd_pages = max(1, (wd_total + per_page - 1) // per_page)

    elif tab == "orders":
        orders, order_total = customer_admin_service.get_customer_orders(
            db, customer_id, page=page, per_page=per_page
        )
        order_pages = max(1, (order_total + per_page - 1) // per_page)

    csrf = new_csrf_token()
    response = templates.TemplateResponse("admin/customers/detail.html", {
        "request": request,
        "user": user,
        "customer": customer,
        "summary": summary,
        "tab": tab,
        "balance": balance,
        "gold_balance": gold_balance,
        "wallet_entries": wallet_entries,
        "wallet_total": wallet_total,
        "wallet_pages": wallet_pages,
        "withdrawals": withdrawals,
        "wd_total": wd_total,
        "wd_pages": wd_pages,
        "orders": orders,
        "order_total": order_total,
        "order_pages": order_pages,
        "page": page,
        "csrf_token": csrf,
        "msg": msg,
        "error": error,
        "active_page": "customers",
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


# ==========================================
# Customer Update (admin edit)
# ==========================================

@router.post("/{customer_id}")
async def admin_customer_update(
    request: Request,
    customer_id: int,
    first_name: str = Form(""),
    last_name: str = Form(""),
    national_id: str = Form(""),
    mobile: str = Form(""),
    customer_type: str = Form("real"),
    company_name: str = Form(""),
    economic_code: str = Form(""),
    postal_code: str = Form(""),
    address: str = Form(""),
    phone: str = Form(""),
    birth_date: str = Form(""),
    is_active: str = Form("off"),
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
    user=Depends(require_permission("customers")),
):
    csrf_check(request, csrf_token)

    result = customer_admin_service.update_customer(
        db, customer_id,
        first_name=first_name.strip(),
        last_name=last_name.strip(),
        national_id=national_id.strip(),
        mobile=mobile.strip(),
        birth_date=birth_date.strip(),
        customer_type=customer_type,
        company_name=company_name.strip(),
        economic_code=economic_code.strip(),
        postal_code=postal_code.strip(),
        address=address.strip(),
        phone=phone.strip(),
        is_active=(is_active == "on"),
    )

    if not result["success"]:
        error = urllib.parse.quote(result["error"])
        return RedirectResponse(
            f"/admin/customers/{customer_id}?tab=overview&error={error}",
            status_code=303,
        )

    db.commit()
    msg = urllib.parse.quote("اطلاعات مشتری با موفقیت بروزرسانی شد.")
    return RedirectResponse(
        f"/admin/customers/{customer_id}?tab=overview&msg={msg}",
        status_code=303,
    )
