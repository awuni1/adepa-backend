from django.db import models

from common.models import TimeStampedModel


class TicketType(TimeStampedModel):
    organisation = models.ForeignKey("orgs.Organisation", on_delete=models.CASCADE, related_name="ticket_types")
    title = models.CharField(max_length=100)

    def __str__(self):
        return self.title


class Ticket(TimeStampedModel):
    class Priority(models.TextChoices):
        LOW = "low"
        MEDIUM = "medium"
        HIGH = "high"

    class Status(models.TextChoices):
        NEW = "new"
        IN_PROGRESS = "in_progress"
        RESOLVED = "resolved"
        CLOSED = "closed"

    organisation = models.ForeignKey("orgs.Organisation", on_delete=models.CASCADE, related_name="tickets")
    raised_by = models.ForeignKey("people.Person", on_delete=models.CASCADE, related_name="tickets_raised")
    ticket_type = models.ForeignKey(TicketType, on_delete=models.PROTECT, related_name="tickets")
    title = models.CharField(max_length=200)
    description = models.TextField()
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MEDIUM)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW)
    assigned_to = models.ForeignKey(
        "people.Person", null=True, blank=True, on_delete=models.SET_NULL, related_name="tickets_assigned"
    )
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class TicketComment(TimeStampedModel):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey("people.Person", on_delete=models.CASCADE, related_name="+")
    body = models.TextField()

    class Meta:
        ordering = ["created_at"]
