"""
Catalog Module - Service Layer
================================
Business logic for Products, Designs, Packages, and Batches.
Generic image management to avoid code duplication.
"""

from typing import List, Optional, Type, TypeVar
from fastapi import UploadFile
from sqlalchemy.orm import Session

from common.upload import save_upload_file, delete_file
from decimal import Decimal
from common.helpers import safe_int, safe_decimal
from modules.dealer.models import DealerTier
from modules.catalog.models import (
    ProductTierWage,
    Product, ProductImage, ProductCategoryLink,
    CardDesign, CardDesignImage,
    PackageType, PackageTypeImage,
    Batch, BatchImage,
)

T = TypeVar("T")


# ==========================================
# Generic Image Manager
# ==========================================

class ImageManager:
    """
    Handles image CRUD for any entity that has an images relationship.
    Avoids repeating the same logic for Product, Design, Package, Batch.
    """

    @staticmethod
    def save_images(
        db: Session,
        entity_id: int,
        files: List[UploadFile],
        image_model: Type,
        fk_field: str,
        set_first_default: bool = True,
        subfolder: str = "",
    ) -> int:
        """
        Save uploaded images for an entity.
        Returns number of images saved.
        """
        count = 0
        first = set_first_default
        for f in files:
            if not f or not f.filename:
                continue
            path = save_upload_file(f, subfolder=subfolder)
            if path:
                img = image_model(file_path=path, is_default=first, **{fk_field: entity_id})
                first = False
                db.add(img)
                count += 1
        if count:
            db.flush()
        return count

    @staticmethod
    def delete_image(db: Session, image_model: Type, img_id: int) -> Optional[int]:
        """Delete an image and its file. Returns parent entity ID or None."""
        img = db.query(image_model).filter(image_model.id == img_id).first()
        if not img:
            return None
        delete_file(img.file_path)
        parent_id = None
        # Find the FK field dynamically
        for col in image_model.__table__.columns:
            if col.foreign_keys and col.name != "id":
                parent_id = getattr(img, col.name)
                break
        db.delete(img)
        db.flush()
        return parent_id

    @staticmethod
    def set_default(db: Session, image_model: Type, img_id: int, fk_field: str) -> Optional[int]:
        """Set an image as default, unset others."""
        target = db.query(image_model).filter(image_model.id == img_id).first()
        if not target:
            return None
        parent_id = getattr(target, fk_field)
        db.query(image_model).filter(
            getattr(image_model, fk_field) == parent_id
        ).update({"is_default": False})
        target.is_default = True
        db.flush()
        return parent_id


# Singleton
images = ImageManager()


# ==========================================
# Product Service
# ==========================================

class ProductService:

    def list_all(self, db: Session) -> List[Product]:
        return db.query(Product).order_by(Product.weight.asc()).all()

    def get_by_id(self, db: Session, product_id: int) -> Optional[Product]:
        return db.query(Product).filter(Product.id == product_id).first()

    def create(self, db: Session, data: dict, files: List[UploadFile] = None) -> Product:
        product = Product(
            name=data["name"],
            weight=data["weight"],
            purity=safe_decimal(data.get("purity", "750"), Decimal("750")),
            design=data.get("design"),
            card_design_id=data.get("card_design_id"),
            package_type_id=data.get("package_type_id"),
            wage=data.get("wage", 0),
            is_wage_percent=True,
            is_active=data.get("is_active", True),
        )
        db.add(product)
        db.flush()
        db.refresh(product)

        # M2M categories
        for cat_id in (data.get("category_ids") or []):
            db.add(ProductCategoryLink(product_id=product.id, category_id=int(cat_id)))
        if data.get("category_ids"):
            db.flush()

        # Auto-sync end_customer tier wage from product wage
        ec_tier = db.query(DealerTier).filter(DealerTier.is_end_customer == True, DealerTier.is_active == True).first()
        if ec_tier:
            ptw = db.query(ProductTierWage).filter(
                ProductTierWage.product_id == product.id,
                ProductTierWage.tier_id == ec_tier.id,
            ).first()
            if ptw:
                ptw.wage_percent = product.wage
            else:
                db.add(ProductTierWage(product_id=product.id, tier_id=ec_tier.id, wage_percent=product.wage))
            db.flush()

        if files:
            images.save_images(db, product.id, files, ProductImage, "product_id", subfolder="products")

        return product

    def update(self, db: Session, product_id: int, data: dict, files: List[UploadFile] = None) -> Optional[Product]:
        p = self.get_by_id(db, product_id)
        if not p:
            return None

        p.name = data["name"]
        p.weight = data["weight"]
        p.purity = safe_decimal(data.get("purity", "750"), Decimal("750"))
        p.design = data.get("design")
        p.description = data.get("description") or None
        p.card_design_id = data.get("card_design_id")
        p.package_type_id = data.get("package_type_id")
        p.wage = data.get("wage", 0)
        p.is_wage_percent = True
        p.is_active = data.get("is_active", False)

        # Sync M2M categories
        if "category_ids" in data:
            db.query(ProductCategoryLink).filter(ProductCategoryLink.product_id == p.id).delete()
            for cat_id in (data["category_ids"] or []):
                db.add(ProductCategoryLink(product_id=p.id, category_id=int(cat_id)))

        db.flush()

        # Auto-sync end_customer tier wage from product wage
        ec_tier = db.query(DealerTier).filter(DealerTier.is_end_customer == True, DealerTier.is_active == True).first()
        if ec_tier:
            ptw = db.query(ProductTierWage).filter(
                ProductTierWage.product_id == p.id,
                ProductTierWage.tier_id == ec_tier.id,
            ).first()
            if ptw:
                ptw.wage_percent = p.wage
            else:
                db.add(ProductTierWage(product_id=p.id, tier_id=ec_tier.id, wage_percent=p.wage))
            db.flush()

        if files:
            has_default = any(img.is_default for img in p.images)
            images.save_images(
                db, p.id, files, ProductImage, "product_id",
                set_first_default=not has_default, subfolder="products",
            )

        return p


# ==========================================
# Simple Entity Service (Design, Package)
# ==========================================

class SimpleEntityService:
    """Generic service for entities with just name + images."""

    def __init__(self, model, image_model, fk_field: str, subfolder: str):
        self.model = model
        self.image_model = image_model
        self.fk_field = fk_field
        self.subfolder = subfolder

    def list_all(self, db: Session):
        return db.query(self.model).all()

    def get_by_id(self, db: Session, item_id: int):
        return db.query(self.model).filter(self.model.id == item_id).first()

    def create(self, db: Session, name: str, files: List[UploadFile] = None):
        item = self.model(name=name)
        db.add(item)
        db.flush()
        db.refresh(item)

        if files:
            images.save_images(db, item.id, files, self.image_model, self.fk_field,
                             subfolder=self.subfolder)
        return item

    def update(self, db: Session, item_id: int, name: str, files: List[UploadFile] = None):
        item = self.get_by_id(db, item_id)
        if not item:
            return None
        item.name = name
        db.flush()

        if files:
            images.save_images(db, item.id, files, self.image_model, self.fk_field,
                             set_first_default=False, subfolder=self.subfolder)
        return item

    def delete(self, db: Session, item_id: int):
        db.query(self.model).filter(self.model.id == item_id).delete()
        db.flush()


# ==========================================
# Batch Service
# ==========================================

class BatchService:

    def list_all(self, db: Session) -> List[Batch]:
        return db.query(Batch).order_by(Batch.id.desc()).all()

    def get_by_id(self, db: Session, batch_id: int) -> Optional[Batch]:
        return db.query(Batch).filter(Batch.id == batch_id).first()

    def create(self, db: Session, data: dict, files: List[UploadFile] = None) -> Optional[Batch]:
        batch = Batch(
            batch_number=data["batch_number"],
            melt_number=data.get("melt_number"),
            operator=data.get("operator"),
            purity=safe_int(data.get("purity")),
        )
        db.add(batch)
        db.flush()
        db.refresh(batch)

        if files:
            images.save_images(db, batch.id, files, BatchImage, "batch_id", subfolder="batches")

        return batch

    def update(self, db: Session, batch_id: int, data: dict, files: List[UploadFile] = None) -> Optional[Batch]:
        b = self.get_by_id(db, batch_id)
        if not b:
            return None
        b.batch_number = data["batch_number"]
        b.melt_number = data.get("melt_number")
        b.operator = data.get("operator")
        b.purity = safe_int(data.get("purity"))
        db.flush()

        if files:
            has_default = any(img.is_default for img in b.images)
            images.save_images(
                db, b.id, files, BatchImage, "batch_id",
                set_first_default=not has_default, subfolder="batches",
            )
        return b

    def delete(self, db: Session, batch_id: int):
        db.query(Batch).filter(Batch.id == batch_id).delete()
        db.flush()


# ==========================================
# Package Service (dedicated, with price + is_active)
# ==========================================

class PackageService:
    """Service for PackageType with name, price, is_active + images."""

    def list_all(self, db: Session) -> List[PackageType]:
        return db.query(PackageType).order_by(PackageType.id).all()

    def list_active(self, db: Session) -> List[PackageType]:
        return db.query(PackageType).filter(PackageType.is_active == True).order_by(PackageType.id).all()

    def get_by_id(self, db: Session, item_id: int) -> Optional[PackageType]:
        return db.query(PackageType).filter(PackageType.id == item_id).first()

    def create(self, db: Session, name: str, price: int = 0, is_active: bool = True,
               files: List[UploadFile] = None) -> PackageType:
        item = PackageType(name=name, price=price, is_active=is_active)
        db.add(item)
        db.flush()
        db.refresh(item)
        if files:
            images.save_images(db, item.id, files, PackageTypeImage, "package_id",
                             subfolder="packages")
        return item

    def update(self, db: Session, item_id: int, name: str, price: int = 0,
               is_active: bool = True, files: List[UploadFile] = None) -> Optional[PackageType]:
        item = self.get_by_id(db, item_id)
        if not item:
            return None
        item.name = name
        item.price = price
        item.is_active = is_active
        db.flush()
        if files:
            images.save_images(db, item.id, files, PackageTypeImage, "package_id",
                             set_first_default=False, subfolder="packages")
        return item

    def delete(self, db: Session, item_id: int):
        db.query(PackageType).filter(PackageType.id == item_id).delete()
        db.flush()


# ==========================================
# Service Singletons
# ==========================================

product_service = ProductService()
design_service = SimpleEntityService(CardDesign, CardDesignImage, "design_id", "designs")
package_service = PackageService()
batch_service = BatchService()
