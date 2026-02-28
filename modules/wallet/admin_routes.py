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
from modules.auth.deps import require_permission
from modules.wallet.service import wallet_service
from modules.wallet.models import AssetCode, WithdrawalRequest, WithdrawalStatus
from modules.user.models import User

router = APIRouter(prefix="/admin/wallets", tags=["admin-wallet"])


# ==========================================
# 📋 Customer Accounts List
# ==========================================

@router.get("", response_class=HTMLResponse)
async def admin_wallet_list(
    request: Request,
    page: int = 1,
    asset: str = "",
    db: Session = Depends(get_db),
    user=Depends(require_permission("wallets")),
):
    per_page = 30
    ac = asset if asset in ("IRR", "XAU_MG", "XAG_MG") else None
    accounts, total = wallet_service.get_all_accounts(db, page=page, per_page=per_page, asset_code=ac)
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
        "asset_filter": asset,
        "active_page": "wallets",
    })


# ==========================================
# User Wallet Detail (customer or dealer)
# ==========================================

@router.get("/customer/{user_id}", response_class=HTMLResponse)
async def admin_wallet_detail(
    request: Request,
    user_id: int,
    page: int = 1,
    msg: str = None,
    error: str = None,
    db: Session = Depends(get_db),
    user=Depends(require_permission("wallets")),
):
    owner = db.query(User).filter(User.id == user_id).first()
    if not owner:
        raise HTTPException(404, "کاربر یافت نشد")

    balance = wallet_service.get_balance(db, user_id)
    gold_balance = wallet_service.get_balance(db, user_id, asset_code=AssetCode.XAU_MG)
    silver_balance = wallet_service.get_balance(db, user_id, asset_code=AssetCode.XAG_MG)
    per_page = 25
    entries, total = wallet_service.get_transactions(db, user_id, page=page, per_page=per_page)
    total_pages = max(1, (total + per_page - 1) // per_page)

    csrf = new_csrf_token()
    response = templates.TemplateResponse("admin/wallet/detail.html", {
        "request": request,
        "user": user,
        "owner": owner,
        "owner_name": owner.full_name or owner.mobile,
        "owner_id": owner.id,
        "balance": balance,
        "gold_balance": gold_balance,
        "silver_balance": silver_balance,
        "entries": entries,
        "page": page,
        "total_pages": total_pages,
        "total": total,
        "csrf_token": csrf,
        "msg": msg,
        "error": error,
        "active_page": "wallets",
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


@router.get("/dealer/{user_id}", response_class=HTMLResponse)
async def admin_wallet_dealer_detail(
    request: Request,
    user_id: int,
    page: int = 1,
    msg: str = None,
    error: str = None,
    db: Session = Depends(get_db),
    user=Depends(require_permission("wallets")),
):
    owner = db.query(User).filter(User.id == user_id, User.is_dealer == True).first()
    if not owner:
        raise HTTPException(404, "نماینده یافت نشد")

    balance = wallet_service.get_balance(db, user_id)
    gold_balance = wallet_service.get_balance(db, user_id, asset_code=AssetCode.XAU_MG)
    silver_balance = wallet_service.get_balance(db, user_id, asset_code=AssetCode.XAG_MG)
    per_page = 25
    entries, total = wallet_service.get_transactions(db, user_id, page=page, per_page=per_page)
    total_pages = max(1, (total + per_page - 1) // per_page)

    csrf = new_csrf_token()
    response = templates.TemplateResponse("admin/wallet/detail.html", {
        "request": request,
        "user": user,
        "owner": owner,
        "owner_name": owner.full_name,
        "owner_id": owner.id,
        "balance": balance,
        "gold_balance": gold_balance,
        "silver_balance": silver_balance,
        "entries": entries,
        "page": page,
        "total_pages": total_pages,
        "total": total,
        "csrf_token": csrf,
        "msg": msg,
        "error": error,
        "active_page": "wallets",
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


# ==========================================
# ⚙️ Manual Adjustment (Admin only)
# ==========================================

@router.post("/adjust")
async def admin_wallet_adjust(
    request: Request,
    user_id: int = Form(...),
    direction: str = Form(...),
    asset: str = Form("IRR"),
    amount: str = Form(...),
    description: str = Form(""),
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
    user=Depends(require_permission("wallets", level="full")),
):
    csrf_check(request, csrf_token)

    if asset == "XAU_MG":
        ac = AssetCode.XAU_MG
    elif asset == "XAG_MG":
        ac = AssetCode.XAG_MG
    else:
        ac = AssetCode.IRR
    redirect_url = f"/admin/wallets/customer/{user_id}"

    try:
        if ac == AssetCode.IRR:
            adj_amount = int(amount) * 10  # toman → rial
        else:
            adj_amount = int(float(amount) * 1000)  # gram → mg

        wallet_service.admin_adjust(
            db, user_id, adj_amount, direction,
            description=description, admin_id=user.id,
            asset_code=ac,
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
    user=Depends(require_permission("wallets")),
):
    from sqlalchemy.orm import joinedload

    per_page = 30

    # Dealer user IDs
    dealer_ids_q = db.query(User.id).filter(User.is_dealer == True)

    # --- Customer withdrawals ---
    cust_q = (
        db.query(WithdrawalRequest)
        .filter(~WithdrawalRequest.user_id.in_(dealer_ids_q))
        .options(joinedload(WithdrawalRequest.user))
    )
    customer_total = cust_q.count()
    customer_withdrawals = (
        cust_q.order_by(WithdrawalRequest.created_at.desc())
        .offset((page - 1) * per_page).limit(per_page).all()
    )
    customer_pages = max(1, (customer_total + per_page - 1) // per_page)

    # --- Dealer withdrawals ---
    dealer_q = (
        db.query(WithdrawalRequest)
        .filter(WithdrawalRequest.user_id.in_(dealer_ids_q))
        .options(joinedload(WithdrawalRequest.user))
    )
    dealer_total = dealer_q.count()
    dealer_withdrawals = (
        dealer_q.order_by(WithdrawalRequest.created_at.desc())
        .offset((page - 1) * per_page).limit(per_page).all()
    )
    dealer_pages = max(1, (dealer_total + per_page - 1) // per_page)

    # Pending counts
    customer_pending = (
        db.query(WithdrawalRequest)
        .filter(WithdrawalRequest.status == WithdrawalStatus.PENDING)
        .filter(~WithdrawalRequest.user_id.in_(dealer_ids_q))
        .count()
    )
    dealer_pending = (
        db.query(WithdrawalRequest)
        .filter(WithdrawalRequest.status == WithdrawalStatus.PENDING)
        .filter(WithdrawalRequest.user_id.in_(dealer_ids_q))
        .count()
    )

    csrf = new_csrf_token()
    response = templates.TemplateResponse("admin/wallet/withdrawals.html", {
        "request": request,
        "user": user,
        "customer_withdrawals": customer_withdrawals,
        "dealer_withdrawals": dealer_withdrawals,
        "customer_pending": customer_pending,
        "dealer_pending": dealer_pending,
        "pending_count": customer_pending + dealer_pending,
        "page": page,
        "customer_pages": customer_pages,
        "dealer_pages": dealer_pages,
        "total_pages": max(customer_pages, dealer_pages),
        "total": customer_total + dealer_total,
        "csrf_token": csrf,
        "active_page": "withdrawals",
    })
    response.set_cookie("csrf_token", csrf, httponly=True, samesite="lax")
    return response


@router.post("/withdrawals/{wr_id}/approve")
async def admin_withdrawal_approve(
    request: Request,
    wr_id: int,
    admin_note: str = Form(""),
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
    user=Depends(require_permission("wallets", level="full")),
):
    csrf_check(request, csrf_token)
    try:
        wr = wallet_service.approve_withdrawal(db, wr_id, admin_note)
        try:
            from modules.notification.service import notification_service
            from modules.notification.models import NotificationType
            notification_service.send(
                db, wr.user_id,
                notification_type=NotificationType.WALLET_WITHDRAW,
                title=f"درخواست برداشت #{wr_id} تأیید شد",
                body=f"درخواست برداشت شما به مبلغ {wr.amount_irr // 10:,} تومان تأیید و به حساب بانکی واریز شد.",
                link="/wallet/withdraw",
                sms_text=f"طلاملا: درخواست برداشت #{wr_id} تأیید شد. مبلغ {wr.amount_irr // 10:,} تومان به حساب بانکی واریز می‌شود.",
                reference_type="withdrawal_approved", reference_id=str(wr_id),
            )
        except Exception:
            pass
        db.commit()
        return RedirectResponse(
            f"/admin/wallets/withdrawals/list?msg=درخواست+%23{wr_id}+تأیید+شد",
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
    user=Depends(require_permission("wallets", level="full")),
):
    csrf_check(request, csrf_token)
    try:
        wr = wallet_service.reject_withdrawal(db, wr_id, admin_note)
        try:
            from modules.notification.service import notification_service
            from modules.notification.models import NotificationType
            notification_service.send(
                db, wr.user_id,
                notification_type=NotificationType.WALLET_WITHDRAW,
                title=f"درخواست برداشت #{wr_id} رد شد",
                body=f"درخواست برداشت شما به مبلغ {wr.amount_irr // 10:,} تومان رد شد و مبلغ بلوکه‌شده آزاد گردید.",
                link="/wallet/withdraw",
                sms_text=f"طلاملا: درخواست برداشت #{wr_id} رد شد. مبلغ {wr.amount_irr // 10:,} تومان آزاد شد.",
                reference_type="withdrawal_rejected", reference_id=str(wr_id),
            )
        except Exception:
            pass
        db.commit()
        return RedirectResponse(
            f"/admin/wallets/withdrawals/list?msg=درخواست+%23{wr_id}+رد+شد+و+مبلغ+آزاد+گردید",
            status_code=302,
        )
    except ValueError as e:
        db.rollback()
        return RedirectResponse(
            f"/admin/wallets/withdrawals/list?error={str(e)}",
            status_code=302,
        )
