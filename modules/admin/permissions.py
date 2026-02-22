"""
Admin Permissions Registry
============================
Central registry of all permission keys, hierarchical levels, and their Persian labels.
Used by staff management, sidebar rendering, and route protection.

Levels (each includes all below):
  view   → GET routes only (list, detail)
  create → view + POST routes that create new entities
  edit   → create + POST routes that modify existing entities
  full   → edit + POST routes that delete + approve/reject + sensitive actions
"""

# --- Hierarchical levels (ordered: each includes all below) ---

PERMISSION_LEVELS = ["view", "create", "edit", "full"]

PERMISSION_LEVEL_LABELS = {
    "view":   "نمایش",
    "create": "ایجاد",
    "edit":   "ویرایش",
    "full":   "کامل",
}

# --- Section registry ---

PERMISSION_REGISTRY = {
    "dashboard":  "داشبورد",
    "products":   "محصولات و کاتالوگ",
    "batches":    "بچ / ذوب",
    "inventory":  "شمش‌ها (موجودی)",
    "orders":     "سفارشات",
    "customers":  "مدیریت کاربران",
    "wallets":    "کیف پول‌ها و برداشت",
    "coupons":    "کوپن‌ها",
    "dealers":    "نمایندگان",
    "tickets":    "تیکت‌های پشتیبانی",
    "logs":       "لاگ درخواست‌ها",
    "settings":   "تنظیمات سیستم",
    "staff":      "مدیریت ادمین‌ها",
}

ALL_PERMISSION_KEYS = list(PERMISSION_REGISTRY.keys())


# --- Level helpers ---

def level_index(level: str) -> int:
    """Return numeric index for a level. Higher = more access. Returns -1 for invalid."""
    try:
        return PERMISSION_LEVELS.index(level)
    except ValueError:
        return -1


def has_level(granted_level: str, required_level: str) -> bool:
    """Check if granted_level >= required_level in the hierarchy."""
    return level_index(granted_level) >= level_index(required_level)
