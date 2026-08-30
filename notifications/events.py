"""Event -> email template registry (§10). Any domain-status change anywhere
in the platform calls emit(event_name, payload); HR staff never send stage
emails manually. Each event maps to a template + recipient resolver, and
dispatch always happens through Celery so the request/response cycle never
waits on SMTP."""

EVENT_TEMPLATES = {
    "application.created": "emails/application_received.html",
    "application.stage_changed": "emails/application_stage_changed.html",
    "interview.scheduled": "emails/interview_scheduled.html",
    "interview.rescheduled": "emails/interview_rescheduled.html",
    "person.hired": "emails/welcome.html",
    "person.exited": "emails/exit_confirmation.html",
    "leave.requested": "emails/leave_requested.html",
    "leave.approved": "emails/leave_approved.html",
    "leave.rejected": "emails/leave_rejected.html",
    "payslip.issued": "emails/payslip_issued.html",
    "review.submitted": "emails/review_submitted.html",
}


def emit(event_name: str, payload: dict) -> None:
    if event_name not in EVENT_TEMPLATES:
        raise ValueError(f"Unregistered notification event: {event_name}")

    from .tasks import dispatch_event

    dispatch_event.delay(event_name, payload)
