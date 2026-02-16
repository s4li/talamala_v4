"""
Staff Management Service
===========================
CRUD operations for SystemUser (admin/operator) accounts and permissions.
"""

from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from modules.admin.models import SystemUser
from modules.admin.permissions import ALL_PERMISSION_KEYS


class StaffService:

    def list_staff(self, db: Session) -> List[SystemUser]:
        return db.query(SystemUser).order_by(SystemUser.created_at.desc()).all()

    def get_by_id(self, db: Session, staff_id: int) -> Optional[SystemUser]:
        return db.query(SystemUser).filter(SystemUser.id == staff_id).first()

    def get_by_mobile(self, db: Session, mobile: str) -> Optional[SystemUser]:
        return db.query(SystemUser).filter(SystemUser.mobile == mobile).first()

    def create_staff(
        self, db: Session,
        mobile: str, full_name: str,
        role: str = "operator",
        permissions: list = None,
    ) -> SystemUser:
        user = SystemUser(mobile=mobile, full_name=full_name, role=role)
        user.permissions = permissions or []
        db.add(user)
        db.flush()
        return user

    def update_staff(
        self, db: Session, staff_id: int,
        full_name: str = None, role: str = None,
    ) -> Optional[SystemUser]:
        user = self.get_by_id(db, staff_id)
        if not user:
            return None
        if full_name is not None:
            user.full_name = full_name
        if role is not None:
            user.role = role
        db.flush()
        return user

    def update_permissions(
        self, db: Session, staff_id: int, permissions: list,
    ) -> Optional[SystemUser]:
        user = self.get_by_id(db, staff_id)
        if not user:
            return None
        valid = [p for p in permissions if p in ALL_PERMISSION_KEYS]
        user.permissions = valid
        db.flush()
        return user


staff_service = StaffService()
