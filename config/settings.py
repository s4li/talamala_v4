"""
TalaMala v4 - Centralized Configuration
========================================
All environment variables and constants are loaded here.
No other module should call os.getenv() directly.
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()


# ==========================================
# 🗄️ Database
# ==========================================
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME")

if not all([DB_USER, DB_PASSWORD, DB_HOST, DB_NAME]):
    print("[ERROR] Critical: Database config missing in .env (DB_USER, DB_PASSWORD, DB_HOST, DB_NAME)")
    sys.exit(1)

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


# ==========================================
# 🔐 Security
# ==========================================
SECRET_KEY = os.getenv("SECRET_KEY")
CUSTOMER_SECRET_KEY = os.getenv("CUSTOMER_SECRET_KEY")
DEALER_SECRET_KEY = os.getenv("DEALER_SECRET_KEY", os.getenv("CUSTOMER_SECRET_KEY", "dealer-fallback-key"))
OTP_SECRET = os.getenv("OTP_SECRET")

if not all([SECRET_KEY, CUSTOMER_SECRET_KEY, OTP_SECRET]):
    print("[ERROR] Critical: Security keys missing in .env (SECRET_KEY, CUSTOMER_SECRET_KEY, OTP_SECRET)")
    sys.exit(1)

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"
COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE", "lax")
CSRF_ENABLED = os.getenv("CSRF_ENABLED", "true").lower() == "true"


# ==========================================
# 📱 SMS Providers
# ==========================================
# Kavenegar
SMS_API_KEY = os.getenv("SMS_API_KEY", "")

# sms.ir (default provider)
SMSIR_API_KEY = os.getenv("SMSIR_API_KEY", "")
SMSIR_LINE_NUMBER = os.getenv("SMSIR_LINE_NUMBER", "")
SMSIR_TEMPLATE_ID = os.getenv("SMSIR_TEMPLATE_ID", "")  # optional: if empty, uses bulk send


# ==========================================
# 💳 Payment Gateways
# ==========================================
ZIBAL_MERCHANT = os.getenv("ZIBAL_MERCHANT", "zibal")
SEPEHR_TERMINAL_ID = int(os.getenv("SEPEHR_TERMINAL_ID") or "99079327")
TOP_USERNAME = os.getenv("TOP_USERNAME", "")
TOP_PASSWORD = os.getenv("TOP_PASSWORD", "")
PARSIAN_PIN = os.getenv("PARSIAN_PIN", "")


# ==========================================
# 🔐 Shahkar Identity Verification (Zohal)
# ==========================================
SHAHKAR_API_TOKEN = os.getenv("SHAHKAR_API_TOKEN", "")


# ==========================================
# 🖥️ Rasis POS Integration
# ==========================================
RASIS_API_URL = os.getenv("RASIS_API_URL", "https://mttestapi.rasisclub.ir")
RASIS_USERNAME = os.getenv("RASIS_USERNAME", "")
RASIS_PASSWORD = os.getenv("RASIS_PASSWORD", "")


# ==========================================
# 📁 File Upload
# ==========================================
UPLOAD_DIR = "static/uploads"
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
DEFAULT_IMAGE_MAX_SIZE = (800, 800)


# ==========================================
# 🔧 App
# ==========================================
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
MAINTENANCE_MODE = os.getenv("MAINTENANCE_MODE", "false").lower() == "true"
MAINTENANCE_SECRET = os.getenv("MAINTENANCE_SECRET", "")

# OTP Settings
OTP_LENGTH = 6
OTP_EXPIRE_MINUTES = 5
OTP_MAX_ATTEMPTS = 3
OTP_RATE_LIMIT_WINDOW = 10  # minutes

# Reservation
RESERVATION_EXPIRE_MINUTES = 15

# Base URL for callbacks
BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000")
