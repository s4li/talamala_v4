"""
Admin Module - Models
======================
SystemUser: Staff/Admin/Operator users
SystemSetting: Key-value system configuration
RequestLog: HTTP request audit trail
"""

import json

from sqlalchemy import Column, Integer, String, DateTime, Text, Index
from sqlalchemy.sql import func
from config.database import Base


class SystemUser(Base):
    __tablename__ = "system_users"

    id = Column(Integer, primary_key=True)
    mobile = Column(String, unique=True, nullable=False, index=True)
    full_name = Column(String, nullable=False)
    role = Column(String, default="operator", nullable=False)  # "admin" | "operator"
    avatar_path = Column(String, nullable=True)

    # Granular permissions: JSON list of permission keys, e.g. '["dashboard","orders"]'
    _permissions = Column("permissions", Text, nullable=True)

    # OTP fields (used by auth module)
    otp_code = Column(String, nullable=True)
    otp_expiry = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

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
        """Check permission. role=='admin' always returns True (super admin bypass)."""
        if self.role == "admin":
            return True
        return perm_key in self.permissions

    @property
    def role_label(self) -> str:
        return {"admin": "مدیر کل", "operator": "اپراتور"}.get(self.role, self.role)

    @property
    def role_color(self) -> str:
        return {"admin": "danger", "operator": "warning"}.get(self.role, "secondary")

    def __repr__(self):
        return f"<SystemUser {self.mobile} ({self.role})>"


class SystemSetting(Base):
    __tablename__ = "system_settings"

    key = Column(String, primary_key=True)
    value = Column(String, nullable=False)
    description = Column(String, nullable=True)

    def __repr__(self):
        return f"<Setting {self.key}={self.value}>"


# ==========================================
# Request Audit Log
# ==========================================

class RequestLog(Base):
    __tablename__ = "request_logs"

    id = Column(Integer, primary_key=True)
    method = Column(String(10), nullable=False)                  # GET, POST, PUT, DELETE
    path = Column(String(500), nullable=False)                   # URL path (no query string)
    query_string = Column(Text, nullable=True)                   # query parameters
    status_code = Column(Integer, nullable=False)                # HTTP response status
    ip_address = Column(String(45), nullable=True)               # IPv4 / IPv6
    user_agent = Column(String(500), nullable=True)              # Browser / client info
    user_type = Column(String(20), nullable=False, default="anonymous")  # admin/operator/customer/dealer/anonymous
    user_id = Column(Integer, nullable=True)                     # user PK (if authenticated)
    user_display = Column(String(200), nullable=True)            # name or mobile (quick display)
    body_preview = Column(Text, nullable=True)                   # POST body (truncated, sensitive masked)
    response_time_ms = Column(Integer, nullable=True)            # response duration (ms)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_reqlog_created", "created_at"),
        Index("ix_reqlog_method", "method"),
        Index("ix_reqlog_path", "path"),
        Index("ix_reqlog_user_type", "user_type"),
        Index("ix_reqlog_ip", "ip_address"),
    )

    @property
    def method_color(self) -> str:
        return {"GET": "info", "POST": "success", "PUT": "warning", "PATCH": "warning",
                "DELETE": "danger"}.get(self.method, "secondary")

    @property
    def status_color(self) -> str:
        if self.status_code < 300:
            return "success"
        elif self.status_code < 400:
            return "info"
        elif self.status_code < 500:
            return "warning"
        return "danger"

    @property
    def user_type_label(self) -> str:
        return {"admin": "مدیر", "operator": "اپراتور", "customer": "مشتری",
                "dealer": "نماینده", "anonymous": "ناشناس"}.get(self.user_type, self.user_type)

    @property
    def user_type_color(self) -> str:
        return {"admin": "danger", "operator": "warning", "customer": "info",
                "dealer": "purple", "anonymous": "secondary"}.get(self.user_type, "secondary")
