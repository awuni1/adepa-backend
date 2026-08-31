from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from .events import EVENT_TEMPLATES


def _resolve_interview_scheduled(payload: dict):
    """Recipient + email content for interview.scheduled — the only event
    actually wired end-to-end so far. The other events in EVENT_TEMPLATES
    still have no resolver, so dispatch_event below intentionally skips them
    rather than sending an empty/broken email."""
    from interviews.models import InterviewParticipant, InterviewSession

    try:
        session = InterviewSession.objects.select_related("application__job").get(id=payload["session_id"])
    except InterviewSession.DoesNotExist:
        return None

    candidate = (
        InterviewParticipant.objects.filter(session=session, role=InterviewParticipant.Role.CANDIDATE)
        .select_related("person")
        .first()
    )
    if not candidate or not candidate.person.email:
        return None

    context = {
        "candidate_name": candidate.person.first_name,
        "title": session.title,
        "scheduled_at_display": session.scheduled_at.strftime("%A, %d %B %Y · %H:%M UTC"),
        "duration_minutes": session.duration_minutes,
        "job_title": session.application.job.title if session.application else None,
        "join_url": f"{settings.FRONTEND_URL}/interviews/{session.id}/room",
    }
    job_title = context["job_title"]
    subject = f"Your interview for {job_title} is scheduled" if job_title else f"Your interview is scheduled: {session.title}"
    return candidate.person.email, subject, context


def _resolve_person_hired(payload: dict):
    """Recipient + content for person.hired. If hire_from_application didn't
    provision a login (person already had one — e.g. an existing employee
    hired internally), temp_password is None and there's nothing useful to
    email, so this skips sending rather than mailing a password-less
    'welcome' that looks broken."""
    from employees.models import Employment
    from people.models import Person

    if not payload.get("temp_password"):
        return None

    try:
        person = Person.objects.get(id=payload["person_id"])
    except Person.DoesNotExist:
        return None
    if not person.email:
        return None

    employment = Employment.objects.filter(id=payload.get("employment_id")).select_related("department").first()

    context = {
        "first_name": person.first_name,
        "job_title": employment.job_title if employment else None,
        "start_date_display": employment.start_date.strftime("%d %B %Y") if employment else "",
        "login_email": person.email,
        "temp_password": payload["temp_password"],
        "login_url": f"{settings.FRONTEND_URL}/login",
    }
    return person.email, "Welcome to Adepa — your account is ready", context


# Maps event name -> payload -> (to_email, subject, template_context) | None.
# Only events with a real resolver here actually send anything; everything
# else in EVENT_TEMPLATES is a registered-but-not-yet-wired placeholder.
EVENT_RESOLVERS = {
    "interview.scheduled": _resolve_interview_scheduled,
    "person.hired": _resolve_person_hired,
}


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def dispatch_event(self, event_name: str, payload: dict):
    """Resolves the recipient + content for an event and sends the real
    transactional email. Events without a resolver in EVENT_RESOLVERS are
    silently skipped (not sent half-broken) until their recipient/template
    logic is written — see EVENT_TEMPLATES in events.py for what's still
    pending."""

    template = EVENT_TEMPLATES[event_name]
    resolver = EVENT_RESOLVERS.get(event_name)
    if resolver is None:
        return

    resolved = resolver(payload)
    if resolved is None:
        return
    to_email, subject, context = resolved

    try:
        html_body = render_to_string(template, context)
        email = EmailMultiAlternatives(subject=subject, body=strip_tags(html_body), to=[to_email])
        email.attach_alternative(html_body, "text/html")
        email.send(fail_silently=False)
    except Exception as exc:
        raise self.retry(exc=exc)
