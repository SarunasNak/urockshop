from .base import *

DEBUG = True
PAYSERA_TEST_MODE = True

ALLOWED_HOSTS = [
    "sarunasnakvosas.pythonanywhere.com",
    "localhost", "127.0.0.1",
    "testserver",
]

CSRF_TRUSTED_ORIGINS = [
    "https://sarunasnakvosas.pythonanywhere.com",
    "http://localhost",
    "http://127.0.0.1",
]

SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_SSL_REDIRECT = False

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
