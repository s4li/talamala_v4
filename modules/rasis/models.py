"""
Rasis POS Integration — Models
================================
Stores receipt data fetched from Rasis POS devices for audit and sale matching.
"""

from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey, Boolean,
    BigInteger, Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from config.database import Base


class RasisReceipt(Base):
    """
    A single receipt item fetched from Rasis POS.
    One row per receipt detail item (flattened from header + detail).
    Links to Bar via product_cbrc → Bar.serial_code.
    """
    __tablename__ = "rasis_receipts"

    id = Column(Integer, primary_key=True)
    dealer_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Receipt header
    receipt_no = Column(BigInteger, nullable=True)          # شماره فاکتور Rasis (ReceiptNo)
    record_version = Column(BigInteger, nullable=True)      # RecordVersion for incremental sync
    factor_tarikh = Column(String, nullable=True)           # تاریخ فاکتور (FactorTarikh)
    total_amount = Column(BigInteger, default=0)            # مجموع مبلغ فاکتور (ریال)
    pay_card = Column(BigInteger, default=0)                # پرداخت کارتی (ریال)
    pay_cash = Column(BigInteger, default=0)                # پرداخت نقدی (ریال)
    payer_mobile = Column(String(15), nullable=True)        # موبایل خریدار (PayerMobile)
    payer_name = Column(String, nullable=True)              # نام خریدار (PayerName)

    # Receipt detail item
    product_cbrc = Column(String, nullable=True, index=True)  # بارکد محصول = serial_code (ProductCbrc)
    product_name = Column(String, nullable=True)              # نام محصول on POS (ProductName)
    item_price = Column(BigInteger, default=0)                # قیمت واحد (Price, ریال)
    item_total = Column(BigInteger, default=0)                # مجموع قیمت آیتم (TotalPrice, ریال)

    # Matching
    bar_id = Column(Integer, ForeignKey("bars.id", ondelete="SET NULL"), nullable=True)
    dealer_sale_id = Column(Integer, ForeignKey("dealer_sales.id", ondelete="SET NULL"), nullable=True)
    raw_data = Column(Text, nullable=True)                  # Full JSON receipt for audit
    processed = Column(Boolean, default=False)              # True = matched & DealerSale created
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    dealer = relationship("User", foreign_keys=[dealer_id])
    bar = relationship("Bar", foreign_keys=[bar_id])
    dealer_sale = relationship("DealerSale", foreign_keys=[dealer_sale_id])
