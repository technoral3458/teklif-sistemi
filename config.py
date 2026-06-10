import os

APP_NAME = "B2B Teklif Sistemi"
APP_ICON = "⚙️"
VERSION = "2.0.0"
SERVICE_NAME = "ersanb2b"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
IMAGES_DIR = os.path.join(BASE_DIR, "images")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(IMAGES_DIR, exist_ok=True)

FACTORY_DB = os.path.join(DATA_DIR, "factory_data.db")
USERS_DB = os.path.join(DATA_DIR, "users.db")

ALLOWED_IMAGE_TYPES = ["png", "jpg", "jpeg", "webp"]
MAX_IMAGE_MB = 5

SMTP_SERVER = os.getenv("SMTP_SERVER", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
SMTP_FROM = os.getenv("SMTP_FROM", "")

DEFAULT_ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@example.com")
DEFAULT_ADMIN_PASS = os.getenv("ADMIN_PASS", "Admin123!")
DEFAULT_ADMIN_COMPANY = os.getenv("ADMIN_COMPANY", "Merkez")

CURRENCIES = ["USD", "EUR", "TRY", "RMB"]
DEFAULT_CURRENCY = "USD"

SUPPORTED_LANGS = ["tr", "en", "zh"]
DEFAULT_LANG = "tr"

QTY_TYPES = ["MANUAL", "FIXED_1", "PER_MACHINE"]
OPTION_SCOPES = ["GLOBAL", "MODEL_SPECIFIC"]

OFFER_STATUSES = ["Beklemede", "Onaylandı", "Reddedildi", "Sipariş Verildi", "İptal"]

ROLES = {
    "admin": "Sistem Yöneticisi",
    "manufacturer": "Üretici",
    "dealer": "Bayi",
}
