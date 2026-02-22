"""
Auth Module - Service Layer
=============================
Business logic for OTP generation, verification, and user registration.

NOTE: Unified auth — single User model, single token type.
"""

import secrets
from datetime import timedelta
from typing import Tuple

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from common.helpers import now_utc
from common.security import (
    hash_otp, generate_otp, check_otp_rate_limit, check_otp_verify_rate_limit,
    create_token,
)
from common.exceptions import OTPError, AuthenticationError
from config.settings import OTP_EXPIRE_MINUTES
from modules.user.models import User


class AuthService:
    """Handles all authentication logic: OTP send, verify, and token creation."""

    def find_or_create_user(
        self, db: Session, mobile: str,
        first_name: str = "", last_name: str = "",
        ref_code: str = "", profile_data: dict = None,
    ) -> User:
        """
        Find existing user by mobile. If not found, create a new customer user.

        Returns:
            User object
        """
        profile_data = profile_data or {}

        # Check existing user (any role)
        user = db.query(User).filter(User.mobile == mobile).first()
        if user:
            return user

        # Create new customer user
        try:
            # Use real national_id from registration, or generate guest placeholder
            national_id = profile_data.get("national_id", "").strip()
            if not national_id:
                national_id = f"GUEST_{secrets.token_hex(4)}_{mobile}"

            # Resolve referral code to referrer ID
            referred_by = None
            if ref_code:
                referrer = db.query(User).filter(User.referral_code == ref_code).first()
                if referrer:
                    referred_by = referrer.id

            user = User(
                mobile=mobile,
                first_name=first_name or "کاربر",
                last_name=last_name or "مهمان",
                national_id=national_id,
                referred_by=referred_by,
            )

            # Set profile fields from registration
            if profile_data:
                user.birth_date = profile_data.get("birth_date") or None
                user.customer_type = profile_data.get("customer_type", "real")
                user.postal_code = profile_data.get("postal_code") or None
                user.address = profile_data.get("address") or None
                user.phone = profile_data.get("phone") or None
                if user.customer_type == "legal":
                    user.company_name = profile_data.get("company_name") or None
                    user.economic_code = profile_data.get("economic_code") or None

            db.add(user)
            db.flush()
            db.refresh(user)
            return user
        except IntegrityError:
            db.rollback()
            # Race condition: another request created this user
            user = db.query(User).filter(User.mobile == mobile).first()
            if user:
                return user
            raise AuthenticationError("خطای ثبت نام. لطفا مجدد تلاش کنید.")

    def send_otp(
        self, db: Session, mobile: str,
        first_name: str = "", last_name: str = "",
        ref_code: str = "", profile_data: dict = None,
    ) -> Tuple[str, str]:
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

        user = self.find_or_create_user(
            db, mobile, first_name=first_name, last_name=last_name,
            ref_code=ref_code, profile_data=profile_data or {},
        )

        # Generate OTP
        otp_raw = generate_otp()

        # Store hashed OTP
        user.otp_code = hash_otp(mobile, otp_raw)
        user.otp_expiry = now_utc() + timedelta(minutes=OTP_EXPIRE_MINUTES)
        db.flush()

        # Display name for SMS
        display_name = user.first_name or "کاربر"

        return otp_raw, display_name.replace(" ", "_")

    def verify_otp(self, db: Session, mobile: str, code: str) -> Tuple[str, str]:
        """
        Verify OTP code for a mobile number.

        Returns:
            (token, redirect_url)

        Raises:
            AuthenticationError if OTP is invalid or expired
        """
        mobile = mobile.strip()
        code = code.strip()
        now = now_utc()

        # Rate limit verification attempts (brute-force protection)
        if not check_otp_verify_rate_limit(mobile):
            raise AuthenticationError("⛔ تعداد تلاش بیش از حد مجاز! ۱۰ دقیقه صبر کنید.")

        user = db.query(User).filter(User.mobile == mobile).first()
        if not user:
            raise AuthenticationError("❌ کد اشتباه یا منقضی شده است.")

        if not user.is_active:
            raise AuthenticationError("❌ حساب کاربری شما غیرفعال شده است.")

        if not user.otp_expiry or user.otp_expiry < now:
            raise AuthenticationError("❌ کد اشتباه یا منقضی شده است.")

        if user.otp_code != hash_otp(mobile, code):
            raise AuthenticationError("❌ کد اشتباه یا منقضی شده است.")

        # Clear OTP
        user.otp_code = None
        user.otp_expiry = None
        db.flush()

        # Create unified token
        token = create_token({"sub": user.mobile})

        # Determine redirect URL based on highest role
        redirect_url = user.primary_redirect

        return token, redirect_url


# Singleton instance
auth_service = AuthService()
