from celery import shared_task


@shared_task
def process_payroll_run(payroll_run_id):
    from .models import PayrollRun
    from .services import run_payroll

    payroll_run = PayrollRun.objects.get(id=payroll_run_id)
    payroll_run.status = PayrollRun.Status.PROCESSING
    payroll_run.save(update_fields=["status"])

    run_payroll(payroll_run)

    payroll_run.status = PayrollRun.Status.DRAFT
    payroll_run.save(update_fields=["status"])


@shared_task
def generate_payslip_pdfs(payroll_run_id):
    """Renders each Payslip to a WeasyPrint PDF and uploads it (§3, §7.5)."""
    from django.core.files.base import ContentFile
    from django.template.loader import render_to_string
    from weasyprint import HTML

    from notifications.events import emit

    from .models import Payslip

    for payslip in Payslip.objects.filter(run_id=payroll_run_id):
        html = render_to_string("payroll/payslip.html", {"payslip": payslip})
        pdf_bytes = HTML(string=html).write_pdf()
        payslip.pdf_file.save(f"payslip-{payslip.id}.pdf", ContentFile(pdf_bytes), save=True)
        emit("payslip.issued", {"payslip_id": str(payslip.id), "person_id": str(payslip.person_id)})


@shared_task
def disburse_payroll_run(payroll_run_id):
    """Pays out every payslip in an approved run via Paystack Transfers.
    A payslip only ever reaches `transfer_status=success` from the Paystack
    webhook once the transfer has actually settled — this task's job is just
    to *request* each transfer and record that it's pending (or why it
    couldn't be requested at all)."""
    import uuid

    from . import paystack
    from .models import Payslip, PayrollRun

    payroll_run = PayrollRun.objects.get(id=payroll_run_id)
    # Retrying a run (e.g. after fixing a missing bank account) must never
    # re-pay someone whose transfer already succeeded or is in flight.
    already_settled = {Payslip.TransferStatus.PENDING, Payslip.TransferStatus.SUCCESS}

    for payslip in payroll_run.payslips.select_related("person__payout_account"):
        if payslip.transfer_status in already_settled:
            continue

        account = getattr(payslip.person, "payout_account", None)
        if not account or not account.recipient_code:
            payslip.transfer_status = Payslip.TransferStatus.SKIPPED
            payslip.transfer_failure_reason = "No payout bank account on file."
            payslip.save(update_fields=["transfer_status", "transfer_failure_reason"])
            continue

        reference = f"payslip-{payslip.id}-{uuid.uuid4().hex[:8]}"
        try:
            result = paystack.initiate_transfer(
                amount=payslip.net,
                recipient_code=account.recipient_code,
                reference=reference,
                reason=f"Salary — {payroll_run.period_month}/{payroll_run.period_year}",
            )
            payslip.transfer_status = Payslip.TransferStatus.PENDING
            payslip.transfer_reference = result.get("reference", reference)
            payslip.transfer_failure_reason = ""
        except ValueError as exc:
            payslip.transfer_status = Payslip.TransferStatus.FAILED
            payslip.transfer_failure_reason = str(exc)
        payslip.save(update_fields=["transfer_status", "transfer_reference", "transfer_failure_reason"])
