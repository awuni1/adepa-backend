from django.db import models

from common.models import TimeStampedModel


class AssetCategory(TimeStampedModel):
    organisation = models.ForeignKey("orgs.Organisation", on_delete=models.CASCADE, related_name="asset_categories")
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Asset(TimeStampedModel):
    class Status(models.TextChoices):
        AVAILABLE = "available"
        ASSIGNED = "assigned"
        MAINTENANCE = "maintenance"
        RETIRED = "retired"

    organisation = models.ForeignKey("orgs.Organisation", on_delete=models.CASCADE, related_name="assets")
    category = models.ForeignKey(AssetCategory, on_delete=models.PROTECT, related_name="assets")
    name = models.CharField(max_length=200)
    tracking_id = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    purchase_date = models.DateField(null=True, blank=True)
    purchase_cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.AVAILABLE)

    def __str__(self):
        return f"{self.name} ({self.tracking_id})"


class AssetAssignment(TimeStampedModel):
    class Status(models.TextChoices):
        ASSIGNED = "assigned"
        RETURNED = "returned"

    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name="assignments")
    person = models.ForeignKey("people.Person", on_delete=models.CASCADE, related_name="asset_assignments")
    assigned_date = models.DateField(auto_now_add=True)
    assigned_by = models.ForeignKey("accounts.User", null=True, on_delete=models.SET_NULL, related_name="+")
    return_date = models.DateField(null=True, blank=True)
    return_condition = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ASSIGNED)

    class Meta:
        ordering = ["-assigned_date"]

    def __str__(self):
        return f"{self.asset} → {self.person}"
