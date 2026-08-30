from django.db import models

from common.models import TimeStampedModel


class OffboardingStage(TimeStampedModel):
    organisation = models.ForeignKey("orgs.Organisation", on_delete=models.CASCADE, related_name="offboarding_stages")
    title = models.CharField(max_length=100)
    sequence = models.PositiveIntegerField(default=0)
    is_final_stage = models.BooleanField(default=False)

    class Meta:
        ordering = ["sequence"]

    def __str__(self):
        return self.title


class OffboardingTaskTemplate(TimeStampedModel):
    stage = models.ForeignKey(OffboardingStage, on_delete=models.CASCADE, related_name="task_templates")
    title = models.CharField(max_length=200)
    is_required = models.BooleanField(default=True)

    def __str__(self):
        return self.title


class PersonOffboarding(TimeStampedModel):
    class Status(models.TextChoices):
        ONGOING = "ongoing"
        COMPLETED = "completed"
        CANCELLED = "cancelled"

    person = models.OneToOneField("people.Person", on_delete=models.CASCADE, related_name="offboarding")
    current_stage = models.ForeignKey(OffboardingStage, on_delete=models.PROTECT, related_name="+")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ONGOING)
    exit_reason = models.CharField(max_length=255, blank=True)
    notice_starts = models.DateField(null=True, blank=True)
    notice_ends = models.DateField(null=True, blank=True)
    initiated_by = models.ForeignKey("accounts.User", null=True, on_delete=models.SET_NULL, related_name="+")
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Offboarding — {self.person}"


class PersonOffboardingTask(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending"
        DONE = "done"

    person_offboarding = models.ForeignKey(PersonOffboarding, on_delete=models.CASCADE, related_name="tasks")
    task_template = models.ForeignKey(OffboardingTaskTemplate, on_delete=models.CASCADE, related_name="+")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey("accounts.User", null=True, on_delete=models.SET_NULL, related_name="+")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["person_offboarding", "task_template"], name="uniq_offboarding_task"),
        ]
