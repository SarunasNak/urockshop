from .base import *
import os

ENVIRONMENT = "production"

# --- BENDRAI ---
DEBUG = False  # Produkcijoje visada False

ALLOWED_HOSTS = [
    "urock.lt",
    "www.urock.lt",
]

# Tik šie origin'ai gali naudoti CSRF
CSRF_TRUSTED_ORIGINS = [
    "https://urock.lt",
    "https://www.urock.lt",
]

# ========= DB (PostgreSQL) =========
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME"),
        "USER": os.getenv("DB_USER"),
        "PASSWORD": os.getenv("DB_PASSWORD"),
        "HOST": os.getenv("DB_HOST"),
        "PORT": os.getenv("DB_PORT", "5432"),
        "CONN_MAX_AGE": 60,
    }
}

# --- PROXY/HTTPS ---
# Cloudflare ar PythonAnywhere siunčia X-Forwarded-Proto, kad Django suprastų HTTPS
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Visada peradresuoti į HTTPS
SECURE_SSL_REDIRECT = True

# Slapukai tik per saugų HTTPS
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Naršyklėms pasakyti, kad visada naudotų HTTPS šiam domenui
SECURE_HSTS_SECONDS = 31536000  # 1 metai
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Papildomi saugumo headeriai
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
X_FRAME_OPTIONS = "DENY"

# --- EL. PAŠTAS ---
EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend")
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp-relay.brevo.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "true").lower() == "true"
EMAIL_USE_SSL = False
EMAIL_TIMEOUT = int(os.getenv("EMAIL_TIMEOUT", "20"))

EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "UROCK <info@urock.lt>")
SERVER_EMAIL = DEFAULT_FROM_EMAIL

# --- LOGGING (pasirinktinai, bet naudinga prod aplinkoje) ---
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "file": {
            "level": "WARNING",
            "class": "logging.FileHandler",
            "filename": os.path.join(BASE_DIR, "django_errors.log"),
        },
    },
    "loggers": {
        "django": {
            "handlers": ["file"],
            "level": "WARNING",
            "propagate": True,
        },
    },
}

# --- PASIRINKTINAI: ADMIN AIŠKINIMAI APIE KLAIDAS ---
# ADMINS = [("Sarunas", "info@urock.lt")]

# --- CUSTOM PROJECT SETTINGS ---
MAINTENANCE_COVER = os.getenv("MAINTENANCE_COVER", "false").lower() == "true"
