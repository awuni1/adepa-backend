from celery import shared_task
from django.core.mail import send_mail

from .events import EVENT_TEMPLATES


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def dispatch_event(self, event_name: str, payload: dict):
    """Resolves the template for an event and sends the transactional email.
    Recipient resolution and template rendering are event-specific — wire up
    a resolver per event as each module's email content is finalised."""

    template = EVENT_TEMPLATES[event_name]
    try:
        # Placeholder send — subject/recipient/context resolution is
        # event-specific and filled in as each module's copy is finalised.
        send_mail(
            subject=f"[Adepa HR] {event_name}",
            message=str(payload),
            from_email=None,
            recipient_list=[],
            fail_silently=True,
        )
    except Exception as exc:
        raise self.retry(exc=exc)
