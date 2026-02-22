"""
Auth Module - Dependencies
===========================
FastAPI dependencies for user authentication and authorization.
These are injected into route handlers via Depends().

NOTE: Unified auth — single User model, single auth_token cookie.
"""

from fastapi import Request, Depends, HTTPException, status
from sqlalchemy.orm import Session

from config.database import get_db
from common.security import decode_token
from modules.user.models import User


def get_current_active_user(request: Request, db: Session = Depends(get_db)):
    """
    Identify the current user from the auth_token cookie.
    Returns User object or None.
    """
    token = request.cookies.get("auth_token")
    if not token:
        return None

    payload = decode_token(token)
    if not payload:
        return None

    mobile = payload.get("sub")
    if not mobile:
        return None

    user = db.query(User).filter(User.mobile == mobile, User.is_active == True).first()
    return user


def require_login(user=Depends(get_current_active_user)):
    """Require any authenticated active user (customer, dealer, or admin). Raises 401 if not logged in."""
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="login_required")
    return user


def require_staff(user=Depends(get_current_active_user)):
    """Only allow staff/admin users. Raises 403 otherwise."""
    if not user or not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="دسترسی غیرمجاز")
    return user


def require_operator_or_admin(user=Depends(get_current_active_user)):
    """Allow both Admins and Operators. Raises 403 otherwise."""
    if not user or not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="دسترسی غیرمجاز")
    return user


def require_dealer(user=Depends(get_current_active_user)):
    """Only allow dealer users. Raises 401 if not authenticated as dealer."""
    if not user or not user.is_dealer:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="login_required")
    return user


def require_super_admin(user=Depends(get_current_active_user)):
    """Only allow full Admins (not operators)."""
    if not user or not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="نیازمند دسترسی مدیر کل")

    if user.admin_role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="نیازمند دسترسی مدیر کل")

    return user


def require_permission(*perm_keys: str, level: str = "view"):
    """
    Factory: returns a dependency that checks granular permissions at a specific level.
    admin_role=='admin' always passes (super admin bypass).

    Levels (hierarchical — each includes all below):
      view   → read-only (list, detail)
      create → view + create new entities
      edit   → create + modify existing entities
      full   → edit + delete + approve/reject + sensitive actions

    Usage:
      user=Depends(require_permission("orders"))                 # default: view
      user=Depends(require_permission("orders", level="edit"))   # edit level
      user=Depends(require_permission("orders", "wallets", level="view"))  # multi-key
    """
    from modules.admin.permissions import PERMISSION_REGISTRY, PERMISSION_LEVEL_LABELS

    def dependency(user=Depends(get_current_active_user)):
        if not user or not user.is_admin:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="login_required")

        # super admin bypasses all
        if user.admin_role == "admin":
            return user

        for key in perm_keys:
            if not user.has_permission(key, level):
                section_label = PERMISSION_REGISTRY.get(key, key)
                level_label = PERMISSION_LEVEL_LABELS.get(level, level)
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"شما دسترسی «{level_label}» به بخش «{section_label}» ندارید",
                )
        return user

    return dependency
