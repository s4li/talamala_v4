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


def require_customer(user=Depends(get_current_active_user)):
    """Only allow customer users. Raises 401 if not authenticated or not a customer."""
    if not user or not user.is_customer:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="login_required")
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


def require_permission(*perm_keys: str):
    """
    Factory: returns a dependency that checks granular permissions.
    admin_role=='admin' always passes (super admin bypass).

    Usage: user=Depends(require_permission("orders"))
    """
    from modules.admin.permissions import PERMISSION_REGISTRY

    def dependency(user=Depends(get_current_active_user)):
        if not user or not user.is_admin:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="login_required")

        # super admin bypasses all
        if user.admin_role == "admin":
            return user

        for key in perm_keys:
            if not user.has_permission(key):
                label = PERMISSION_REGISTRY.get(key, key)
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"شما دسترسی به بخش «{label}» ندارید",
                )
        return user

    return dependency
