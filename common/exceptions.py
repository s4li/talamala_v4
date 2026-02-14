"""
TalaMala v4 - Custom Exceptions
================================
Business-level exceptions that can be caught and converted to HTTP responses.
"""

from fastapi import HTTPException, status


class TalaMalaError(Exception):
    """Base exception for all business logic errors."""
    def __init__(self, message: str = "خطای سیستمی رخ داد."):
        self.message = message
        super().__init__(self.message)


class AuthenticationError(TalaMalaError):
    """Raised when authentication fails."""
    pass


class AuthorizationError(TalaMalaError):
    """Raised when user lacks permission."""
    pass


class OTPError(TalaMalaError):
    """Raised for OTP-related issues (expired, invalid, rate limited)."""
    pass


class InsufficientBalanceError(TalaMalaError):
    """Raised when wallet balance is not enough."""
    def __init__(self):
        super().__init__("موجودی حساب کافی نیست.")


class InsufficientInventoryError(TalaMalaError):
    """Raised when product inventory is not enough."""
    def __init__(self, product_name: str = ""):
        msg = f"موجودی کافی نیست: {product_name}" if product_name else "موجودی کافی نیست."
        super().__init__(msg)


class DuplicateError(TalaMalaError):
    """Raised for unique constraint violations at the business level."""
    pass


class PaymentError(TalaMalaError):
    """Raised for payment gateway errors."""
    pass


class NotFoundError(TalaMalaError):
    """Raised when a requested resource doesn't exist."""
    pass


def raise_http(error: TalaMalaError, status_code: int = 400):
    """Convert a business exception to an HTTP exception."""
    raise HTTPException(status_code=status_code, detail=error.message)
