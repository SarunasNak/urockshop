from .base import *
import os

# --- BENDRAI ---
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# Įtrauk ir PA subdomeną, kad kol kas galėtum testuoti be DNS
PA_HOST = os.getenv("PA_HOST", "SarunasNakvosas.pythonanywhere.com")

ALLOWED_HOSTS = [h.strip() for h in os.getenv(
    "ALLOWED_HOSTS",
    f"urock.lt,www.urock.lt,{PA_HOST}"
).split(",") if h.strip()]

# CSRF reikia pilnų originų su schema:
DEFAULT_CSRF = f"https://urock.lt,https://www.urock.lt,https://{PA_HOST}"
CSRF_TRUSTED_ORIGINS = [o.strip() for o in os.getenv(
    "CSRF_TRUSTED_ORIGINS", DEFAULT_CSRF
).split(",") if o.strip()]

# --- PROXY/HTTPS ---
# Už Cloudflare/PA dažniausiai gausi X-Forwarded-Proto
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Kad kol tvarkai DNS/SSL, galėtum testuoti http ant PA subdomeno,
# valdyk redirect'ą per ENV (įjunk tik kai jau pilnai perėjai į HTTPS per CF)
SECURE_SSL_REDIRECT = os.getenv("SECURE_SSL_REDIRECT", "false").lower() == "true"

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# HSTS įjunk tik po to, kai HTTPS tikrai veikia ant domeno (ne PA subdomeno).
SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "0"))  # 0 kol kas
SECURE_HSTS_INCLUDE_SUBDOMAINS = os.getenv("SECURE_HSTS_INCLUDE_SUBDOMAINS", "true").lower() == "true"
SECURE_HSTS_PRELOAD = os.getenv("SECURE_HSTS_PRELOAD", "false").lower() == "true"

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
X_FRAME_OPTIONS = "DENY"

# --- EL. PAŠTAS (palik savo reikšmes / ENV) ---
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.yourprovider.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "info@urock.lt")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "true").lower() == "true"
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", EMAIL_HOST_USER)
SERVER_EMAIL = DEFAULT_FROM_EMAIL

# (pasirinktinai) ADMIN pranešimai apie 500 klaidas:
# ADMINS = [("Sarunas", "info@urock.lt")]
