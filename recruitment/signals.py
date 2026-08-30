from django.db.models.signals import post_save
from django.dispatch import receiver

from notifications.events import emit

from .models import Application


@receiver(post_save, sender=Application)
def on_application_created(sender, instance, created, **kwargs):
    if not created:
        return
    emit("application.created", {"application_id": str(instance.id)})

    from ai.tasks import screen_resume

    screen_resume.delay(str(instance.id))
