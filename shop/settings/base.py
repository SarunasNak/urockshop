from pathlib import Path
import os
from dotenv import load_dotenv, find_dotenv

# rodo į projekto šaknį (šalia manage.py)
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Užkrauk .env PRIEŠ bet kokius os.getenv()
# Variantas A: aiškus kelias
load_dotenv(BASE_DIR / ".env")
# arba Variantas B: automatiškai susiras .env aukštyn
# load_dotenv(find_dotenv())

# --- Core ---
DEBUG = os.getenv("DEBUG", "false").strip().lower() == "true"
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-only-change-me")

SITE_HOST = os.getenv("SITE_HOST", "sarunasnakvosas.pythonanywhere.com")
SITE_SCHEME = os.getenv("SITE_SCHEME", "https")
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", SITE_HOST).split(",")
CSRF_TRUSTED_ORIGINS = [
    o.strip() for o in os.getenv(
        "CSRF_TRUSTED_ORIGINS",
        f"{SITE_SCHEME}://{SITE_HOST}"
    ).split(",") if o.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # 3rd party
    "rest_framework",
    "django_filters",
    # tavo app’ai
    "catalog",
    "pages",
    "cart",
    "checkout.apps.CheckoutConfig",
    "blog",
    "paysera",
    "stripe_payments",
]
INSTALLED_APPS += ["django.contrib.sitemaps"]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "shop.urls"

TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "templates"],
    "APP_DIRS": True,
    "OPTIONS": {
        "context_processors": [
            "django.template.context_processors.debug",
            "django.template.context_processors.request",
            "django.contrib.auth.context_processors.auth",
            "django.contrib.messages.context_processors.messages",
            "cart.context_processors.cart_info",
            "pages.context_processors.site_settings",
            "stripe_payments.context_processors.stripe_public_key",
        ],
    },
}]

WSGI_APPLICATION = "shop.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

LANGUAGE_CODE = "lt"
TIME_ZONE = "Europe/Vilnius"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 12,
}

# El. paštas
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "info@urock.lt")
ORDER_ADMIN_EMAIL = os.getenv("ORDER_ADMIN_EMAIL", "info@urock.lt")

# === Paysera ===
PAYSERA_PROJECT_ID = int(os.getenv("PAYSERA_PROJECT_ID", "0"))
PAYSERA_SIGN_PASSWORD = os.getenv("PAYSERA_SIGN_PASSWORD", "")
PAYSERA_TEST_MODE = os.getenv("PAYSERA_TEST_MODE", "true").lower() == "true"

# --- Saugos vėliavos prod'ui (pasirinktinai) ---
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

#Stripe
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
STRIPE_CURRENCY = os.getenv("STRIPE_CURRENCY", "eur")


