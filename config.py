import os

APP_NAME    = "B2B Teklif Sistemi"
VERSION     = "3.0.0"
SECRET_KEY  = os.getenv("SECRET_KEY", "change-this-secret-in-production-32chars!")

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
DATA_DIR    = os.path.join(BASE_DIR, "data")
IMAGES_DIR  = os.path.join(BASE_DIR, "static", "img", "uploads")

os.makedirs(DATA_DIR,   exist_ok=True)
os.makedirs(IMAGES_DIR, exist_ok=True)

FACTORY_DB = os.path.join(DATA_DIR, "factory.db")
USERS_DB   = os.path.join(DATA_DIR, "users.db")

MAX_IMAGE_MB        = 5
ALLOWED_IMAGE_EXTS  = {"png", "jpg", "jpeg", "webp"}

ADMIN_EMAIL   = os.getenv("ADMIN_EMAIL",   "admin@example.com")
ADMIN_PASS    = os.getenv("ADMIN_PASS",    "Admin123!")
ADMIN_COMPANY = os.getenv("ADMIN_COMPANY", "Yönetim")

SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
SMTP_FROM = os.getenv("SMTP_FROM", os.getenv("ADMIN_EMAIL", "noreply@example.com"))

CURRENCIES       = ["USD", "EUR", "TRY", "RMB"]
OFFER_STATUSES   = ["Beklemede", "Onaylandı", "Reddedildi", "Sipariş Verildi", "İptal"]
PAYMENT_METHODS  = ["Nakit", "Banka Havalesi / EFT", "Çek", "Senet", "Kredi Kartı", "Diğer"]
QTY_TYPES        = ["MANUAL", "FIXED_1", "PER_MACHINE"]
OPTION_SCOPES    = ["GLOBAL", "MODEL_SPECIFIC"]

LANGS = {
    "tr": "🇹🇷 Türkçe",
    "en": "🇬🇧 English",
    "zh": "🇨🇳 中文",
}

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
