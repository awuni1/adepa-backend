from django.db import models

from common.models import TimeStampedModel


class OnboardingStage(TimeStampedModel):
    """Ordered stages a new hire moves through (e.g. Paperwork, Equipment,
    Orientation, Done) — configured per organisation."""

    organisation = models.ForeignKey("orgs.Organisation", on_delete=models.CASCADE, related_name="onboarding_stages")
    title = models.CharField(max_length=100)
    sequence = models.PositiveIntegerField(default=0)
    is_final_stage = models.BooleanField(default=False)

    class Meta:
        ordering = ["sequence"]

    def __str__(self):
        return self.title


class OnboardingTaskTemplate(TimeStampedModel):
    stage = models.ForeignKey(OnboardingStage, on_delete=models.CASCADE, related_name="task_templates")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    is_required = models.BooleanField(default=True)

    def __str__(self):
        return self.title


class PersonOnboarding(TimeStampedModel):
    """Tracks one hired person's progress through onboarding — created when
    an Application converts to Employment (§7.3's provenance link)."""

    class Status(models.TextChoices):
        IN_PROGRESS = "in_progress"
        COMPLETED = "completed"

    person = models.OneToOneField("people.Person", on_delete=models.CASCADE, related_name="onboarding")
    current_stage = models.ForeignKey(OnboardingStage, on_delete=models.PROTECT, related_name="+")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.IN_PROGRESS)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Onboarding — {self.person}"


class PersonOnboardingTask(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending"
        DONE = "done"

    person_onboarding = models.ForeignKey(PersonOnboarding, on_delete=models.CASCADE, related_name="tasks")
    task_template = models.ForeignKey(OnboardingTaskTemplate, on_delete=models.CASCADE, related_name="+")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey("accounts.User", null=True, on_delete=models.SET_NULL, related_name="+")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["person_onboarding", "task_template"], name="uniq_onboarding_task"),
        ]
