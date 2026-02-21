"""
User Module - Unified User Model
===================================
Single users table replacing customers, dealers, and system_users.
A user can have multiple roles simultaneously (is_customer, is_dealer, is_admin).
"""

import json
import secrets
import string

from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, ForeignKey,
    Text, Numeric, Index,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from config.database import Base


def generate_referral_code(length: int = 8) -> str:
    """Generate a random uppercase alphanumeric referral code."""
    chars = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(chars) for _ in range(length))


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    # === Identity ===
    mobile = Column(String(11), unique=True, nullable=False, index=True)
    national_id = Column(String, unique=True, nullable=True, index=True)

    # === Profile ===
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    birth_date = Column(String, nullable=True)
    avatar_path = Column(String, nullable=True)

    # === Auth (OTP) ===
    otp_code = Column(String, nullable=True)
    otp_expiry = Column(DateTime(timezone=True), nullable=True)

    # === Role Flags ===
    is_customer = Column(Boolean, default=False, server_default="false", nullable=False, index=True)
    is_dealer = Column(Boolean, default=False, server_default="false", nullable=False, index=True)
    is_admin = Column(Boolean, default=False, server_default="false", nullable=False, index=True)
    is_active = Column(Boolean, default=True, server_default="true", nullable=False, index=True)

    # === Customer-specific ===
    customer_type = Column(String, nullable=True)       # "real" | "legal"
    company_name = Column(String, nullable=True)
    economic_code = Column(String, nullable=True)
    postal_code = Column(String, nullable=True)
    address = Column(String, nullable=True)
    phone = Column(String, nullable=True)               # Landline
    referral_code = Column(String(10), unique=True, nullable=True, index=True)
    referred_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    referral_rewarded = Column(Boolean, default=False, server_default="false")

    # === Dealer-specific ===
    tier_id = Column(Integer, ForeignKey("dealer_tiers.id", ondelete="SET NULL"), nullable=True, index=True)
    commission_percent = Column(Numeric(5, 2), default=2.0, nullable=True)
    is_warehouse = Column(Boolean, default=False, server_default="false", nullable=False)
    is_postal_hub = Column(Boolean, default=False, server_default="false", nullable=False)
    province_id = Column(Integer, ForeignKey("geo_provinces.id", ondelete="SET NULL"), nullable=True, index=True)
    city_id = Column(Integer, ForeignKey("geo_cities.id", ondelete="SET NULL"), nullable=True, index=True)
    district_id = Column(Integer, ForeignKey("geo_districts.id", ondelete="SET NULL"), nullable=True, index=True)
    dealer_address = Column(Text, nullable=True)        # Dealer business address
    dealer_postal_code = Column(String(10), nullable=True)
    landline_phone = Column(String(15), nullable=True)
    api_key = Column(String(64), unique=True, nullable=True, index=True)
    rasis_sharepoint = Column(Integer, nullable=True)  # Rasis POS branch sharepoint ID

    # === Admin-specific ===
    admin_role = Column(String, nullable=True)           # "admin" | "operator"
    _permissions = Column("permissions", Text, nullable=True)  # JSON list

    # === Audit ===
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # === Relationships ===
    tier = relationship("DealerTier", foreign_keys=[tier_id])
    province = relationship("GeoProvince", foreign_keys=[province_id])
    city = relationship("GeoCity", foreign_keys=[city_id])
    district = relationship("GeoDistrict", foreign_keys=[district_id])
    referrer = relationship("User", remote_side=[id], foreign_keys=[referred_by])

    __table_args__ = (
        Index("ix_users_created", "created_at"),
    )

    # === Name Properties ===

    @property
    def full_name(self) -> str:
        """Compute full name from first + last."""
        parts = [self.first_name or "", self.last_name or ""]
        name = " ".join(p for p in parts if p).strip()
        return name or "کاربر"

    @property
    def display_name(self) -> str:
        """For invoices: company name for legal, full_name for real, dealer name, etc."""
        if self.is_customer and self.customer_type == "legal" and self.company_name:
            return self.company_name
        return self.full_name

    # === Customer Properties ===

    @property
    def is_profile_complete(self) -> bool:
        """Check if required profile fields are filled for ordering."""
        if not self.first_name or self.first_name == "کاربر":
            return False
        if not self.last_name or self.last_name == "مهمان":
            return False
        if not self.national_id or self.national_id.startswith("GUEST_"):
            return False
        if not self.customer_type:
            return False
        if not self.postal_code:
            return False
        if not self.address:
            return False
        if self.customer_type == "legal" and not self.company_name:
            return False
        return True

    # === Admin Properties (backward compat with SystemUser) ===

    @property
    def is_staff(self) -> bool:
        return self.is_admin

    @property
    def role(self) -> str:
        """Admin role: 'admin' or 'operator'. Returns empty string if not admin."""
        return self.admin_role or ""

    @property
    def permissions(self) -> list:
        if not self._permissions:
            return []
        try:
            return json.loads(self._permissions)
        except (json.JSONDecodeError, TypeError):
            return []

    @permissions.setter
    def permissions(self, value: list):
        self._permissions = json.dumps(value) if value else None

    @property
    def permissions_count(self) -> int:
        return len(self.permissions)

    def has_permission(self, perm_key: str) -> bool:
        """Check permission. admin_role=='admin' always returns True (super admin bypass)."""
        if self.admin_role == "admin":
            return True
        return perm_key in self.permissions

    @property
    def role_label(self) -> str:
        return {"admin": "مدیر کل", "operator": "اپراتور"}.get(self.admin_role or "", "")

    @property
    def role_color(self) -> str:
        return {"admin": "danger", "operator": "warning"}.get(self.admin_role or "", "secondary")

    # === Dealer Properties (backward compat with Dealer) ===

    @property
    def tier_name(self) -> str:
        return self.tier.name if self.tier else "—"

    @property
    def province_name(self) -> str:
        return self.province.name if self.province else "—"

    @property
    def city_name(self) -> str:
        return self.city.name if self.city else "—"

    @property
    def district_name(self) -> str:
        return self.district.name if self.district else "—"

    @property
    def full_address(self) -> str:
        parts = []
        if self.province:
            parts.append(self.province.name)
        if self.city:
            parts.append(self.city.name)
        if self.district:
            parts.append(self.district.name)
        addr = self.dealer_address or self.address
        if addr:
            parts.append(addr)
        return "، ".join(parts) if parts else "—"

    @property
    def dealer_display_name(self) -> str:
        """Full display: نمایندگی اصفهان - اصفهان"""
        parts = [self.full_name]
        if self.city:
            city_name = self.city.name
            parts.append(f"- {city_name}")
            if self.province and self.province.name != city_name:
                parts.append(f"({self.province.name})")
        return " ".join(parts)

    @property
    def type_label(self) -> str:
        if self.is_warehouse:
            return "انبار مرکزی"
        return self.tier_name

    @property
    def type_icon(self) -> str:
        if self.is_warehouse:
            return "bi-box-seam"
        return "bi-shop"

    @property
    def type_color(self) -> str:
        if self.is_warehouse:
            return "primary"
        return "success"

    # === Roles ===

    @property
    def roles(self) -> list:
        """Returns list of active role strings."""
        r = []
        if self.is_customer:
            r.append("customer")
        if self.is_dealer:
            r.append("dealer")
        if self.is_admin:
            r.append("admin")
        return r

    @property
    def primary_redirect(self) -> str:
        """Where to redirect after login, based on highest role."""
        if self.is_admin:
            return "/admin/dashboard"
        if self.is_dealer:
            return "/dealer/dashboard"
        return "/"

    def __repr__(self):
        role_str = "+".join(self.roles) or "guest"
        return f"<User {self.mobile} ({role_str}) {self.full_name}>"
