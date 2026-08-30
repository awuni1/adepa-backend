from rest_framework import generics, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from accounts.permissions import IsHRorAdmin

from . import paystack
from .models import PayoutAccount, PayrollRun, Payslip, SalaryStructure
from .serializers import (
    CreatePayrollRunSerializer,
    PayoutAccountSerializer,
    PayrollRunSerializer,
    PayslipSerializer,
    SalaryStructureSerializer,
)
from .tasks import disburse_payroll_run, generate_payslip_pdfs, process_payroll_run


class SalaryStructureViewSet(ModelViewSet):
    serializer_class = SalaryStructureSerializer
    permission_classes = [IsHRorAdmin]

    def get_queryset(self):
        return SalaryStructure.objects.filter(person__organisation=self.request.user.organisation)


class PayrollRunViewSet(ModelViewSet):
    serializer_class = PayrollRunSerializer
    permission_classes = [IsHRorAdmin]

    def get_queryset(self):
        return PayrollRun.objects.filter(organisation=self.request.user.organisation).prefetch_related(
            "payslips__person"
        )

    def create(self, request, *args, **kwargs):
        serializer = CreatePayrollRunSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payroll_run = PayrollRun.objects.create(organisation=request.user.organisation, **serializer.validated_data)
        process_payroll_run.delay(str(payroll_run.id))
        return Response(PayrollRunSerializer(payroll_run).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        payroll_run = self.get_object()
        payroll_run.status = PayrollRun.Status.APPROVED
        payroll_run.approved_by = request.user
        payroll_run.save(update_fields=["status", "approved_by"])
        generate_payslip_pdfs.delay(str(payroll_run.id))
        return Response(PayrollRunSerializer(payroll_run).data)

    @action(detail=True, methods=["post"])
    def disburse(self, request, pk=None):
        payroll_run = self.get_object()
        if payroll_run.status != PayrollRun.Status.APPROVED:
            return Response({"detail": "Only approved runs can be disbursed."}, status=status.HTTP_400_BAD_REQUEST)
        disburse_payroll_run.delay(str(payroll_run.id))
        return Response(PayrollRunSerializer(payroll_run).data)


class PayslipViewSet(ReadOnlyModelViewSet):
    serializer_class = PayslipSerializer
    permission_classes = [IsHRorAdmin]
    filterset_fields = ["person", "run"]

    def get_queryset(self):
        return Payslip.objects.filter(person__organisation=self.request.user.organisation).select_related("person")


class MyPayslipsView(generics.ListAPIView):
    serializer_class = PayslipSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        return Payslip.objects.filter(person=self.request.user.person).select_related("person")


class MyPayoutAccountView(APIView):
    """Self-service bank-account setup for salary disbursement. Registering
    (or replacing) an account resolves it with Paystack first — so the
    employee sees whose name it's actually registered under before we ever
    create a transfer recipient for it — then mints that recipient."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        account = PayoutAccount.objects.filter(person=request.user.person).first()
        if not account:
            return Response(None)
        return Response(PayoutAccountSerializer(account).data)

    def put(self, request):
        bank_code = request.data.get("bank_code")
        bank_name = request.data.get("bank_name", "")
        account_number = request.data.get("account_number")
        if not bank_code or not account_number:
            return Response({"detail": "Bank and account number are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            resolved = paystack.resolve_account_number(account_number, bank_code)
            recipient = paystack.create_transfer_recipient(
                name=resolved["account_name"], account_number=account_number, bank_code=bank_code,
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        account, _ = PayoutAccount.objects.update_or_create(
            person=request.user.person,
            defaults={
                "bank_code": bank_code,
                "bank_name": bank_name,
                "account_number": account_number,
                "account_name": resolved["account_name"],
                "recipient_code": recipient["recipient_code"],
            },
        )
        return Response(PayoutAccountSerializer(account).data)


class PaystackBanksView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            return Response(paystack.list_banks())
        except Exception:
            return Response({"detail": "Couldn't reach Paystack — try again shortly."}, status=status.HTTP_502_BAD_GATEWAY)


class PaystackWebhookView(APIView):
    """Receives Paystack's transfer.* events — the only place a Payslip is
    ever marked `success`. Disbursing (see `disburse_payroll_run`) only ever
    *requests* a transfer; whether it actually landed is decided here."""

    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        import json

        from django.utils import timezone

        signature = request.headers.get("x-paystack-signature")
        if not paystack.verify_webhook_signature(request.body, signature):
            return Response(status=status.HTTP_403_FORBIDDEN)

        event = json.loads(request.body)
        event_type = event.get("event")
        data = event.get("data", {})
        reference = data.get("reference")
        if not reference:
            return Response(status=status.HTTP_200_OK)

        payslip = Payslip.objects.filter(transfer_reference=reference).select_related("run").first()
        if not payslip:
            return Response(status=status.HTTP_200_OK)

        if event_type == "transfer.success":
            payslip.transfer_status = Payslip.TransferStatus.SUCCESS
            payslip.paid_at = timezone.now()
            payslip.save(update_fields=["transfer_status", "paid_at"])
        elif event_type in ("transfer.failed", "transfer.reversed"):
            payslip.transfer_status = Payslip.TransferStatus.FAILED
            payslip.transfer_failure_reason = data.get("message") or event_type
            payslip.save(update_fields=["transfer_status", "transfer_failure_reason"])
        else:
            return Response(status=status.HTTP_200_OK)

        run = payslip.run
        statuses = set(run.payslips.values_list("transfer_status", flat=True))
        if statuses and statuses <= {Payslip.TransferStatus.SUCCESS, Payslip.TransferStatus.SKIPPED}:
            run.status = PayrollRun.Status.PAID
            run.save(update_fields=["status"])

        return Response(status=status.HTTP_200_OK)
