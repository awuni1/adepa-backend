from .base import *  # noqa: F401,F403

DEBUG = False

SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 7
SECURE_HSTS_INCLUDE_SUBDOMAINS = True

# drf-spectacular's Swagger UI is gated behind admin auth in prod (§5.1)
SPECTACULAR_SETTINGS = {**SPECTACULAR_SETTINGS, "SERVE_PERMISSIONS": ["rest_framework.permissions.IsAdminUser"]}  # noqa: F405
