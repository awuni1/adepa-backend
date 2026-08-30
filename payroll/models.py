from cloudinary_storage.storage import RawMediaCloudinaryStorage
from django.db import models

from common.models import TimeStampedModel


class SalaryStructure(TimeStampedModel):
    person = models.ForeignKey("people.Person", on_delete=models.CASCADE, related_name="salary_structures")
    base_salary = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="GHS")
    allowances = models.JSONField(default=list)
    deductions = models.JSONField(default=list)
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)


class PayrollRun(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft"
        PROCESSING = "processing"
        APPROVED = "approved"
        PAID = "paid"

    organisation = models.ForeignKey("orgs.Organisation", on_delete=models.CASCADE)
    period_year = models.PositiveSmallIntegerField()
    period_month = models.PositiveSmallIntegerField()
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)
    approved_by = models.ForeignKey("accounts.User", null=True, on_delete=models.SET_NULL)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organisation", "period_year", "period_month"], name="uniq_payroll_period"
            )
        ]


class Payslip(TimeStampedModel):
    class TransferStatus(models.TextChoices):
        NOT_INITIATED = "not_initiated"
        PENDING = "pending"
        SUCCESS = "success"
        FAILED = "failed"
        SKIPPED = "skipped"  # no PayoutAccount on file for this person

    run = models.ForeignKey(PayrollRun, on_delete=models.CASCADE, related_name="payslips")
    person = models.ForeignKey("people.Person", on_delete=models.CASCADE, related_name="payslips")
    gross = models.DecimalField(max_digits=12, decimal_places=2)
    total_deductions = models.DecimalField(max_digits=12, decimal_places=2)
    net = models.DecimalField(max_digits=12, decimal_places=2)
    line_items = models.JSONField(default=list)
    pdf_file = models.FileField(upload_to="payslips/%Y/%m/", null=True, blank=True, storage=RawMediaCloudinaryStorage())
    transfer_status = models.CharField(max_length=16, choices=TransferStatus.choices, default=TransferStatus.NOT_INITIATED)
    transfer_reference = models.CharField(max_length=64, blank=True)
    transfer_failure_reason = models.CharField(max_length=255, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)


class PayoutAccount(TimeStampedModel):
    """A person's bank account for salary disbursement via Paystack Transfers.
    Set up self-service by the employee (like their other 'My…' resources);
    `recipient_code` is Paystack's own id for the recipient, minted once via
    the Transfer Recipient API and then reused for every future payout."""

    person = models.OneToOneField("people.Person", on_delete=models.CASCADE, related_name="payout_account")
    bank_code = models.CharField(max_length=16)
    bank_name = models.CharField(max_length=120)
    account_number = models.CharField(max_length=32)
    account_name = models.CharField(max_length=150, blank=True)
    recipient_code = models.CharField(max_length=64, blank=True)
