"""
Auth Module - Dependencies
===========================
FastAPI dependencies for user authentication and authorization.
These are injected into route handlers via Depends().
"""

from fastapi import Request, Depends, HTTPException, status
from sqlalchemy.orm import Session

from config.database import get_db
from common.security import decode_staff_token, decode_customer_token, decode_dealer_token
from modules.admin.models import SystemUser
from modules.customer.models import Customer
from modules.dealer.models import Dealer


def get_current_active_user(request: Request, db: Session = Depends(get_db)):
    """
    Identify the current user from cookies.
    Returns SystemUser (with is_staff=True) or Customer (with is_staff=False) or None.

    This is the main auth dependency - most routes use this.
    """
    # 1. Check for staff/admin token
    admin_token = request.cookies.get("auth_token")
    if admin_token:
        payload = decode_staff_token(admin_token)
        if payload:
            mobile = payload.get("sub")
            if mobile:
                user = db.query(SystemUser).filter(SystemUser.mobile == mobile).first()
                if user:
                    setattr(user, "is_staff", True)
                    return user

    # 2. Check for dealer token
    dealer_token = request.cookies.get("dealer_token")
    if dealer_token:
        payload = decode_dealer_token(dealer_token)
        if payload:
            mobile = payload.get("sub")
            if mobile:
                user = db.query(Dealer).filter(Dealer.mobile == mobile, Dealer.is_active == True).first()
                if user:
                    setattr(user, "is_staff", False)
                    setattr(user, "is_dealer", True)
                    return user

    # 3. Check for customer token
    cust_token = request.cookies.get("customer_token")
    if cust_token:
        payload = decode_customer_token(cust_token)
        if payload:
            mobile = payload.get("sub")
            if mobile:
                user = db.query(Customer).filter(Customer.mobile == mobile, Customer.is_active == True).first()
                if user:
                    setattr(user, "is_staff", False)
                    setattr(user, "is_dealer", False)
                    return user

    return None


def require_staff(user=Depends(get_current_active_user)):
    """Only allow staff/admin users. Raises 403 otherwise."""
    if not user or not getattr(user, "is_staff", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="دسترسی غیرمجاز")
    return user


def require_customer(user=Depends(get_current_active_user)):
    """Only allow customer users. Raises 401 if not authenticated."""
    if not user or getattr(user, "is_staff", False) or getattr(user, "is_dealer", False):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="login_required")
    return user


def require_operator_or_admin(user=Depends(get_current_active_user)):
    """Allow both Admins and Operators. Raises 403 otherwise."""
    if not user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="احراز هویت نشده")

    # Admin has full access
    if getattr(user, "is_staff", False):
        return user

    # Operator also allowed
    if hasattr(user, "role") and user.role == "operator":
        return user

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="دسترسی غیرمجاز")


def require_dealer(user=Depends(get_current_active_user)):
    """Only allow dealer users. Raises 401 if not authenticated as dealer."""
    if not user or not getattr(user, "is_dealer", False):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="login_required")
    return user


def require_super_admin(user=Depends(get_current_active_user)):
    """Only allow full Admins (not operators)."""
    if not user or not getattr(user, "is_staff", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="نیازمند دسترسی مدیر کل")

    if hasattr(user, "role") and user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="نیازمند دسترسی مدیر کل")

    return user
