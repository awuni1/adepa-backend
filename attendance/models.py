from django.db import models

from common.models import TimeStampedModel


class AttendanceRecord(TimeStampedModel):
    person = models.ForeignKey("people.Person", on_delete=models.CASCADE, related_name="attendance")
    date = models.DateField(db_index=True)
    clock_in = models.DateTimeField(null=True, blank=True)
    clock_out = models.DateTimeField(null=True, blank=True)
    source = models.CharField(max_length=16, default="web")
    status = models.CharField(max_length=16, default="present")
    clock_in_lat = models.FloatField(null=True, blank=True)
    clock_in_lng = models.FloatField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["person", "date"], name="uniq_attendance_day")]


class GeofenceZone(TimeStampedModel):
    """A permitted clock-in radius. If an org has no active zones, clock-in
    location isn't checked at all — geofencing is opt-in per org."""

    organisation = models.ForeignKey("orgs.Organisation", on_delete=models.CASCADE, related_name="geofence_zones")
    name = models.CharField(max_length=120)
    latitude = models.FloatField()
    longitude = models.FloatField()
    radius_meters = models.PositiveIntegerField(default=200)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class LeaveType(TimeStampedModel):
    organisation = models.ForeignKey("orgs.Organisation", on_delete=models.CASCADE)
    name = models.CharField(max_length=64)
    days_per_year = models.PositiveSmallIntegerField()
    paid = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class LeaveRequest(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending"
        APPROVED = "approved"
        REJECTED = "rejected"
        CANCELLED = "cancelled"

    person = models.ForeignKey("people.Person", on_delete=models.CASCADE, related_name="leave_requests")
    leave_type = models.ForeignKey(LeaveType, on_delete=models.PROTECT)
    start_date = models.DateField()
    end_date = models.DateField()
    days = models.DecimalField(max_digits=5, decimal_places=1)
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    approver = models.ForeignKey(
        "people.Person", null=True, on_delete=models.SET_NULL, related_name="leave_approvals"
    )
    decided_at = models.DateTimeField(null=True, blank=True)


class LeaveBalance(TimeStampedModel):
    person = models.ForeignKey("people.Person", on_delete=models.CASCADE, related_name="leave_balances")
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    year = models.PositiveSmallIntegerField()
    entitled = models.DecimalField(max_digits=5, decimal_places=1)
    taken = models.DecimalField(max_digits=5, decimal_places=1, default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["person", "leave_type", "year"], name="uniq_balance")
        ]
