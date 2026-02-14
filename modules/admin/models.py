"""
Admin Module - Models
======================
SystemUser: Staff/Admin/Operator users
SystemSetting: Key-value system configuration
"""

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from config.database import Base


class SystemUser(Base):
    __tablename__ = "system_users"

    id = Column(Integer, primary_key=True)
    mobile = Column(String, unique=True, nullable=False, index=True)
    full_name = Column(String, nullable=False)
    role = Column(String, default="operator", nullable=False)  # "admin" | "operator"
    avatar_path = Column(String, nullable=True)

    # OTP fields (used by auth module)
    otp_code = Column(String, nullable=True)
    otp_expiry = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<SystemUser {self.mobile} ({self.role})>"


class SystemSetting(Base):
    __tablename__ = "system_settings"

    key = Column(String, primary_key=True)
    value = Column(String, nullable=False)
    description = Column(String, nullable=True)

    def __repr__(self):
        return f"<Setting {self.key}={self.value}>"
