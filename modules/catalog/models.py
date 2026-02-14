"""
Catalog Module - Models
========================
Product, ProductCategory, CardDesign, PackageType, Batch and their images.
"""

from sqlalchemy import (
    Column, Integer, String, BigInteger, Numeric, Boolean,
    ForeignKey, DateTime, UniqueConstraint,
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
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    category_id = Column(Integer, ForeignKey("product_categories.id", ondelete="CASCADE"), nullable=False)

    product = relationship("Product", back_populates="category_links")
    category = relationship("ProductCategory", back_populates="product_links")

    __table_args__ = (
        UniqueConstraint("product_id", "category_id", name="uq_product_category_link"),
    )


# ==========================================
# 📦 Product
# ==========================================

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    weight = Column(Numeric(10, 3), nullable=False)           # گرم
    purity = Column(Integer, default=750, nullable=False)      # عیار (750 = 18K)
    wage = Column(BigInteger, default=0, nullable=False)       # اجرت ساخت
    is_wage_percent = Column(Boolean, default=True, nullable=False)  # اجرت درصدی یا ریالی
    profit_percent = Column(Numeric(5, 2), default=7.0, nullable=False)
    commission_percent = Column(Numeric(5, 2), default=0.0, nullable=False)
    stone_price = Column(BigInteger, default=0, nullable=False)          # قیمت سنگ
    accessory_cost = Column(BigInteger, default=0, nullable=False)       # هزینه متفرقه
    accessory_profit_percent = Column(Numeric(5, 2), default=15.0, nullable=False)
    design = Column(String, nullable=True)
    card_design_id = Column(Integer, ForeignKey("card_designs.id", ondelete="SET NULL"), nullable=True)
    package_type_id = Column(Integer, ForeignKey("package_types.id", ondelete="SET NULL"), nullable=True)
    is_active = Column(Boolean, default=True)

    # Relationships
    category_links = relationship("ProductCategoryLink", back_populates="product", cascade="all, delete-orphan")
    card_design = relationship("CardDesign", foreign_keys=[card_design_id])
    package_type = relationship("PackageType", foreign_keys=[package_type_id])
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
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)

    product = relationship("Product", back_populates="images")


# ==========================================
# 🎨 Card Design (طرح کارت)
# ==========================================

class CardDesign(Base):
    __tablename__ = "card_designs"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)

    images = relationship("CardDesignImage", back_populates="design", cascade="all, delete-orphan")

    @property
    def default_image(self):
        for img in self.images:
            if img.is_default:
                return img.file_path
        return self.images[0].file_path if self.images else None


class CardDesignImage(Base):
    __tablename__ = "design_images"

    id = Column(Integer, primary_key=True)
    file_path = Column(String, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)
    design_id = Column(Integer, ForeignKey("card_designs.id", ondelete="CASCADE"), nullable=True)

    design = relationship("CardDesign", back_populates="images")


# ==========================================
# 📦 Package Type (نوع بسته‌بندی)
# ==========================================

class PackageType(Base):
    __tablename__ = "package_types"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)

    images = relationship("PackageTypeImage", back_populates="package", cascade="all, delete-orphan")

    @property
    def default_image(self):
        for img in self.images:
            if img.is_default:
                return img.file_path
        return self.images[0].file_path if self.images else None


class PackageTypeImage(Base):
    __tablename__ = "package_images"

    id = Column(Integer, primary_key=True)
    file_path = Column(String, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)
    package_id = Column(Integer, ForeignKey("package_types.id", ondelete="CASCADE"), nullable=True)

    package = relationship("PackageType", back_populates="images")


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
    batch_id = Column(Integer, ForeignKey("batches.id", ondelete="CASCADE"), nullable=False)

    batch = relationship("Batch", back_populates="images")


# ==========================================
# 📊 Product Tier Wage (اجرت پلکانی)
# ==========================================

class ProductTierWage(Base):
    __tablename__ = "product_tier_wages"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    tier_id = Column(Integer, ForeignKey("dealer_tiers.id", ondelete="CASCADE"), nullable=False)
    wage_percent = Column(Numeric(5, 2), nullable=False)

    product = relationship("Product", back_populates="tier_wages")
    tier = relationship("DealerTier")

    __table_args__ = (
        UniqueConstraint("product_id", "tier_id", name="uq_product_tier_wage"),
    )
