from datetime import timedelta
from pathlib import Path

import dj_database_url
import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY", default="insecure-dev-key")
DEBUG = env.bool("DEBUG", default=False)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "django_filters",
    "corsheaders",
    "cloudinary",
    "cloudinary_storage",
    "drf_spectacular",
    "common",
    "orgs",
    "accounts",
    "people",
    "recruitment",
    "interviews",
    "employees",
    "attendance",
    "payroll",
    "performance",
    "notifications",
    "ai",
    "onboarding",
    "offboarding",
    "assets",
    "helpdesk",
    "audit",
    "documents",
]

AUTH_USER_MODEL = "accounts.User"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "audit.middleware.CurrentUserMiddleware",
]

ROOT_URLCONF = "adepa.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "adepa.wsgi.application"
ASGI_APPLICATION = "adepa.asgi.application"

DATABASES = {
    "default": dj_database_url.parse(
        env("DATABASE_URL"),
        # 0, not persistent: DATABASE_URL now points at Supabase's transaction-mode
        # pooler (port 6543), which multiplexes connections itself. Django holding
        # its own connections open on top of that (conn_max_age>0) just doubles up
        # pooling and was how the session-mode pooler's connection cap got exhausted.
        conn_max_age=0,
        ssl_require=True,
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Accra"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Cloudinary — files & images (§3.2)
CLOUDINARY_STORAGE = {
    "CLOUD_NAME": env("CLOUDINARY_CLOUD_NAME", default=""),
    "API_KEY": env("CLOUDINARY_API_KEY", default=""),
    "API_SECRET": env("CLOUDINARY_API_SECRET", default=""),
}
DEFAULT_FILE_STORAGE = "cloudinary_storage.storage.MediaCloudinaryStorage"

# Agora (§8)
AGORA_APP_ID = env("AGORA_APP_ID", default="")
AGORA_APP_CERTIFICATE = env("AGORA_APP_CERTIFICATE", default="")
AGORA_CUSTOMER_KEY = env("AGORA_CUSTOMER_KEY", default="")
AGORA_CUSTOMER_SECRET = env("AGORA_CUSTOMER_SECRET", default="")
# Notification secret for the Cloud Recording / Media product, from Agora
# Console → Notifications. Verifies the Agora-Signature-V2 header on
# incoming webhook callbacks (see interviews.views.AgoraWebhookView).
AGORA_WEBHOOK_SECRET = env("AGORA_WEBHOOK_SECRET", default="")

# Paystack (payroll disbursement — transfer recipients + transfers).
# https://paystack.com/docs/api/transfer-recipient/
PAYSTACK_SECRET_KEY = env("PAYSTACK_SECRET_KEY", default="")
PAYSTACK_PUBLIC_KEY = env("PAYSTACK_PUBLIC_KEY", default="")

# Groq (§9). Switched from Gemini after the Gemini key's project turned out
# to have zero pro-model quota (free tier) and the flash model was hitting
# persistent 503s — see chat history for the diagnostic that found this.
# "llama-3.3-70b-versatile" (the model this was first wired up with) has since
# been retired from this key's catalog (404 model_not_found) — verified against
# GET /openai/v1/models and swapped for gpt-oss-120b, live-tested working below.
GROQ_API_KEY = env("GROQ_API_KEY", default="")
GROQ_MODEL = "openai/gpt-oss-120b"

# Resend, via its SMTP relay — so notifications/tasks.py's existing send_mail()
# call actually delivers instead of silently no-op'ing (fail_silently=True was
# masking that no backend was configured at all). Falls back to Django's
# console backend when no key is set, so local dev without a key still works.
EMAIL_BACKEND = (
    "django.core.mail.backends.smtp.EmailBackend"
    if env("RESEND_API_KEY", default="")
    else "django.core.mail.backends.console.EmailBackend"
)
EMAIL_HOST = "smtp.resend.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = "resend"
EMAIL_HOST_PASSWORD = env("RESEND_API_KEY", default="")
EMAIL_TIMEOUT = 15  # Django's SMTP backend blocks forever by default otherwise
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="Adepa HR <onboarding@resend.dev>")

# Where the frontend actually lives — used to build real links (e.g. "join
# your interview") inside transactional emails, since the API has no other
# way to know the SPA's own origin.
FRONTEND_URL = env("FRONTEND_URL", default="http://localhost:5173")

CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_PAGINATION_CLASS": "common.pagination.StandardPagination",
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.ScopedRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "public_apply": "10/hour",
        "chatbot": "60/hour",
        "token_mint": "30/hour",
    },
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "common.exceptions.api_exception_handler",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Adepa HR API",
    "VERSION": "1.0.0",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "TOKEN_OBTAIN_SERIALIZER": "accounts.tokens.AdepaTokenObtainPairSerializer",
}

# Celery (§12)
CELERY_BROKER_URL = env("REDIS_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE

from celery.schedules import crontab  # noqa: E402

CELERY_BEAT_SCHEDULE = {
    "attrition-scan": {
        "task": "ai.tasks.run_attrition_scan",
        "schedule": crontab(hour=2, minute=0, day_of_week="mon"),
    },
    "attendance-close-day": {
        "task": "attendance.tasks.close_day",
        "schedule": crontab(hour=23, minute=55),
    },
    "leave-accrual-monthly": {
        "task": "attendance.tasks.accrue_leave",
        "schedule": crontab(day_of_month=1, hour=1, minute=0),
    },
}
