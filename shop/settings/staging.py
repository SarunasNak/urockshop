# shop/settings/staging.py
import os
from .base import *  # noqa: F401,F403  # (nutildo perspėjimą apie import *)
from .base import BASE_DIR  # noqa: F401  # kad linteris „matytų“ BASE_DIR
from dotenv import load_dotenv

# užkrauk .env iš projekto šaknies
load_dotenv(BASE_DIR / ".env")

# ========= Bendri =========
DEBUG = False

ALLOWED_HOSTS = [h.strip() for h in os.getenv(
    "ALLOWED_HOSTS",
    # tavo staging domenas + pythonanywhere subdomenas
    "staging.urock.lt,.pythonanywhere.com"
).split(",") if h.strip()]

CSRF_TRUSTED_ORIGINS = [o.strip() for o in os.getenv(
    "CSRF_TRUSTED_ORIGINS",
    # CSRF čia reikia pilnų originų su schema
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
        # "OPTIONS": {"sslmode": os.getenv("DB_SSLMODE", "require")},
        "CONN_MAX_AGE": 60,
    }
}

# ========= Failai =========
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_ROOT = BASE_DIR / "media"

# ========= Saugos skirtumai staging'e =========
# HSTS staginge NENAUDOJAM, kad neužraktintum naršyklių
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False

# HTTPS redirect'ą įjunk tik jei staging domenas turi SSL
SECURE_SSL_REDIRECT = True

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# ========= El. paštas (nestipriai – į konsolę) =========
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = "Urock Staging <no-reply@staging.urock.lt>"

