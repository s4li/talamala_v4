"""
TalaMala v4 - Template Configuration
======================================
Jinja2 templates setup with custom filters and global functions.
"""

from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from config.database import SessionLocal
from common.helpers import format_toman, format_weight, format_jdate, format_time_ago, persian_number, format_gold_gram, format_metal_gram

# Initialize templates
TEMPLATE_DIR = "templates"
templates = Jinja2Templates(directory=TEMPLATE_DIR)


# ==========================================
# Template Helper: System Settings
# ==========================================

def get_setting_value(key: str, default: str = "") -> str:
    """
    Fetch a system setting value from DB.
    Used inside Jinja2 templates as a global function.
    Creates its own DB session (templates don't have access to request's session).
    """
    db = SessionLocal()
    try:
        # Import here to avoid circular imports at module load time
        from modules.admin.models import SystemSetting
        setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()
        return setting.value if setting else default
    finally:
        db.close()


def get_setting_from_db(db: Session, key: str, default: str = "") -> str:
    """Fetch a system setting using an existing DB session (for use in routes)."""
    from modules.admin.models import SystemSetting
    setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    return setting.value if setting else default


def parse_int_setting(db: Session, key: str, default: int = 0) -> int:
    """Fetch a system setting and parse it as integer."""
    val = get_setting_from_db(db, key, str(default))
    try:
        return int(str(val).strip())
    except (ValueError, TypeError):
        return default


# ==========================================
# Register Filters & Globals
# ==========================================

# Filters (usage in template: {{ value | toman }})
templates.env.filters["toman"] = format_toman
templates.env.filters["weight_format"] = format_weight
templates.env.filters["jdate"] = format_jdate
templates.env.filters["persian_number"] = persian_number
templates.env.filters["gold_gram"] = format_gold_gram
templates.env.filters["metal_gram"] = format_metal_gram
templates.env.filters["time_ago"] = format_time_ago
templates.env.filters["purity"] = lambda v: str(v).rstrip('0').rstrip('.') if v else "—"

# Persian label mapping for enum values used in dropdowns/filters
_FA_LABELS = {
    # BarStatus
    "Raw": "خام", "Assigned": "اختصاص", "Reserved": "رزرو", "Sold": "فروخته",
    # OrderStatus
    "Pending": "در انتظار پرداخت", "Paid": "پرداخت شده", "Cancelled": "لغو شده",
    # DeliveryStatus
    "Preparing": "آماده‌سازی", "Shipped": "ارسال شده", "Delivered": "تحویل شده",
    # DeliveryMethod
    "Pickup": "حضوری", "Postal": "پستی",
}
templates.env.filters["fa_label"] = lambda v: _FA_LABELS.get(str(v), str(v)) if v else "—"

# Ticket category label mapping (for department transfer dropdown)
_TICKET_CAT_LABELS = {
    "Financial": "مالی", "Technical": "فنی", "Sales": "فروش",
    "Complaints": "شکایات", "Other": "سایر",
}
templates.env.filters["ticket_category_label"] = lambda v: _TICKET_CAT_LABELS.get(str(v), str(v))

# Static asset version for cache busting (bump when CSS/JS changes)
STATIC_VERSION = "1.3"
templates.env.globals["STATIC_VER"] = STATIC_VERSION

# Globals (usage in template: {{ get_setting_value('key') }})
templates.env.globals["get_setting_value"] = get_setting_value

# Flash messages: available in templates via get_flashed_messages(request)
from common.flash import get_flashed_messages
templates.env.globals["get_flashed_messages"] = get_flashed_messages
