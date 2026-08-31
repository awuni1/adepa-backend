from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "admin"
        HR = "hr"
        MANAGER = "manager"
        EMPLOYEE = "employee"
        CANDIDATE = "candidate"

    role = models.CharField(max_length=12, choices=Role.choices, default=Role.EMPLOYEE)
    organisation = models.ForeignKey(
        "orgs.Organisation", null=True, blank=True, on_delete=models.CASCADE, related_name="users"
    )
    # Set when a login is provisioned with a system-generated password (e.g.
    # a new hire's welcome email) — the frontend forces a change-password
    # screen before anything else while this is true.
    must_change_password = models.BooleanField(default=False)

    def __str__(self):
        return self.get_full_name() or self.username
