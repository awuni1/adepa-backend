from cloudinary.models import CloudinaryField
from django.db import models

from common.models import TimeStampedModel


class Person(TimeStampedModel):
    """The spine of the platform: a candidate and an employee are the same
    underlying entity at different lifecycle stages (§1, §4.1)."""

    class LifecycleStage(models.TextChoices):
        APPLICANT = "applicant"
        CANDIDATE = "candidate"
        OFFER = "offer"
        EMPLOYEE = "employee"
        ALUMNI = "alumni"

    organisation = models.ForeignKey(
        "orgs.Organisation", on_delete=models.CASCADE, related_name="people"
    )
    user = models.OneToOneField(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="person"
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=32, blank=True)
    avatar = CloudinaryField("image", blank=True, null=True)
    lifecycle_stage = models.CharField(
        max_length=16, choices=LifecycleStage.choices, default=LifecycleStage.APPLICANT, db_index=True
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["organisation", "email"], name="uniq_person_email_per_org"),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name}"
