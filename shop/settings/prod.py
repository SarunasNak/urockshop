from .base import *
import os

DEBUG = os.getenv("DEBUG", "false").lower() == "true"

ALLOWED_HOSTS = [h.strip() for h in os.getenv(
    "ALLOWED_HOSTS",
    "urock.lt,www.urock.lt"  # default: live
).split(",") if h.strip()]

CSRF_TRUSTED_ORIGINS = [o.strip() for o in os.getenv(
    "CSRF_TRUSTED_ORIGINS",
    "https://urock.lt,https://www.urock.lt"  # default: live
).split(",") if o.strip()]

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# HSTS – įjunk TIK LIVE (nenaudok HSTS ant staging):
SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "31536000"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = os.getenv("SECURE_HSTS_INCLUDE_SUBDOMAINS", "true").lower() == "true"
SECURE_HSTS_PRELOAD = os.getenv("SECURE_HSTS_PRELOAD", "false").lower() == "true"

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
X_FRAME_OPTIONS = "DENY"

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.yourprovider.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "info@urock.lt")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "true").lower() == "true"

DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", EMAIL_HOST_USER)
SERVER_EMAIL = DEFAULT_FROM_EMAIL
