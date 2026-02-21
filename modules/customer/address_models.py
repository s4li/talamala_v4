"""
Customer Module - Address & Geo Models
=========================================
GeoProvince, GeoCity, GeoDistrict: Iran geographic data.
CustomerAddress: Saved addresses for postal delivery.
"""

from sqlalchemy import (
    Column, Integer, String, Boolean, ForeignKey, DateTime, Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from config.database import Base


# ==========================================
# Geographic Data
# ==========================================

class GeoProvince(Base):
    __tablename__ = "geo_provinces"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    sort_order = Column(Integer, default=0)

    cities = relationship("GeoCity", back_populates="province", cascade="all, delete-orphan")


class GeoCity(Base):
    __tablename__ = "geo_cities"

    id = Column(Integer, primary_key=True)
    province_id = Column(Integer, ForeignKey("geo_provinces.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False)
    sort_order = Column(Integer, default=0)

    province = relationship("GeoProvince", back_populates="cities")
    districts = relationship("GeoDistrict", back_populates="city", cascade="all, delete-orphan")


class GeoDistrict(Base):
    __tablename__ = "geo_districts"

    id = Column(Integer, primary_key=True)
    city_id = Column(Integer, ForeignKey("geo_cities.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False)

    city = relationship("GeoCity", back_populates="districts")


# ==========================================
# Customer Address
# ==========================================

class CustomerAddress(Base):
    __tablename__ = "customer_addresses"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String, nullable=False)  # عنوان: خانه، محل کار، ...
    province_id = Column(Integer, ForeignKey("geo_provinces.id", ondelete="RESTRICT"), nullable=False, index=True)
    city_id = Column(Integer, ForeignKey("geo_cities.id", ondelete="RESTRICT"), nullable=False, index=True)
    district_id = Column(Integer, ForeignKey("geo_districts.id", ondelete="SET NULL"), nullable=True, index=True)
    address = Column(Text, nullable=False)
    postal_code = Column(String(10), nullable=True)
    receiver_name = Column(String, nullable=True)
    receiver_phone = Column(String(15), nullable=True)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User")
    province = relationship("GeoProvince")
    city = relationship("GeoCity")
    district = relationship("GeoDistrict")

    @property
    def full_address(self) -> str:
        parts = []
        if self.province:
            parts.append(self.province.name)
        if self.city:
            parts.append(self.city.name)
        if self.district:
            parts.append(self.district.name)
        parts.append(self.address)
        return "، ".join(parts)
