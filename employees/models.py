from cloudinary_storage.storage import RawMediaCloudinaryStorage
from django.db import models

from common.models import TimeStampedModel


class Employment(TimeStampedModel):
    class Status(models.TextChoices):
        ACTIVE = "active"
        ON_LEAVE = "on_leave"
        SUSPENDED = "suspended"
        EXITED = "exited"

    person = models.OneToOneField("people.Person", on_delete=models.CASCADE, related_name="employment")
    organisation = models.ForeignKey("orgs.Organisation", on_delete=models.CASCADE)
    department = models.ForeignKey("orgs.Department", on_delete=models.PROTECT)
    job_title = models.CharField(max_length=200)
    manager = models.ForeignKey(
        "people.Person", null=True, blank=True, on_delete=models.SET_NULL, related_name="reports"
    )
    employee_no = models.CharField(max_length=32)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.ACTIVE)
    hired_from_application = models.ForeignKey(
        "recruitment.Application", null=True, blank=True, on_delete=models.SET_NULL
    )


class EmployeeDocument(TimeStampedModel):
    person = models.ForeignKey("people.Person", on_delete=models.CASCADE, related_name="documents")
    kind = models.CharField(max_length=32)
    file = models.FileField(upload_to="employee-docs/%Y/", storage=RawMediaCloudinaryStorage())
    uploaded_by = models.ForeignKey("accounts.User", null=True, on_delete=models.SET_NULL)


class RoleHistory(TimeStampedModel):
    person = models.ForeignKey("people.Person", on_delete=models.CASCADE, related_name="role_history")
    job_title = models.CharField(max_length=200)
    department = models.ForeignKey("orgs.Department", on_delete=models.PROTECT)
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    change_reason = models.CharField(max_length=64)
