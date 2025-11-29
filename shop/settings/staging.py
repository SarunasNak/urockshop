# shop/settings/staging.py
import os
from .base import *  # noqa: F401,F403
from .base import BASE_DIR  # noqa: F401
from dotenv import load_dotenv

# Užkrauk .env iš projekto šaknies
load_dotenv(BASE_DIR / ".env.staging")

# ========= Bendri =========
DEBUG = False

ALLOWED_HOSTS = [h.strip() for h in os.getenv(
    "ALLOWED_HOSTS",
    "staging.urock.lt,.pythonanywhere.com"
).split(",") if h.strip()]

CSRF_TRUSTED_ORIGINS = [o.strip() for o in os.getenv(
    "CSRF_TRUSTED_ORIGINS",
    # PASTABA: pakeisk <tavo-vardas> į realų PA subdomeną
    "https://staging.urock.lt,https://<tavo-vardas>.pythonanywhere.com"
).split(",") if o.strip()]

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

# ========= El. paštas (staging per Brevo SMTP – reikšmės ateina iš .env) =========
EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend")
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp-relay.brevo.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "true").lower() == "true"
EMAIL_USE_SSL = False
EMAIL_TIMEOUT = int(os.getenv("EMAIL_TIMEOUT", "20"))

# Brevo SMTP username (pvz.: 92xxxxxxx@smtp-brevo.com) ir slaptažodis iš .env
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")

# Iš ko siųsti (turi būti autentifikuotas @urock.lt domenas Brevo)
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "UROCK <info@urock.lt>")
SERVER_EMAIL = DEFAULT_FROM_EMAIL


# ========= Failai =========
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_ROOT = BASE_DIR / "media"

# ========= Saugumas =========
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False

SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# noqa
INSTALLED_APPS += [
    "video",
]


