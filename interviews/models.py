import uuid

from django.db import models

from common.models import TimeStampedModel


class InterviewSession(TimeStampedModel):
    class Kind(models.TextChoices):
        INTERVIEW = "interview"
        MEETING = "meeting"

    class Status(models.TextChoices):
        SCHEDULED = "scheduled"
        LIVE = "live"
        COMPLETED = "completed"
        CANCELLED = "cancelled"
        NO_SHOW = "no_show"

    organisation = models.ForeignKey("orgs.Organisation", on_delete=models.CASCADE)
    kind = models.CharField(max_length=12, choices=Kind.choices)
    application = models.ForeignKey(
        "recruitment.Application", null=True, blank=True, on_delete=models.CASCADE, related_name="interviews"
    )
    title = models.CharField(max_length=200)
    scheduled_at = models.DateTimeField(db_index=True)
    duration_minutes = models.PositiveSmallIntegerField(default=45)
    channel_name = models.CharField(max_length=64, unique=True, default=uuid.uuid4)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.SCHEDULED)
    recording_enabled = models.BooleanField(default=True)
    recording_consent_ack = models.BooleanField(default=False)
    recording_sid = models.CharField(max_length=128, blank=True)
    recording_resource_id = models.CharField(max_length=256, blank=True)
    recording_file = models.FileField(upload_to="recordings/%Y/%m/", null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)


class InterviewParticipant(TimeStampedModel):
    class Role(models.TextChoices):
        HOST = "host"
        INTERVIEWER = "interviewer"
        CANDIDATE = "candidate"
        ATTENDEE = "attendee"

    session = models.ForeignKey(InterviewSession, on_delete=models.CASCADE, related_name="participants")
    person = models.ForeignKey("people.Person", on_delete=models.CASCADE)
    role = models.CharField(max_length=12, choices=Role.choices)
    agora_uid = models.PositiveIntegerField()
    joined_at = models.DateTimeField(null=True, blank=True)
    left_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["session", "person"], name="uniq_participant"),
            models.UniqueConstraint(fields=["session", "agora_uid"], name="uniq_uid_in_channel"),
        ]
