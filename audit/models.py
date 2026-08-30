from django.db import models

from common.models import TimeStampedModel


class AuditLog(TimeStampedModel):
    class Action(models.TextChoices):
        CREATE = "create"
        UPDATE = "update"
        DELETE = "delete"

    organisation = models.ForeignKey("orgs.Organisation", on_delete=models.CASCADE, related_name="audit_logs")
    actor = models.ForeignKey("accounts.User", null=True, on_delete=models.SET_NULL, related_name="+")
    model_name = models.CharField(max_length=100)
    object_id = models.CharField(max_length=64)
    object_repr = models.CharField(max_length=255, blank=True)
    action = models.CharField(max_length=10, choices=Action.choices)
    changes = models.JSONField(default=dict, blank=True)  # {"field": {"old": ..., "new": ...}}

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.action} {self.model_name}#{self.object_id}"
