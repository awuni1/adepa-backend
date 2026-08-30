from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    MyPayoutAccountView,
    MyPayslipsView,
    PaystackBanksView,
    PaystackWebhookView,
    PayrollRunViewSet,
    PayslipViewSet,
    SalaryStructureViewSet,
)

router = DefaultRouter()
router.register("payroll/salary-structures", SalaryStructureViewSet, basename="salary-structure")
router.register("payroll/runs", PayrollRunViewSet, basename="payroll-run")
router.register("payroll/payslips", PayslipViewSet, basename="payslip")

urlpatterns = [
    path("payroll/payslips/me/", MyPayslipsView.as_view(), name="my-payslips"),
    path("payroll/payout-account/me/", MyPayoutAccountView.as_view(), name="my-payout-account"),
    path("payroll/banks/", PaystackBanksView.as_view(), name="paystack-banks"),
    path("payroll/webhooks/paystack/", PaystackWebhookView.as_view(), name="paystack-webhook"),
    *router.urls,
]
