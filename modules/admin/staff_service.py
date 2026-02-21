"""
Staff Management Service
===========================
CRUD operations for admin/operator users (User with is_admin=True) and permissions.
"""

from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from modules.user.models import User
from modules.admin.permissions import ALL_PERMISSION_KEYS


class StaffService:

    def list_staff(self, db: Session) -> List[User]:
        return (
            db.query(User)
            .filter(User.is_admin == True)
            .order_by(User.created_at.desc())
            .all()
        )

    def get_by_id(self, db: Session, staff_id: int) -> Optional[User]:
        return (
            db.query(User)
            .filter(User.id == staff_id, User.is_admin == True)
            .first()
        )

    def get_by_mobile(self, db: Session, mobile: str) -> Optional[User]:
        return (
            db.query(User)
            .filter(User.mobile == mobile, User.is_admin == True)
            .first()
        )

    def create_staff(
        self, db: Session,
        mobile: str, full_name: str,
        role: str = "operator",
        permissions: list = None,
    ) -> User:
        # Check if user with this mobile already exists
        existing = db.query(User).filter(User.mobile == mobile).first()
        if existing:
            # Promote existing user to admin
            existing.is_admin = True
            existing.admin_role = role
            existing.first_name = existing.first_name or full_name.split()[0] if full_name else existing.first_name
            existing.last_name = existing.last_name or " ".join(full_name.split()[1:]) if full_name and len(full_name.split()) > 1 else existing.last_name
            existing.permissions = permissions or []
            db.flush()
            return existing

        # Parse full_name into first/last
        parts = full_name.split() if full_name else []
        first = parts[0] if parts else ""
        last = " ".join(parts[1:]) if len(parts) > 1 else ""

        user = User(
            mobile=mobile,
            first_name=first,
            last_name=last,
            is_admin=True,
            admin_role=role,
        )
        user.permissions = permissions or []
        db.add(user)
        db.flush()
        return user

    def update_staff(
        self, db: Session, staff_id: int,
        full_name: str = None, role: str = None,
    ) -> Optional[User]:
        user = self.get_by_id(db, staff_id)
        if not user:
            return None
        if full_name is not None:
            parts = full_name.split() if full_name else []
            user.first_name = parts[0] if parts else ""
            user.last_name = " ".join(parts[1:]) if len(parts) > 1 else ""
        if role is not None:
            user.admin_role = role
        db.flush()
        return user

    def update_permissions(
        self, db: Session, staff_id: int, permissions: list,
    ) -> Optional[User]:
        user = self.get_by_id(db, staff_id)
        if not user:
            return None
        valid = [p for p in permissions if p in ALL_PERMISSION_KEYS]
        user.permissions = valid
        db.flush()
        return user


staff_service = StaffService()
