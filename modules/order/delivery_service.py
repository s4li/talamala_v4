"""
Delivery Module - Service Layer
==================================
Delivery code generation, location filtering, shipping cost calculation.
"""

import secrets
import hashlib
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import func

from common.templating import get_setting_from_db
from modules.inventory.models import Bar, BarStatus, Location, LocationType


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
    # Province / City Filtering
    # ==========================================

    def get_provinces_with_branches(self, db: Session) -> List[str]:
        """Get distinct provinces that have active pickup-capable locations."""
        rows = db.query(Location.province).filter(
            Location.is_active == True,
            Location.province.isnot(None),
            Location.province != "",
            Location.location_type.in_([
                LocationType.BRANCH, LocationType.WAREHOUSE,
            ]),
        ).distinct().order_by(Location.province).all()
        return [r[0] for r in rows]

    def get_cities_in_province(self, db: Session, province: str) -> List[str]:
        """Get distinct cities in a province that have active locations."""
        rows = db.query(Location.city).filter(
            Location.is_active == True,
            Location.province == province,
            Location.city.isnot(None),
            Location.city != "",
            Location.location_type.in_([
                LocationType.BRANCH, LocationType.WAREHOUSE,
            ]),
        ).distinct().order_by(Location.city).all()
        return [r[0] for r in rows]

    def get_pickup_locations(
        self,
        db: Session,
        province: str = None,
        city: str = None,
        product_ids: List[int] = None,
    ) -> List[dict]:
        """
        Get locations where pickup is available.
        If product_ids given, also shows available inventory per location.
        """
        q = db.query(Location).filter(
            Location.is_active == True,
            Location.location_type.in_([
                LocationType.BRANCH, LocationType.WAREHOUSE,
            ]),
        )
        if province:
            q = q.filter(Location.province == province)
        if city:
            q = q.filter(Location.city == city)

        locations = q.order_by(Location.name).all()

        results = []
        for loc in locations:
            bar_q = db.query(func.count(Bar.id)).filter(
                Bar.location_id == loc.id,
                Bar.status == BarStatus.ASSIGNED,
                Bar.customer_id.is_(None),
                Bar.reserved_customer_id.is_(None),
            )
            if product_ids:
                bar_q = bar_q.filter(Bar.product_id.in_(product_ids))

            stock = bar_q.scalar() or 0

            results.append({
                "id": loc.id,
                "name": loc.name,
                "province": loc.province or "",
                "city": loc.city or "",
                "address": loc.address or "",
                "phone": loc.phone or "",
                "type": loc.location_type,
                "type_label": loc.type_label,
                "stock": stock,
            })

        return results

    # ==========================================
    # Postal Hub
    # ==========================================

    def get_postal_hub(self, db: Session) -> Optional[Location]:
        """Get the designated postal shipping warehouse."""
        loc = db.query(Location).filter(
            Location.is_postal_hub == True,
            Location.is_active == True,
        ).first()
        return loc

    def get_postal_hub_stock(self, db: Session, product_ids: List[int] = None) -> int:
        """Count available bars in the postal hub."""
        hub = self.get_postal_hub(db)
        if not hub:
            return 0
        q = db.query(func.count(Bar.id)).filter(
            Bar.location_id == hub.id,
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
