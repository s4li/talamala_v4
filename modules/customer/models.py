"""
Customer Module - Models
=========================
Customer: End-user who buys gold bars.

NOTE on Relationships:
    Cross-module relationships (bars, orders, cart, accounts, etc.)
    are registered dynamically when each module is loaded.
    See modules/<module>/models.py for relationship setup.
"""

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from config.database import Base


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    national_id = Column(String, unique=True, index=True, nullable=False)
    mobile = Column(String, unique=True, index=True, nullable=False)
    birth_date = Column(String, nullable=True)
    avatar_path = Column(String, nullable=True)

    # OTP fields (used by auth module)
    otp_code = Column(String, nullable=True)
    otp_expiry = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    @property
    def full_name(self) -> str:
        parts = [self.first_name or "", self.last_name or ""]
        return " ".join(p for p in parts if p).strip() or "کاربر"

    def __repr__(self):
        return f"<Customer {self.mobile} ({self.full_name})>"
