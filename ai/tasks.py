from celery import shared_task


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def screen_resume(self, application_id):
    from recruitment.models import Application

    from . import services

    application = Application.objects.select_related("job").get(id=application_id)
    try:
        services.screen_resume(application)
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def summarise_interview(self, session_id):
    from interviews.models import InterviewSession

    from . import services

    session = InterviewSession.objects.get(id=session_id)
    try:
        services.summarise_interview(session)
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task
def run_attrition_scan():
    from . import services

    services.run_attrition_scan()
