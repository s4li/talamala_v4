"""
Delivery Module - Service Layer
==================================
Delivery code generation, dealer-based location filtering, shipping cost calculation.
"""

import secrets
import hashlib
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import func

from common.templating import get_setting_from_db
from modules.inventory.models import Bar, BarStatus
from modules.user.models import User
from modules.customer.address_models import GeoProvince, GeoCity


def generate_delivery_code() -> Tuple[str, str]:
    """
    Generate a 6-digit delivery code and its hash.
    Returns: (plain_code, hashed_code)
    """
    code = "".join([str(secrets.randbelow(10)) for _ in range(6)])
    hashed = hashlib.sha256(code.encode()).hexdigest()
    return code, hashed


def verify_delivery_code(plain_code: str, hashed_code: str) -> bool:
    """Verify a delivery code against its hash."""
    return hashlib.sha256(plain_code.encode()).hexdigest() == hashed_code


class DeliveryService:

    # ==========================================
    # Province / City Filtering (from Dealers)
    # ==========================================

    def get_provinces_with_branches(self, db: Session) -> List[str]:
        """Get distinct province names that have active dealers (for pickup)."""
        rows = db.query(GeoProvince.name).join(
            User, User.province_id == GeoProvince.id,
        ).filter(
            User.is_dealer == True,
            User.is_active == True,
        ).distinct().order_by(GeoProvince.name).all()
        return [r[0] for r in rows]

    def get_cities_in_province(self, db: Session, province: str) -> List[str]:
        """Get distinct city names in a province that have active dealers."""
        rows = db.query(GeoCity.name).join(
            User, User.city_id == GeoCity.id,
        ).join(
            GeoProvince, User.province_id == GeoProvince.id,
        ).filter(
            User.is_dealer == True,
            User.is_active == True,
            GeoProvince.name == province,
        ).distinct().order_by(GeoCity.name).all()
        return [r[0] for r in rows]

    def get_pickup_dealers(
        self,
        db: Session,
        province: str = None,
        city: str = None,
        product_ids: List[int] = None,
    ) -> List[dict]:
        """
        Get dealers where pickup is available.
        If product_ids given, also shows available inventory per dealer.
        """
        q = db.query(User).filter(
            User.is_dealer == True,
            User.is_active == True,
        )
        if province:
            q = q.join(GeoProvince, User.province_id == GeoProvince.id).filter(
                GeoProvince.name == province,
            )
        if city:
            q = q.join(GeoCity, User.city_id == GeoCity.id).filter(
                GeoCity.name == city,
            )

        dealers = q.order_by(User.full_name).all()

        results = []
        for dealer in dealers:
            bar_q = db.query(func.count(Bar.id)).filter(
                Bar.dealer_id == dealer.id,
                Bar.status == BarStatus.ASSIGNED,
                Bar.customer_id.is_(None),
                Bar.reserved_customer_id.is_(None),
            )
            if product_ids:
                bar_q = bar_q.filter(Bar.product_id.in_(product_ids))

            stock = bar_q.scalar() or 0

            results.append({
                "id": dealer.id,
                "name": dealer.full_name,
                "province": dealer.province_name,
                "city": dealer.city_name,
                "address": dealer.address or "",
                "phone": dealer.landline_phone or "",
                "type": dealer.type_label,
                "type_label": dealer.type_label,
                "stock": stock,
            })

        return results

    # ==========================================
    # Postal Hub (dealer with is_postal_hub=True)
    # ==========================================

    def get_postal_hub(self, db: Session) -> Optional[User]:
        """Get the designated postal shipping dealer/warehouse."""
        return db.query(User).filter(
            User.is_dealer == True,
            User.is_postal_hub == True,
            User.is_active == True,
        ).first()

    def get_postal_hub_stock(self, db: Session, product_ids: List[int] = None) -> int:
        """Count available bars in the postal hub."""
        hub = self.get_postal_hub(db)
        if not hub:
            return 0
        q = db.query(func.count(Bar.id)).filter(
            Bar.dealer_id == hub.id,
            Bar.status == BarStatus.ASSIGNED,
            Bar.customer_id.is_(None),
            Bar.reserved_customer_id.is_(None),
        )
        if product_ids:
            q = q.filter(Bar.product_id.in_(product_ids))
        return q.scalar() or 0

    # ==========================================
    # Shipping Cost Calculation
    # ==========================================

    def calculate_shipping(self, db: Session, cart_total: int) -> dict:
        """
        Calculate shipping and insurance costs.
        Returns: {
            shipping_cost, insurance_cost, total_delivery_cost,
            is_available, unavailable_reason,
            insurance_cap
        }
        """
        shipping_cost = int(get_setting_from_db(db, "shipping_cost", "500000"))        # ریال
        insurance_percent = float(get_setting_from_db(db, "insurance_percent", "1.5"))  # درصد
        insurance_cap = int(get_setting_from_db(db, "insurance_cap", "500000000"))      # ریال - سقف بیمه

        insurance_cost = int(cart_total * insurance_percent / 100)

        # Check insurance cap
        is_available = cart_total <= insurance_cap
        unavailable_reason = ""
        if not is_available:
            unavailable_reason = (
                f"به دلیل سقف بیمه پست ({self._format_toman(insurance_cap)} تومان)، "
                f"این سفارش فقط قابلیت تحویل حضوری دارد."
            )

        return {
            "shipping_cost": shipping_cost,
            "insurance_cost": insurance_cost,
            "total_delivery_cost": shipping_cost + insurance_cost,
            "is_available": is_available,
            "unavailable_reason": unavailable_reason,
            "insurance_cap": insurance_cap,
        }

    # ==========================================
    # Helpers
    # ==========================================

    def _format_toman(self, rial: int) -> str:
        toman = rial // 10
        return f"{toman:,}"


# Singleton
delivery_service = DeliveryService()
