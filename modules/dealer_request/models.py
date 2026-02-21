"""
Dealer Request Module - Models
=================================
Prospective dealers submit applications through the public form.
Admin reviews and approves/rejects them.

Models:
  - DealerRequest: Application submitted by a user
  - DealerRequestAttachment: Document/image uploaded with the request

Enums:
  - DealerRequestStatus: Pending / Approved / Rejected / RevisionNeeded
  - Gender: male / female
"""

import enum
from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey, Text, Index,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from config.database import Base


# ==========================================
# Enums
# ==========================================

class DealerRequestStatus(str, enum.Enum):
    PENDING = "Pending"
    APPROVED = "Approved"
    REJECTED = "Rejected"
    REVISION_NEEDED = "RevisionNeeded"


class Gender(str, enum.Enum):
    MALE = "male"
    FEMALE = "female"


# ==========================================
# DealerRequest
# ==========================================

class DealerRequest(Base):
    __tablename__ = "dealer_requests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    birth_date = Column(String, nullable=True)       # Jalali format "1370/01/15"
    email = Column(String, nullable=True)
    mobile = Column(String, nullable=False)
    gender = Column(String, nullable=True)            # Gender enum value
    province_id = Column(Integer, ForeignKey("geo_provinces.id", ondelete="SET NULL"), nullable=True)
    city_id = Column(Integer, ForeignKey("geo_cities.id", ondelete="SET NULL"), nullable=True)
    status = Column(String, nullable=False, default=DealerRequestStatus.PENDING.value)
    admin_note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    province = relationship("GeoProvince", foreign_keys=[province_id])
    city = relationship("GeoCity", foreign_keys=[city_id])
    attachments = relationship(
        "DealerRequestAttachment", back_populates="dealer_request",
        cascade="all, delete-orphan", lazy="joined",
    )

    __table_args__ = (
        Index("ix_dealer_req_user", "user_id"),
        Index("ix_dealer_req_status", "status"),
    )

    # --- Properties ---

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def status_label(self) -> str:
        return {
            DealerRequestStatus.PENDING.value: "\u062f\u0631 \u0627\u0646\u062a\u0638\u0627\u0631 \u0628\u0631\u0631\u0633\u06cc",
            DealerRequestStatus.APPROVED.value: "\u062a\u0627\u06cc\u06cc\u062f \u0634\u062f\u0647",
            DealerRequestStatus.REJECTED.value: "\u0631\u062f \u0634\u062f\u0647",
            DealerRequestStatus.REVISION_NEEDED.value: "\u0646\u06cc\u0627\u0632 \u0628\u0647 \u0627\u0635\u0644\u0627\u062d",
        }.get(self.status, self.status)

    @property
    def status_color(self) -> str:
        return {
            DealerRequestStatus.PENDING.value: "warning",
            DealerRequestStatus.APPROVED.value: "success",
            DealerRequestStatus.REJECTED.value: "danger",
            DealerRequestStatus.REVISION_NEEDED.value: "info",
        }.get(self.status, "secondary")

    @property
    def gender_label(self) -> str:
        return {
            Gender.MALE.value: "\u0645\u0631\u062f",
            Gender.FEMALE.value: "\u0632\u0646",
        }.get(self.gender, "\u2014")

    @property
    def province_name(self) -> str:
        return self.province.name if self.province else "\u2014"

    @property
    def city_name(self) -> str:
        return self.city.name if self.city else "\u2014"


# ==========================================
# DealerRequestAttachment
# ==========================================

class DealerRequestAttachment(Base):
    __tablename__ = "dealer_request_attachments"

    id = Column(Integer, primary_key=True, index=True)
    dealer_request_id = Column(
        Integer,
        ForeignKey("dealer_requests.id", ondelete="CASCADE"),
        nullable=False,
    )
    file_path = Column(String, nullable=False)
    original_filename = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    dealer_request = relationship("DealerRequest", back_populates="attachments")

    __table_args__ = (
        Index("ix_dealer_req_attach_req", "dealer_request_id"),
    )
