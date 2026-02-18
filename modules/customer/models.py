"""
Customer Module - Models
=========================
Customer: End-user who buys gold bars.

NOTE on Relationships:
    Cross-module relationships (bars, orders, cart, accounts, etc.)
    are registered dynamically when each module is loaded.
    See modules/<module>/models.py for relationship setup.
"""

import secrets
import string

from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from config.database import Base


def generate_referral_code(length: int = 8) -> str:
    """Generate a random uppercase alphanumeric referral code."""
    chars = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(chars) for _ in range(length))


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    national_id = Column(String, unique=True, index=True, nullable=False)
    mobile = Column(String, unique=True, index=True, nullable=False)
    birth_date = Column(String, nullable=True)
    avatar_path = Column(String, nullable=True)
    is_active = Column(Boolean, default=True, server_default="true", nullable=False)

    # Legal entity type: "real" (حقیقی) or "legal" (حقوقی)
    customer_type = Column(String, nullable=True)  # "real" | "legal"
    company_name = Column(String, nullable=True)   # نام شرکت (فقط حقوقی)
    economic_code = Column(String, nullable=True)   # کد اقتصادی (فقط حقوقی)
    postal_code = Column(String, nullable=True)     # کد پستی
    address = Column(String, nullable=True)         # نشانی
    phone = Column(String, nullable=True)           # شماره تماس ثابت

    # Referral
    referral_code = Column(String(10), unique=True, nullable=True, index=True)
    referred_by = Column(Integer, nullable=True)        # customer_id of referrer
    referral_rewarded = Column(Boolean, default=False, server_default="false")

    # OTP fields (used by auth module)
    otp_code = Column(String, nullable=True)
    otp_expiry = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    @property
    def full_name(self) -> str:
        parts = [self.first_name or "", self.last_name or ""]
        return " ".join(p for p in parts if p).strip() or "کاربر"

    @property
    def display_name(self) -> str:
        """For invoices: company name for legal entities, full_name for real persons."""
        if self.customer_type == "legal" and self.company_name:
            return self.company_name
        return self.full_name

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

    def __repr__(self):
        return f"<Customer {self.mobile} ({self.full_name})>"
