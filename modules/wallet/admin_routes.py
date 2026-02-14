"""
Wallet Admin Routes
=====================
Manage customer wallets, approve withdrawals, manual adjustments.
"""

from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from config.database import get_db
from common.templating import templates
from common.security import csrf_check, new_csrf_token
from modules.auth.deps import require_staff, require_super_admin
from modules.wallet.service import wallet_service
from modules.wallet.models import AssetCode, OwnerType, WithdrawalRequest, WithdrawalStatus
from modules.customer.models import Customer
from modules.dealer.models import Dealer

router = APIRouter(prefix="/admin/wallets", tags=["admin-wallet"])


# ==========================================
# 📋 Customer Accounts List
# ==========================================

@router.get("", response_class=HTMLResponse)
async def admin_wallet_list(
    request: Request,
    page: int = 1,
    owner_type: str = "",
    asset: str = "",
    db: Session = Depends(get_db),
    user=Depends(require_staff),
):
    per_page = 30
    ot = owner_type if owner_type in ("customer", "dealer") else None
    ac = asset if asset in ("IRR", "XAU_MG") else None
    accounts, total = wallet_service.get_all_accounts(db, page=page, per_page=per_page, owner_type=ot, asset_code=ac)
    total_pages = max(1, (total + per_page - 1) // per_page)
    stats = wallet_service.get_stats(db)

    return templates.TemplateResponse("admin/wallet/accounts.html", {
        "request": request,
        "user": user,
        "accounts": accounts,
        "stats": stats,
        "page": page,
        "total_pages": total_pages,
        "total": total,
        "owner_type_filter": owner_type,
        "asset_filter": asset,
        "active_page": "wallets",
    })


# ==========================================
# 👤 Customer Wallet Detail
# ==========================================

@router.get("/customer/{customer_id}", response_class=HTMLResponse)
async def admin_wallet_detail(
    request: Request,
    customer_id: int,
    page: int = 1,
    msg: str = None,
    error: str = None,
    db: Session = Depends(get_db),
    user=Depends(require_staff),
):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(404, "مشتری یافت نشد")

    balance = wallet_service.get_balance(db, customer_id)
    gold_balance = wallet_service.get_balance(db, customer_id, asset_code=AssetCode.XAU_MG)
    per_page = 25
    entries, total = wallet_service.get_transactions(db, customer_id, page=page, per_page=per_page)
    total_pages = max(1, (total + per_page - 1) // per_page)

    csrf = new_csrf_token()
    return templates.TemplateResponse("admin/wallet/detail.html", {
        "request": request,
        "user": user,
        "owner_type": "customer",
        "owner": customer,
        "owner_name": customer.full_name or customer.mobile,
        "owner_id": customer.id,
        "balance": balance,
        "gold_balance": gold_balance,
        "entries": entries,
        "page": page,
        "total_pages": total_pages,
        "total": total,
        "csrf_token": csrf,
        "msg": msg,
        "error": error,
        "active_page": "wallets",
    })


@router.get("/dealer/{dealer_id}", response_class=HTMLResponse)
async def admin_wallet_dealer_detail(
    request: Request,
    dealer_id: int,
    page: int = 1,
    msg: str = None,
    error: str = None,
    db: Session = Depends(get_db),
    user=Depends(require_staff),
):
    dealer = db.query(Dealer).filter(Dealer.id == dealer_id).first()
    if not dealer:
        raise HTTPException(404, "نماینده یافت نشد")

    balance = wallet_service.get_balance(db, dealer_id, owner_type=OwnerType.DEALER)
    gold_balance = wallet_service.get_balance(db, dealer_id, asset_code=AssetCode.XAU_MG, owner_type=OwnerType.DEALER)
    per_page = 25
    entries, total = wallet_service.get_transactions(db, dealer_id, owner_type=OwnerType.DEALER, page=page, per_page=per_page)
    total_pages = max(1, (total + per_page - 1) // per_page)

    csrf = new_csrf_token()
    return templates.TemplateResponse("admin/wallet/detail.html", {
        "request": request,
        "user": user,
        "owner_type": "dealer",
        "owner": dealer,
        "owner_name": dealer.full_name,
        "owner_id": dealer.id,
        "balance": balance,
        "gold_balance": gold_balance,
        "entries": entries,
        "page": page,
        "total_pages": total_pages,
        "total": total,
        "csrf_token": csrf,
        "msg": msg,
        "error": error,
        "active_page": "wallets",
    })


# ==========================================
# ⚙️ Manual Adjustment (Admin only)
# ==========================================

@router.post("/adjust")
async def admin_wallet_adjust(
    request: Request,
    owner_type: str = Form(...),
    owner_id: int = Form(...),
    direction: str = Form(...),
    asset: str = Form("IRR"),
    amount: str = Form(...),
    description: str = Form(""),
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
    user=Depends(require_super_admin),
):
    csrf_check(request, csrf_token)

    ot = OwnerType.DEALER if owner_type == "dealer" else OwnerType.CUSTOMER
    ac = AssetCode.XAU_MG if asset == "XAU_MG" else AssetCode.IRR
    redirect_url = f"/admin/wallets/{owner_type}/{owner_id}"

    try:
        if ac == AssetCode.IRR:
            adj_amount = int(amount) * 10  # toman → rial
        else:
            adj_amount = int(float(amount) * 1000)  # gram → mg

        wallet_service.admin_adjust(
            db, owner_id, adj_amount, direction,
            description=description, admin_id=user.id,
            asset_code=ac, owner_type=ot,
        )
        db.commit()
        label = "واریز" if direction == "deposit" else "برداشت"
        return RedirectResponse(f"{redirect_url}?msg={label}+با+موفقیت+انجام+شد", status_code=302)
    except ValueError as e:
        db.rollback()
        return RedirectResponse(f"{redirect_url}?error={str(e)}", status_code=302)


# ==========================================
# 🏦 Withdrawal Requests
# ==========================================

@router.get("/withdrawals/list", response_class=HTMLResponse)
async def admin_withdrawals_list(
    request: Request,
    page: int = 1,
    db: Session = Depends(get_db),
    user=Depends(require_staff),
):
    per_page = 30
    withdrawals, total = wallet_service.get_all_withdrawals(db, page=page, per_page=per_page)
    total_pages = max(1, (total + per_page - 1) // per_page)
    pending_count = (
        db.query(WithdrawalRequest)
        .filter(WithdrawalRequest.status == WithdrawalStatus.PENDING)
        .count()
    )

    csrf = new_csrf_token()
    return templates.TemplateResponse("admin/wallet/withdrawals.html", {
        "request": request,
        "user": user,
        "withdrawals": withdrawals,
        "pending_count": pending_count,
        "page": page,
        "total_pages": total_pages,
        "total": total,
        "csrf_token": csrf,
        "active_page": "withdrawals",
    })


@router.post("/withdrawals/{wr_id}/approve")
async def admin_withdrawal_approve(
    request: Request,
    wr_id: int,
    admin_note: str = Form(""),
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
    user=Depends(require_super_admin),
):
    csrf_check(request, csrf_token)
    try:
        wallet_service.approve_withdrawal(db, wr_id, admin_note)
        db.commit()
        return RedirectResponse(
            f"/admin/wallets/withdrawals/list?msg=درخواست+#{wr_id}+تأیید+شد",
            status_code=302,
        )
    except ValueError as e:
        db.rollback()
        return RedirectResponse(
            f"/admin/wallets/withdrawals/list?error={str(e)}",
            status_code=302,
        )


@router.post("/withdrawals/{wr_id}/reject")
async def admin_withdrawal_reject(
    request: Request,
    wr_id: int,
    admin_note: str = Form(""),
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
    user=Depends(require_super_admin),
):
    csrf_check(request, csrf_token)
    try:
        wallet_service.reject_withdrawal(db, wr_id, admin_note)
        db.commit()
        return RedirectResponse(
            f"/admin/wallets/withdrawals/list?msg=درخواست+#{wr_id}+رد+شد+و+مبلغ+آزاد+گردید",
            status_code=302,
        )
    except ValueError as e:
        db.rollback()
        return RedirectResponse(
            f"/admin/wallets/withdrawals/list?error={str(e)}",
            status_code=302,
        )
