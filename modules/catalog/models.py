"""
Catalog Module - Models
========================
Product, ProductCategory, PackageType, GiftBox, Batch and their images.
"""

from sqlalchemy import (
    Column, Integer, String, Text, BigInteger, Numeric, Boolean,
    ForeignKey, DateTime, UniqueConstraint, CheckConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from config.database import Base


# ==========================================
# 🗂️ Product Category
# ==========================================

class ProductCategory(Base):
    __tablename__ = "product_categories"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    slug = Column(String, nullable=False, unique=True)
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)

    product_links = relationship("ProductCategoryLink", back_populates="category", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ProductCategory {self.name}>"


# ==========================================
# 🔗 Product ↔ Category (M2M Junction)
# ==========================================

class ProductCategoryLink(Base):
    __tablename__ = "product_category_links"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("product_categories.id", ondelete="CASCADE"), nullable=False, index=True)

    product = relationship("Product", back_populates="category_links")
    category = relationship("ProductCategory", back_populates="product_links")

    __table_args__ = (
        UniqueConstraint("product_id", "category_id", name="uq_product_category_link"),
    )


# ==========================================
# 🔗 Product ↔ PackageType (M2M Junction)
# ==========================================

class ProductPackageLink(Base):
    __tablename__ = "product_package_links"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    package_type_id = Column(Integer, ForeignKey("package_types.id", ondelete="CASCADE"), nullable=False, index=True)

    product = relationship("Product", back_populates="package_links")
    package_type = relationship("PackageType")

    __table_args__ = (
        UniqueConstraint("product_id", "package_type_id", name="uq_product_package_link"),
    )


# ==========================================
# 📦 Product
# ==========================================

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    weight = Column(Numeric(10, 3), nullable=False)           # گرم
    purity = Column(Numeric(4, 1), default=750, nullable=False)  # عیار (750, 995, 999.9)
    wage = Column(Numeric(5, 2), default=0, nullable=False)     # اجرت ساخت (درصدی)
    buyback_wage_percent = Column(Numeric(5, 2), default=0, nullable=False)  # درصد اجرت بازخرید (جدا از اجرت ساخت)
    is_wage_percent = Column(Boolean, default=True, nullable=False)  # همیشه True برای شمش
    metal_type = Column(String(20), default="gold", nullable=False)  # "gold", "silver" — maps to PRECIOUS_METALS keys
    package_type_id = Column(Integer, ForeignKey("package_types.id", ondelete="SET NULL"), nullable=True, index=True)

    __table_args__ = (
        CheckConstraint("purity > 0 AND purity <= 999.9", name="ck_product_purity_range"),
        CheckConstraint("weight > 0", name="ck_product_weight_positive"),
        CheckConstraint("wage >= 0", name="ck_product_wage_nonneg"),
        CheckConstraint("buyback_wage_percent >= 0", name="ck_product_buyback_wage_nonneg"),
    )
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)

    # Relationships
    category_links = relationship("ProductCategoryLink", back_populates="product", cascade="all, delete-orphan")
    package_type = relationship("PackageType", foreign_keys=[package_type_id])
    package_links = relationship("ProductPackageLink", back_populates="product", cascade="all, delete-orphan")
    images = relationship("ProductImage", back_populates="product", cascade="all, delete-orphan")
    tier_wages = relationship("ProductTierWage", back_populates="product", cascade="all, delete-orphan")

    @property
    def categories(self):
        """Get list of ProductCategory objects for this product."""
        return [link.category for link in self.category_links]

    @property
    def category_ids(self):
        """Get list of category IDs for this product."""
        return [link.category_id for link in self.category_links]

    @property
    def allowed_packages(self):
        """Get list of PackageType objects allowed for this product."""
        return [link.package_type for link in self.package_links]

    @property
    def allowed_package_ids(self):
        """Get list of allowed package type IDs."""
        return [link.package_type_id for link in self.package_links]

    @property
    def default_image(self):
        for img in self.images:
            if img.is_default:
                return img.file_path
        return self.images[0].file_path if self.images else None

    def get_wage_for_tier(self, tier_id: int) -> float:
        """Get wage percent for a specific tier. Fallback to product.wage."""
        for tw in self.tier_wages:
            if tw.tier_id == tier_id:
                return float(tw.wage_percent)
        return float(self.wage) if self.is_wage_percent else 7.0

    def __repr__(self):
        return f"<Product {self.name} ({self.weight}g)>"


class ProductImage(Base):
    __tablename__ = "product_images"

    id = Column(Integer, primary_key=True)
    file_path = Column(String, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)

    product = relationship("Product", back_populates="images")


# ==========================================
# 📦 Package Type (کارت محصول — بسته‌بندی وکیوم)
# ==========================================

class PackageType(Base):
    __tablename__ = "package_types"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    price = Column(BigInteger, default=0, nullable=False)       # قیمت بسته‌بندی (ریال)
    is_active = Column(Boolean, default=True, nullable=False)

    images = relationship("PackageTypeImage", back_populates="package", cascade="all, delete-orphan")

    @property
    def default_image(self):
        for img in self.images:
            if img.is_default:
                return img.file_path
        return self.images[0].file_path if self.images else None


class PackageTypeImage(Base):
    __tablename__ = "package_type_images"

    id = Column(Integer, primary_key=True)
    file_path = Column(String, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)
    package_id = Column(Integer, ForeignKey("package_types.id", ondelete="CASCADE"), nullable=True, index=True)

    package = relationship("PackageType", back_populates="images")


# ==========================================
# 🎁 Gift Box (جعبه کادو — بسته‌بندی بیرونی انتخابی مشتری)
# ==========================================

class GiftBox(Base):
    __tablename__ = "gift_boxes"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(Text, nullable=True)
    price = Column(BigInteger, default=0, nullable=False)       # قیمت (ریال)
    is_active = Column(Boolean, default=True, nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)

    images = relationship("GiftBoxImage", back_populates="gift_box", cascade="all, delete-orphan")

    @property
    def default_image(self):
        for img in self.images:
            if img.is_default:
                return img.file_path
        return self.images[0].file_path if self.images else None


class GiftBoxImage(Base):
    __tablename__ = "gift_box_images"

    id = Column(Integer, primary_key=True)
    file_path = Column(String, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)
    gift_box_id = Column(Integer, ForeignKey("gift_boxes.id", ondelete="CASCADE"), nullable=False, index=True)

    gift_box = relationship("GiftBox", back_populates="images")


# ==========================================
# 🔥 Batch (بچ / ذوب)
# ==========================================

class Batch(Base):
    __tablename__ = "batches"

    id = Column(Integer, primary_key=True)
    batch_number = Column(String, unique=True, nullable=False)
    melt_number = Column(String, nullable=True)
    operator = Column(String, nullable=True)
    purity = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    images = relationship("BatchImage", back_populates="batch", cascade="all, delete-orphan")

    @property
    def default_image(self):
        for img in self.images:
            if img.is_default:
                return img.file_path
        return self.images[0].file_path if self.images else None


class BatchImage(Base):
    __tablename__ = "batch_images"

    id = Column(Integer, primary_key=True)
    file_path = Column(String, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)
    batch_id = Column(Integer, ForeignKey("batches.id", ondelete="CASCADE"), nullable=False, index=True)

    batch = relationship("Batch", back_populates="images")


# ==========================================
# 📊 Product Tier Wage (اجرت پلکانی)
# ==========================================

class ProductTierWage(Base):
    __tablename__ = "product_tier_wages"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    tier_id = Column(Integer, ForeignKey("dealer_tiers.id", ondelete="CASCADE"), nullable=False, index=True)
    wage_percent = Column(Numeric(5, 2), nullable=False)

    product = relationship("Product", back_populates="tier_wages")
    tier = relationship("DealerTier")

    __table_args__ = (
        UniqueConstraint("product_id", "tier_id", name="uq_product_tier_wage"),
    )
