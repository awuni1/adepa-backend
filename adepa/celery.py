import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "adepa.settings.dev")

app = Celery("adepa")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
