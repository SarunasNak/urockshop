from .base import *
import os

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
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.yourprovider.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "info@urock.lt")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
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
