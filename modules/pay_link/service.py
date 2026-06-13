"""
PaymentLink Service
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
from sqlalchemy.orm import Session

from modules.pay_link.models import PaymentLink
from modules.payment.gateways import get_gateway, GatewayPaymentRequest
from common.helpers import now_utc
from config.settings import BASE_URL

logger = logging.getLogger("talamala.pay_link")


class PaymentLinkService:

    def create(
        self,
        db: Session,
        user_id: int,
        amount_irr: int,
        description: str,
        gateway: str,
        created_by: int,
        expires_at=None,
        notes: str = None,
    ) -> PaymentLink:
        link = PaymentLink(
            user_id=user_id,
            amount_irr=amount_irr,
            description=description,
            gateway=gateway,
            created_by=created_by,
            expires_at=expires_at,
            notes=notes,
        )
        db.add(link)
        db.flush()
        return link

    def get_by_token(self, db: Session, token: str) -> Optional[PaymentLink]:
        return db.query(PaymentLink).filter(PaymentLink.token == token).first()

    def get_by_id(self, db: Session, link_id: int) -> Optional[PaymentLink]:
        return db.query(PaymentLink).filter(PaymentLink.id == link_id).first()

    def initiate(self, db: Session, link: PaymentLink) -> Dict[str, Any]:
        """Start a gateway payment for this link. Returns redirect_url on success."""
        if not link.is_active:
            return {"success": False, "error": "این لینک پرداخت فعال نیست"}

        gw = get_gateway(link.gateway)
        if not gw:
            return {"success": False, "error": f"درگاه {link.gateway} در دسترس نیست"}

        callback_url = f"{BASE_URL}/pay/callback/{link.gateway}?token={link.token}"
        result = gw.create_payment(GatewayPaymentRequest(
            amount_irr=link.amount_irr,
            callback_url=callback_url,
            description=link.description,
            order_ref=link.token,
        ))

        if result.success:
            link.track_id = result.track_id
            db.flush()
            return {"success": True, "redirect_url": result.redirect_url}
        else:
            return {"success": False, "error": result.error_message}

    def verify(
        self, db: Session, gateway_name: str, params: Dict[str, Any], token: str
    ) -> Dict[str, Any]:
        """Verify gateway callback and mark link as paid."""
        link = self.get_by_token(db, token)
        if not link:
            return {"success": False, "error": "لینک پرداخت یافت نشد"}

        if link.is_paid:
            return {"success": True, "already_paid": True, "link": link}

        if not link.is_active:
            return {"success": False, "error": "لینک پرداخت فعال نیست"}

        gw = get_gateway(gateway_name)
        if not gw:
            return {"success": False, "error": f"درگاه نامعتبر: {gateway_name}"}

        if gateway_name == "sepehr":
            params["expected_amount"] = link.amount_irr

        result = gw.verify_payment(params)

        if result.success:
            link.status = "paid"
            link.paid_at = now_utc()
            link.ref_number = result.ref_number
            db.flush()
            logger.info(f"PaymentLink #{link.id} paid: ref={result.ref_number}")
            return {"success": True, "link": link}
        else:
            logger.warning(f"PaymentLink #{link.id} verify failed: {result.error_message}")
            return {"success": False, "error": result.error_message}

    def cancel(self, db: Session, link: PaymentLink) -> None:
        link.status = "cancelled"
        db.flush()

    def list_links(
        self,
        db: Session,
        page: int = 1,
        per_page: int = 20,
        status: str = None,
        search: str = None,
    ) -> Tuple[List[PaymentLink], int]:
        from modules.user.models import User
        q = db.query(PaymentLink).join(User, PaymentLink.user_id == User.id)
        if status:
            q = q.filter(PaymentLink.status == status)
        if search:
            q = q.filter(
                User.mobile.contains(search)
                | User.first_name.contains(search)
                | User.last_name.contains(search)
            )
        total = q.count()
        items = (
            q.order_by(PaymentLink.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        return items, total

    def stats(self, db: Session) -> Dict[str, Any]:
        from sqlalchemy import func
        total = db.query(func.count(PaymentLink.id)).scalar() or 0
        paid = db.query(func.count(PaymentLink.id)).filter(PaymentLink.status == "paid").scalar() or 0
        pending = db.query(func.count(PaymentLink.id)).filter(PaymentLink.status == "pending").scalar() or 0
        total_paid_irr = (
            db.query(func.coalesce(func.sum(PaymentLink.amount_irr), 0))
            .filter(PaymentLink.status == "paid")
            .scalar()
            or 0
        )
        return {
            "total": total,
            "paid": paid,
            "pending": pending,
            "total_paid_irr": total_paid_irr,
        }


pay_link_service = PaymentLinkService()
