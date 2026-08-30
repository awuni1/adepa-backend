from .base import *  # noqa: F401,F403

DEBUG = True
ALLOWED_HOSTS = ["*"]

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

SPECTACULAR_SETTINGS = {**SPECTACULAR_SETTINGS, "SERVE_INCLUDE_SCHEMA": True}  # noqa: F405
