"""
Trade Guard — Per-metal, per-channel trade toggle system.
==========================================================
Allows admin to independently enable/disable trading for each metal type
across different channels (shop, wallet, POS, B2B, buyback).

Usage:
    from modules.pricing.trade_guard import require_trade_enabled, is_trade_enabled

    # Raise ValueError if disabled (same pattern as require_fresh_price)
    require_trade_enabled(db, "gold", "wallet_buy")

    # Boolean check (for UI indicators)
    if is_trade_enabled(db, "silver", "shop"):
        ...
"""

from sqlalchemy.orm import Session
from common.templating import get_setting_from_db


# All valid channels
TRADE_CHANNELS = [
    "shop", "wallet_buy", "wallet_sell",
    "dealer_pos", "customer_pos",
    "b2b_order", "buyback",
]

# Persian labels for error messages
_CHANNEL_LABELS = {
    "shop": "خرید از فروشگاه",
    "wallet_buy": "خرید از کیف پول",
    "wallet_sell": "فروش از کیف پول",
    "dealer_pos": "فروش از پوز نماینده",
    "customer_pos": "فروش از پوز فروشگاهی",
    "b2b_order": "سفارش عمده",
    "buyback": "بازخرید",
}


def is_trade_enabled(db: Session, metal_type: str, channel: str) -> bool:
    """Check if trading is enabled for a metal+channel combo.

    Args:
        metal_type: "gold" or "silver"
        channel: one of TRADE_CHANNELS
    Returns:
        True if enabled (default True if setting not found)
    """
    key = f"{metal_type}_{channel}_enabled"
    val = get_setting_from_db(db, key, "true")
    return val.strip().lower() == "true"


def require_trade_enabled(db: Session, metal_type: str, channel: str):
    """Raise ValueError if trading is disabled for this metal+channel.

    Same pattern as require_fresh_price() — routes catch ValueError
    and show user-friendly error message.
    """
    if not is_trade_enabled(db, metal_type, channel):
        from modules.wallet.models import PRECIOUS_METALS
        label = PRECIOUS_METALS.get(metal_type, {}).get("label", metal_type)
        ch_label = _CHANNEL_LABELS.get(channel, channel)
        raise ValueError(f"{ch_label} {label} در حال حاضر غیرفعال است")


def get_all_trade_status(db: Session) -> dict:
    """Get all trade toggle statuses for admin settings page.

    Returns:
        {"gold_shop_enabled": True, "gold_wallet_buy_enabled": False, ...}
    """
    from modules.wallet.models import PRECIOUS_METALS
    result = {}
    for metal_type in PRECIOUS_METALS:
        for channel in TRADE_CHANNELS:
            key = f"{metal_type}_{channel}_enabled"
            result[key] = is_trade_enabled(db, metal_type, channel)
    return result
