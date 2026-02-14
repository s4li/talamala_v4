"""
Auth Module - Service Layer
=============================
Business logic for OTP generation, verification, and user registration.
"""

import secrets
from datetime import timedelta
from typing import Optional, Tuple

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from common.helpers import now_utc
from common.security import (
    hash_otp, generate_otp, check_otp_rate_limit,
    create_staff_token, create_customer_token, create_dealer_token,
)
from common.exceptions import OTPError, AuthenticationError
from config.settings import OTP_EXPIRE_MINUTES
from modules.admin.models import SystemUser
from modules.customer.models import Customer
from modules.dealer.models import Dealer


class AuthService:
    """Handles all authentication logic: OTP send, verify, and token creation."""

    def find_or_create_user(self, db: Session, mobile: str) -> Tuple[object, str]:
        """
        Find existing user (staff, dealer, or customer) by mobile.
        If not found, create a guest customer.

        Returns:
            (user_object, user_type)  where user_type is 'staff', 'dealer', or 'customer'
        """
        # Check staff first
        system_user = db.query(SystemUser).filter(SystemUser.mobile == mobile).first()
        if system_user:
            return system_user, "staff"

        # Check dealer
        dealer = db.query(Dealer).filter(Dealer.mobile == mobile, Dealer.is_active == True).first()
        if dealer:
            return dealer, "dealer"

        # Check existing customer
        customer = db.query(Customer).filter(Customer.mobile == mobile).first()
        if customer:
            return customer, "customer"

        # Create new guest customer
        try:
            guest_nid = f"GUEST_{secrets.token_hex(4)}_{mobile}"
            customer = Customer(
                mobile=mobile,
                first_name="کاربر",
                last_name="مهمان",
                national_id=guest_nid,
            )
            db.add(customer)
            db.commit()
            db.refresh(customer)
            return customer, "customer"
        except IntegrityError:
            db.rollback()
            # Race condition: another request created this user
            customer = db.query(Customer).filter(Customer.mobile == mobile).first()
            if customer:
                return customer, "customer"
            raise AuthenticationError("خطای ثبت نام. لطفا مجدد تلاش کنید.")

    def send_otp(self, db: Session, mobile: str) -> Tuple[str, str]:
        """
        Generate and store OTP for a mobile number.

        Returns:
            (otp_raw, display_name) - otp_raw for SMS sending, display_name for SMS template

        Raises:
            OTPError if rate limited
        """
        mobile = mobile.strip()

        # Rate limit check
        if not check_otp_rate_limit(mobile):
            raise OTPError("⛔ درخواست زیاد! ۱۰ دقیقه صبر کنید.")

        user, user_type = self.find_or_create_user(db, mobile)

        # Generate OTP
        otp_raw = generate_otp()

        # Store hashed OTP
        user.otp_code = hash_otp(mobile, otp_raw)
        user.otp_expiry = now_utc() + timedelta(minutes=OTP_EXPIRE_MINUTES)
        db.commit()

        # Display name for SMS
        if user_type == "staff":
            display_name = user.full_name
        elif user_type == "dealer":
            display_name = user.full_name
        else:
            display_name = user.first_name or "کاربر"

        return otp_raw, display_name.replace(" ", "_")

    def verify_otp(self, db: Session, mobile: str, code: str) -> Tuple[str, str, str]:
        """
        Verify OTP code for a mobile number.

        Returns:
            (token, cookie_name, redirect_url)

        Raises:
            AuthenticationError if OTP is invalid or expired
        """
        mobile = mobile.strip()
        code = code.strip()
        now = now_utc()

        # Check Staff
        system_user = db.query(SystemUser).filter(SystemUser.mobile == mobile).first()
        if system_user and system_user.otp_expiry and system_user.otp_expiry >= now:
            if system_user.otp_code == hash_otp(mobile, code):
                system_user.otp_code = None
                system_user.otp_expiry = None
                db.commit()
                token = create_staff_token({"sub": system_user.mobile, "type": "staff"})
                return token, "auth_token", "/admin/dashboard"

        # Check Dealer
        dealer = db.query(Dealer).filter(Dealer.mobile == mobile, Dealer.is_active == True).first()
        if dealer and dealer.otp_expiry and dealer.otp_expiry >= now:
            if dealer.otp_code == hash_otp(mobile, code):
                dealer.otp_code = None
                dealer.otp_expiry = None
                db.commit()
                token = create_dealer_token({"sub": dealer.mobile, "type": "dealer"})
                return token, "dealer_token", "/dealer/dashboard"

        # Check Customer
        customer = db.query(Customer).filter(Customer.mobile == mobile).first()
        if customer and customer.otp_expiry and customer.otp_expiry >= now:
            if customer.otp_code == hash_otp(mobile, code):
                customer.otp_code = None
                customer.otp_expiry = None
                db.commit()
                token = create_customer_token({"sub": customer.mobile, "type": "customer"})
                return token, "customer_token", "/"

        raise AuthenticationError("❌ کد اشتباه یا منقضی شده است.")


# Singleton instance
auth_service = AuthService()
