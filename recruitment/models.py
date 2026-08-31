from cloudinary_storage.storage import RawMediaCloudinaryStorage
from django.db import models

from common.models import TimeStampedModel


class JobPosting(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft"
        OPEN = "open"
        CLOSED = "closed"
        ARCHIVED = "archived"

    organisation = models.ForeignKey("orgs.Organisation", on_delete=models.CASCADE)
    department = models.ForeignKey("orgs.Department", on_delete=models.PROTECT)
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField()
    requirements = models.JSONField(default=list)
    location = models.CharField(max_length=120)
    employment_type = models.CharField(max_length=32)
    salary_min = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    salary_max = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)
    closes_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return self.title


class Application(TimeStampedModel):
    class Stage(models.TextChoices):
        RECEIVED = "received"
        SCREENING = "screening"
        SHORTLISTED = "shortlisted"
        INTERVIEW = "interview"
        OFFER = "offer"
        HIRED = "hired"
        REJECTED = "rejected"
        WITHDRAWN = "withdrawn"

    # Legal stage transitions enforced server-side (§7.1). One step back
    # through the live pipeline is allowed too (e.g. an accidental advance,
    # or an interview that needs another screening pass) — but HIRED and
    # REJECTED/WITHDRAWN stay terminal on purpose: un-hiring has real
    # downstream effects (hire() already created a real Employment record),
    # so that needs its own deliberate action, not a stage-flag reversal.
    TRANSITIONS = {
        Stage.RECEIVED: {Stage.SCREENING, Stage.REJECTED, Stage.WITHDRAWN},
        Stage.SCREENING: {Stage.SHORTLISTED, Stage.RECEIVED, Stage.REJECTED, Stage.WITHDRAWN},
        Stage.SHORTLISTED: {Stage.INTERVIEW, Stage.SCREENING, Stage.REJECTED, Stage.WITHDRAWN},
        Stage.INTERVIEW: {Stage.OFFER, Stage.SHORTLISTED, Stage.REJECTED, Stage.WITHDRAWN},
        Stage.OFFER: {Stage.HIRED, Stage.INTERVIEW, Stage.REJECTED, Stage.WITHDRAWN},
        Stage.HIRED: set(),
        Stage.REJECTED: set(),
        Stage.WITHDRAWN: set(),
    }

    job = models.ForeignKey(JobPosting, on_delete=models.CASCADE, related_name="applications")
    person = models.ForeignKey("people.Person", on_delete=models.CASCADE, related_name="applications")
    stage = models.CharField(max_length=16, choices=Stage.choices, default=Stage.RECEIVED, db_index=True)
    cover_letter = models.TextField(blank=True)
    cv_file = models.FileField(upload_to="cvs/%Y/%m/", storage=RawMediaCloudinaryStorage())
    answers = models.JSONField(default=dict)
    source = models.CharField(max_length=64, default="careers_portal")
    stage_history = models.JSONField(default=list)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["job", "person"], name="uniq_application_per_job"),
        ]
        indexes = [models.Index(fields=["job", "stage"])]

    def can_transition_to(self, new_stage: str) -> bool:
        return new_stage in self.TRANSITIONS.get(self.stage, set())


class ApplicationNote(TimeStampedModel):
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="notes")
    author = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True)
    body = models.TextField()


class Scorecard(TimeStampedModel):
    """One interviewer's structured evaluation of one interview."""

    interview = models.ForeignKey(
        "interviews.InterviewSession", on_delete=models.CASCADE, related_name="scorecards"
    )
    interviewer = models.ForeignKey("accounts.User", on_delete=models.CASCADE)
    ratings = models.JSONField(default=dict)
    overall = models.PositiveSmallIntegerField(null=True)
    recommendation = models.CharField(max_length=16, blank=True)
    comments = models.TextField(blank=True)
    ai_draft = models.BooleanField(default=False)
