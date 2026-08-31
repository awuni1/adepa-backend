from .base import *  # noqa: F401,F403

DEBUG = True
ALLOWED_HOSTS = ["*"]

# base.py already picks console vs. Resend's SMTP relay based on whether
# RESEND_API_KEY is set — this used to force console unconditionally, which
# silently swallowed real sends even with a valid key configured.

SPECTACULAR_SETTINGS = {**SPECTACULAR_SETTINGS, "SERVE_INCLUDE_SCHEMA": True}  # noqa: F405
