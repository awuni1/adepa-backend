from django.db import models

from common.models import TimeStampedModel


class AIScreeningResult(TimeStampedModel):
    application = models.OneToOneField(
        "recruitment.Application", on_delete=models.CASCADE, related_name="screening"
    )
    score = models.DecimalField(max_digits=5, decimal_places=2)
    summary = models.TextField()
    extracted = models.JSONField(default=dict)
    requirement_matches = models.JSONField(default=list)
    model_used = models.CharField(max_length=64)
    prompt_version = models.CharField(max_length=16)


class InterviewArtifact(TimeStampedModel):
    session = models.OneToOneField(
        "interviews.InterviewSession", on_delete=models.CASCADE, related_name="artifact"
    )
    transcript = models.TextField(blank=True)
    summary = models.TextField(blank=True)
    scorecard_draft = models.JSONField(default=dict)
    model_used = models.CharField(max_length=64)


class AttritionFlag(TimeStampedModel):
    person = models.ForeignKey("people.Person", on_delete=models.CASCADE, related_name="attrition_flags")
    risk_level = models.CharField(max_length=8)
    signals = models.JSONField(default=list)
    narrative = models.TextField()
    period_start = models.DateField()
    period_end = models.DateField()
    acknowledged_by = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL
    )


class ChatSession(TimeStampedModel):
    person = models.ForeignKey("people.Person", on_delete=models.CASCADE)
    messages = models.JSONField(default=list)


class AIUsageLog(TimeStampedModel):
    feature = models.CharField(max_length=32, db_index=True)
    model = models.CharField(max_length=64)
    input_tokens = models.PositiveIntegerField(default=0)
    output_tokens = models.PositiveIntegerField(default=0)
    latency_ms = models.PositiveIntegerField(default=0)
    success = models.BooleanField(default=True)
    error = models.TextField(blank=True)
