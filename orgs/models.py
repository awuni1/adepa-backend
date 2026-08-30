from cloudinary_storage.storage import RawMediaCloudinaryStorage
from django.db import models

from common.models import TimeStampedModel


class Organisation(TimeStampedModel):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.name


class Department(TimeStampedModel):
    organisation = models.ForeignKey(
        Organisation, on_delete=models.CASCADE, related_name="departments"
    )
    name = models.CharField(max_length=120)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organisation", "name"], name="uniq_department_per_org"
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.organisation.name})"


class Announcement(TimeStampedModel):
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name="announcements")
    title = models.CharField(max_length=200)
    body = models.TextField()
    created_by = models.ForeignKey("accounts.User", null=True, on_delete=models.SET_NULL)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class PolicyDocument(TimeStampedModel):
    """Org-wide compliance/handbook documents employees can view — distinct
    from EmployeeDocument, which holds per-person files like contracts."""

    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name="policy_documents")
    title = models.CharField(max_length=200)
    category = models.CharField(max_length=32, default="compliance")
    file = models.FileField(upload_to="policies/%Y/", storage=RawMediaCloudinaryStorage())
    uploaded_by = models.ForeignKey("accounts.User", null=True, on_delete=models.SET_NULL)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
