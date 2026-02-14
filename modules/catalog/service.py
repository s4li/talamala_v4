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
from common.helpers import safe_int
from modules.catalog.models import (
    Product, ProductImage,
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
            db.commit()
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
        db.commit()
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
        db.commit()
        return parent_id


# Singleton
images = ImageManager()


# ==========================================
# Product Service
# ==========================================

class ProductService:

    def list_all(self, db: Session) -> List[Product]:
        return db.query(Product).order_by(Product.id.desc()).all()

    def get_by_id(self, db: Session, product_id: int) -> Optional[Product]:
        return db.query(Product).filter(Product.id == product_id).first()

    def create(self, db: Session, data: dict, files: List[UploadFile] = None) -> Product:
        product = Product(
            name=data["name"],
            weight=data["weight"],
            purity=safe_int(data.get("purity", "750")) or 750,
            category_id=data.get("category_id"),
            design=data.get("design"),
            card_design_id=data.get("card_design_id"),
            package_type_id=data.get("package_type_id"),
            wage=data.get("wage", 0),
            is_wage_percent=data.get("is_wage_percent", True),
            profit_percent=data.get("profit_percent", 7),
            commission_percent=data.get("commission_percent", 0),
            stone_price=safe_int(data.get("stone_price", "0")) or 0,
            accessory_cost=safe_int(data.get("accessory_cost", "0")) or 0,
            accessory_profit_percent=data.get("accessory_profit_percent", 15),
            is_active=data.get("is_active", True),
        )
        db.add(product)
        db.commit()
        db.refresh(product)

        if files:
            images.save_images(db, product.id, files, ProductImage, "product_id", subfolder="products")

        return product

    def update(self, db: Session, product_id: int, data: dict, files: List[UploadFile] = None) -> Optional[Product]:
        p = self.get_by_id(db, product_id)
        if not p:
            return None

        p.name = data["name"]
        p.weight = data["weight"]
        p.purity = safe_int(data.get("purity", "750")) or 750
        p.category_id = data.get("category_id")
        p.design = data.get("design")
        p.card_design_id = data.get("card_design_id")
        p.package_type_id = data.get("package_type_id")
        p.wage = data.get("wage", 0)
        p.is_wage_percent = data.get("is_wage_percent", False)
        p.profit_percent = data.get("profit_percent", 7)
        p.commission_percent = data.get("commission_percent", 0)
        p.stone_price = safe_int(data.get("stone_price", "0")) or 0
        p.accessory_cost = safe_int(data.get("accessory_cost", "0")) or 0
        p.accessory_profit_percent = data.get("accessory_profit_percent", 15)
        p.is_active = data.get("is_active", False)
        db.commit()

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
        db.commit()
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
        db.commit()

        if files:
            images.save_images(db, item.id, files, self.image_model, self.fk_field,
                             set_first_default=False, subfolder=self.subfolder)
        return item

    def delete(self, db: Session, item_id: int):
        db.query(self.model).filter(self.model.id == item_id).delete()
        db.commit()


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
        db.commit()
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
        db.commit()

        if files:
            has_default = any(img.is_default for img in b.images)
            images.save_images(
                db, b.id, files, BatchImage, "batch_id",
                set_first_default=not has_default, subfolder="batches",
            )
        return b

    def delete(self, db: Session, batch_id: int):
        db.query(Batch).filter(Batch.id == batch_id).delete()
        db.commit()


# ==========================================
# Service Singletons
# ==========================================

product_service = ProductService()
design_service = SimpleEntityService(CardDesign, CardDesignImage, "design_id", "designs")
package_service = SimpleEntityService(PackageType, PackageTypeImage, "package_id", "packages")
batch_service = BatchService()
