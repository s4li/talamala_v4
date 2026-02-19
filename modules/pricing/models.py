"""
Pricing Module - Models
========================
Asset: Per-asset price tracking with staleness guard and auto-update support.
"""

from sqlalchemy import Column, Integer, String, BigInteger, Boolean, DateTime
from sqlalchemy.sql import func

from config.database import Base

# Asset code constants
GOLD_18K = "gold_18k"
SILVER = "silver"


class Asset(Base):
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True)
    asset_code = Column(String(30), unique=True, nullable=False)
    asset_label = Column(String(100), nullable=False)
    price_per_gram = Column(BigInteger, nullable=False, default=0)
    stale_after_minutes = Column(Integer, nullable=False, default=15)
    auto_update = Column(Boolean, default=True)
    update_interval_minutes = Column(Integer, nullable=False, default=5)
    source_url = Column(String, nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_by = Column(String, nullable=True)

    @property
    def is_fresh(self) -> bool:
        """Check if price is within staleness threshold."""
        if not self.updated_at:
            return False
        from common.helpers import now_utc
        elapsed = (now_utc() - self.updated_at).total_seconds() / 60
        return elapsed <= self.stale_after_minutes

    @property
    def minutes_since_update(self) -> float:
        """Minutes since last price update."""
        if not self.updated_at:
            return float("inf")
        from common.helpers import now_utc
        return (now_utc() - self.updated_at).total_seconds() / 60

    def __repr__(self):
        return f"<Asset {self.asset_code}={self.price_per_gram}>"
