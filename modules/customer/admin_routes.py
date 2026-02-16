"""
Customer Admin Routes
=======================
Admin customer management: list, search, detail with transaction history.
"""

from fastapi import APIRouter, Request, Depends, Query, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from config.database import get_db
from common.templating import templates
from modules.auth.deps import require_permission
from modules.customer.admin_service import customer_admin_service
from modules.wallet.service import wallet_service
from modules.wallet.models import AssetCode, OwnerType

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

    return templates.TemplateResponse("admin/customers/list.html", {
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
    })


# ==========================================
# Customer Detail (tabbed)
# ==========================================

@router.get("/{customer_id}", response_class=HTMLResponse)
async def admin_customer_detail(
    request: Request,
    customer_id: int,
    tab: str = Query("overview"),
    page: int = 1,
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

    return templates.TemplateResponse("admin/customers/detail.html", {
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
        "active_page": "customers",
    })
