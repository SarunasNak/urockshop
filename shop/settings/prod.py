import os
from dotenv import load_dotenv
from .base import *  # noqa: F401,F403
from .base import BASE_DIR  # noqa: F401

# Užkrauk .env.production iš projekto šaknies
load_dotenv(BASE_DIR / ".env.production")

# --- BENDRAI ---
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# Domenai
ALLOWED_HOSTS = [h.strip() for h in os.getenv(
    "ALLOWED_HOSTS",
    "urock.lt,www.urock.lt"
).split(",") if h.strip()]

# CSRF reikia pilnų originų su schema:
CSRF_TRUSTED_ORIGINS = [o.strip() for o in os.getenv(
    "CSRF_TRUSTED_ORIGINS",
    "https://urock.lt,https://www.urock.lt"
).split(",") if o.strip()]

# --- PROXY/HTTPS ---
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Naudok ENV valdymui, jei dar netestuojamas HTTPS
SECURE_SSL_REDIRECT = os.getenv("SECURE_SSL_REDIRECT", "true").lower() == "true"

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# --- HSTS ---
SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "31536000"))  # 1 metai
SECURE_HSTS_INCLUDE_SUBDOMAINS = os.getenv("SECURE_HSTS_INCLUDE_SUBDOMAINS", "true").lower() == "true"
SECURE_HSTS_PRELOAD = os.getenv("SECURE_HSTS_PRELOAD", "true").lower() == "true"

# --- Kiti saugumo antraštės ---
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
X_FRAME_OPTIONS = "DENY"

# --- EL. PAŠTAS ---
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.urock.lt")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "info@urock.lt")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "true").lower() == "true"
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", EMAIL_HOST_USER)
SERVER_EMAIL = DEFAULT_FROM_EMAIL

# (pasirinktinai) ADMIN pranešimai apie 500 klaidas:
ADMINS = [("Sarunas", "info@urock.lt")]
