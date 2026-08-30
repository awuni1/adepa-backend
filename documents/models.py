from cloudinary_storage.storage import RawMediaCloudinaryStorage
from django.db import models

from common.models import TimeStampedModel


class DocumentRequest(TimeStampedModel):
    """A document (offer letter, contract, policy acknowledgement) sent to a
    person for e-signature — a typed full name counts as the signature,
    timestamped and IP-stamped, not a cryptographic signature."""

    class Status(models.TextChoices):
        PENDING = "pending"
        SIGNED = "signed"
        DECLINED = "declined"

    organisation = models.ForeignKey("orgs.Organisation", on_delete=models.CASCADE, related_name="document_requests")
    person = models.ForeignKey("people.Person", on_delete=models.CASCADE, related_name="document_requests")
    title = models.CharField(max_length=200)
    file = models.FileField(upload_to="document-requests/%Y/", storage=RawMediaCloudinaryStorage())
    requested_by = models.ForeignKey("accounts.User", null=True, on_delete=models.SET_NULL, related_name="+")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    signature_name = models.CharField(max_length=200, blank=True)
    signed_at = models.DateTimeField(null=True, blank=True)
    signed_ip = models.GenericIPAddressField(null=True, blank=True)
    declined_reason = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} — {self.person}"
