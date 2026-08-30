from django.db import models

from common.models import TimeStampedModel


class ReviewCycle(TimeStampedModel):
    organisation = models.ForeignKey("orgs.Organisation", on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    starts_on = models.DateField()
    ends_on = models.DateField()
    is_active = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class PerformanceReview(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft"
        SUBMITTED = "submitted"
        ACKNOWLEDGED = "acknowledged"

    cycle = models.ForeignKey(ReviewCycle, on_delete=models.CASCADE, related_name="reviews")
    person = models.ForeignKey("people.Person", on_delete=models.CASCADE, related_name="reviews")
    reviewer = models.ForeignKey("people.Person", on_delete=models.PROTECT, related_name="reviews_given")
    ratings = models.JSONField(default=dict)
    summary = models.TextField(blank=True)
    ai_draft_summary = models.TextField(blank=True)
    status = models.CharField(max_length=14, choices=Status.choices, default=Status.DRAFT)


class FeedbackNote(TimeStampedModel):
    person = models.ForeignKey("people.Person", on_delete=models.CASCADE, related_name="feedback_notes")
    author = models.ForeignKey("people.Person", on_delete=models.CASCADE)
    cycle = models.ForeignKey(ReviewCycle, null=True, blank=True, on_delete=models.SET_NULL)
    body = models.TextField()
