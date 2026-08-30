from rest_framework import serializers

from .models import PayoutAccount, PayrollRun, Payslip, SalaryStructure


class SalaryStructureSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalaryStructure
        fields = [
            "id", "person", "base_salary", "currency", "allowances", "deductions",
            "effective_from", "effective_to",
        ]


class PayslipSerializer(serializers.ModelSerializer):
    person_name = serializers.SerializerMethodField()

    class Meta:
        model = Payslip
        fields = [
            "id", "run", "person", "person_name", "gross", "total_deductions", "net",
            "line_items", "pdf_file", "created_at",
            "transfer_status", "transfer_reference", "transfer_failure_reason", "paid_at",
        ]

    def get_person_name(self, obj):
        return f"{obj.person.first_name} {obj.person.last_name}"


class PayoutAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayoutAccount
        fields = ["id", "bank_code", "bank_name", "account_number", "account_name", "recipient_code", "created_at"]
        read_only_fields = ["account_name", "recipient_code"]


class PayrollRunSerializer(serializers.ModelSerializer):
    payslips = PayslipSerializer(many=True, read_only=True)

    class Meta:
        model = PayrollRun
        fields = ["id", "organisation", "period_year", "period_month", "status", "approved_by", "payslips"]
        read_only_fields = ["status", "approved_by"]


class CreatePayrollRunSerializer(serializers.Serializer):
    period_year = serializers.IntegerField()
    period_month = serializers.IntegerField(min_value=1, max_value=12)
