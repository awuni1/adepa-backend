"""Service layer Gemini calls (§2.2, §9): modules call these functions, never
the SDK directly, so prompt versioning and model choice live in one place."""

import json

from django.conf import settings

from .client import gemini_client, load_prompt
from .schemas import INTERVIEW_SUMMARY_SCHEMA, SCREENING_SCHEMA

SCREENING_PROMPT_VERSION = "v1"


def screen_resume(application) -> dict:
    import requests

    from .models import AIScreeningResult

    cv_text = requests.get(application.cv_file.url, timeout=30).text if application.cv_file else ""
    prompt = load_prompt(f"screening_{SCREENING_PROMPT_VERSION}.txt").format(
        job_title=application.job.title,
        requirements="\n".join(f"- {r}" for r in application.job.requirements),
        cv_text=cv_text,
    )
    raw = gemini_client.generate(
        prompt, model=settings.GEMINI_FLASH_MODEL, feature="screening", response_schema=SCREENING_SCHEMA
    )
    data = json.loads(raw)

    result, _ = AIScreeningResult.objects.update_or_create(
        application=application,
        defaults={
            "score": data["score"],
            "summary": data["summary"],
            "extracted": data["extracted"],
            "requirement_matches": data["requirement_matches"],
            "model_used": settings.GEMINI_FLASH_MODEL,
            "prompt_version": SCREENING_PROMPT_VERSION,
        },
    )
    application.stage = application.Stage.SCREENING
    application.save(update_fields=["stage"])
    return result


def summarise_interview(session) -> dict:
    """Interview transcription/summary uses Gemini's native audio input
    (§3, no separate speech-to-text service required)."""
    from .models import InterviewArtifact

    audio_bytes = session.recording_file.read() if session.recording_file else b""
    prompt = load_prompt("interview_summary_v1.txt").format(
        job_title=session.application.job.title if session.application else session.title,
        transcript="[transcribed from attached audio]",
    )
    files = [{"mime_type": "audio/mp4", "data": audio_bytes}] if audio_bytes else []
    raw = gemini_client.generate(
        prompt, model=settings.GEMINI_PRO_MODEL, feature="interview_summary",
        response_schema=INTERVIEW_SUMMARY_SCHEMA, files=files,
    )
    data = json.loads(raw)

    artifact, _ = InterviewArtifact.objects.update_or_create(
        session=session,
        defaults={
            "transcript": data.get("transcript", ""),
            "summary": data["summary"],
            "scorecard_draft": data["scorecard_draft"],
            "model_used": settings.GEMINI_PRO_MODEL,
        },
    )
    return artifact


def draft_job_description(title: str, department: str, brief: str) -> str:
    prompt = load_prompt("job_description_v1.txt").format(title=title, department=department, brief=brief)
    return gemini_client.generate(prompt, model=settings.GEMINI_FLASH_MODEL, feature="jd")


def draft_performance_review(review) -> str:
    notes = "\n".join(f"- {n.body}" for n in review.person.feedback_notes.filter(cycle=review.cycle))
    prompt = load_prompt("performance_review_v1.txt").format(
        person_name=f"{review.person.first_name} {review.person.last_name}",
        cycle_name=review.cycle.name,
        notes=notes or "(no notes logged)",
    )
    return gemini_client.generate(prompt, model=settings.GEMINI_PRO_MODEL, feature="performance_review")


def chat_reply(person, message: str, session) -> str:
    from attendance.models import LeaveBalance

    balances = list(LeaveBalance.objects.filter(person=person).values("leave_type__name", "entitled", "taken"))
    context = f"Leave balances: {balances}"
    system = load_prompt("chatbot_system_v1.txt").format(
        person_name=f"{person.first_name} {person.last_name}", context=context
    )
    prompt = f"{system}\n\nQuestion: {message}"
    reply = gemini_client.generate(prompt, model=settings.GEMINI_FLASH_MODEL, feature="chatbot")

    session.messages.append({"role": "user", "content": message})
    session.messages.append({"role": "assistant", "content": reply})
    session.save(update_fields=["messages"])
    return reply


def run_attrition_scan():
    """Weekly Beat job (§5.1): flags employees whose recent signals (lateness,
    leave patterns) suggest attrition risk. Signal collection is intentionally
    simple here — replace with the org's real HR analytics once available."""
    from datetime import timedelta

    from django.utils import timezone

    from attendance.models import AttendanceRecord
    from people.models import Person

    from .models import AttritionFlag

    period_end = timezone.localdate()
    period_start = period_end - timedelta(days=60)

    for person in Person.objects.filter(lifecycle_stage=Person.LifecycleStage.EMPLOYEE):
        records = AttendanceRecord.objects.filter(person=person, date__range=(period_start, period_end))
        total = records.count()
        if not total:
            continue
        late_ratio = records.filter(status="late").count() / total
        if late_ratio > 0.3:
            AttritionFlag.objects.create(
                person=person,
                risk_level="medium" if late_ratio < 0.5 else "high",
                signals=[f"lateness at {late_ratio:.0%} over last {total} recorded days"],
                narrative=f"{person.first_name} has been late {late_ratio:.0%} of recorded working days recently.",
                period_start=period_start,
                period_end=period_end,
            )
