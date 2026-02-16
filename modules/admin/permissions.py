"""
Admin Permissions Registry
============================
Central registry of all permission keys and their Persian labels.
Used by staff management, sidebar rendering, and route protection.
"""

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
