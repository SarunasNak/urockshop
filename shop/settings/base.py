from pathlib import Path
import os
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ✅ Patikrinam ar DJANGO_SETTINGS_MODULE jau nustatytas (pvz. WSGI)
# Jei taip – neloaduojam jokio kito .env
if not os.getenv("DJANGO_SETTINGS_MODULE"):
    # Jei ENV_FILE nenurodytas, pagal nutylėjimą imam .env
    env_file = os.getenv("ENV_FILE", ".env")
    env_path = BASE_DIR / env_file

    if env_path.exists():
        print(f"✅ Loading environment from {env_path}")
        load_dotenv(env_path)
    else:
        print(f"⚠️ Environment file not found at {env_path}")
else:
    print(f"ℹ️ Using environment already loaded via WSGI: {os.getenv('DJANGO_SETTINGS_MODULE')}")

# Maintenance flag (skaitymas iš .env)
MAINTENANCE_COVER = os.getenv("MAINTENANCE_COVER", "false").lower() == "true"

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
    # Django core
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    'analytics',
    "django.contrib.humanize",   # ↰ prie kitų contrib
     "adminsortable2",

    # 3rd party
    "rest_framework",
    "django_filters",

    # Jūsų app'ai
    "catalog",
    "pages",
    "cart",
    "checkout.apps.CheckoutConfig",  # jei turite AppConfig – puiku
    "blog",
    "paysera",
    "stripe_payments",
    "discounts",
    "newsletter",
]

INSTALLED_APPS += ["django.contrib.sitemaps"]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",

    # 🔒 1. Maintenance eina pirma
    "shop.middleware.MaintenanceCoverMiddleware",

    # 🎯 2. Čia įdedi TrafficSourceMiddleware (IDEALI VIETA)
    "shop.middleware.TrafficSourceMiddleware",

    # 👇 3. Staff disable analytics (gali būti čia, gali būti apačioje, netrukdo)
    "shop.middleware.DisableAnalyticsForStaffMiddleware",

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
            "cart.context_processors.cart_info",  # ← užtenka šito
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
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

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

# Cloudflare proxy – kad Django suprastų, jog užklausa yra HTTPS
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True

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

# --- DPD bendri ---
ENABLE_DPD = os.getenv("ENABLE_DPD", "true").lower() == "true"

# Kur laikom lokaliai (tas pats visiems env’ams)
DPD_CACHE_FILE = os.path.join(BASE_DIR, "checkout", "data", "dpd_lt_pickup_points.json")

# URL ir AUTH skaitom iš env; čia tik default’ai (tušti),
# realias reikšmes paduosi STAGING/PROD override’uose arba per procesų env.
DPD_POINTS_URL  = os.getenv("DPD_POINTS_URL", "")
DPD_POINTS_AUTH = os.getenv("DPD_POINTS_AUTH", "")
DPD_COUNTRY     = os.getenv("DPD_COUNTRY", "LT")
DPD_USERNAME = os.getenv("DPD_USERNAME", "")
DPD_PASSWORD = os.getenv("DPD_PASSWORD", "")

# --- CART / krepšelio nustatymai ---
CART_ITEM_TTL_HOURS = 48  # kiek valandų laikom prekę krepšelyje (sesijoje)

INSTALLED_APPS += ["django_ckeditor_5"]

CKEDITOR_5_CONFIGS = {
    "default": {
        "language": "lt",
        "toolbar": [
            "heading", "|",
            "bold", "italic", "link", "|",
            "fontColor",                 # <- pridėta
            "bulletedList", "numberedList", "|",
            "undo", "redo", "removeFormat",
        ],
        "fontColor": {
            "colors": [
                {"color": "#800020", "label": "Bordó"},
                {"color": "#000000", "label": "Juoda"},
            ],
            "columns": 5,
        },
    },
    "products": {  # palik kaip yra
        "language": "lt",
        "toolbar": [
            "heading", "|",
            "bold", "italic", "link", "|",
            "fontColor", "|",
            "bulletedList", "numberedList", "|",
            "undo", "redo", "removeFormat",
        ],
        "fontColor": {
            "colors": [
                {"color": "#800020", "label": "Bordó"},
                {"color": "#000000", "label": "Juoda"},
            ],
            "columns": 5,
        },
    },
}

