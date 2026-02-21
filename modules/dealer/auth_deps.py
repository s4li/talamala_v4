"""
Dealer API Key Authentication Dependency
==========================================
Shared dependency for authenticating dealers via X-API-Key header.
Used by both dealer API routes and POS API routes.
"""

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from config.database import get_db
from modules.user.models import User
from modules.dealer.service import dealer_service


def get_dealer_by_api_key(
    x_api_key: str = Header(..., alias="X-API-Key"),
    db: Session = Depends(get_db),
) -> User:
    """Authenticate dealer via X-API-Key header."""
    dealer = dealer_service.get_dealer_by_api_key(db, x_api_key)
    if not dealer:
        raise HTTPException(
            status_code=401,
            detail={"success": False, "error": "کلید API نامعتبر"},
        )
    return dealer