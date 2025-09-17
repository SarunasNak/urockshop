from .prod import *

# Staging domenai (gali ateiti ir iš .env, bet duodu saugius default)
ALLOWED_HOSTS = [h.strip() for h in os.getenv(
    "ALLOWED_HOSTS",
    "staging.urock.lt,.pythonanywhere.com"
).split(",") if h.strip()]

CSRF_TRUSTED_ORIGINS = [o.strip() for o in os.getenv(
    "CSRF_TRUSTED_ORIGINS",
    "https://staging.urock.lt"
).split(",") if o.strip()]

# Svarbu: HSTS ant staging NENAUDOJAM (kad „neužrakintum“ naršyklių cache)
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False

# Paprastai DEBUG=false ir staging'e, bet jei nori trumpam – per .env
# DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# Staging: nesiunčiam tikrų laiškų
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = "Urock Staging <no-reply@staging.urock.lt>"