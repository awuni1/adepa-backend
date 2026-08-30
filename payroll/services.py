"""Payroll calculation (§7.5): base (prorated) -> + allowances -> gross ->
- percentage deductions -> - fixed deductions -> - PAYE -> net. Every figure
is frozen into Payslip.line_items so historical payslips never drift when a
SalaryStructure is later edited."""

from calendar import monthrange
from decimal import Decimal

from django.utils import timezone

# Configurable PAYE bracket table (GRA-style), stored per-org in a real
# deployment; kept as a flat default here so the scaffold runs end-to-end.
PAYE_BRACKETS = [
    (Decimal("500"), Decimal("0.00")),
    (Decimal("1000"), Decimal("0.05")),
    (Decimal("Infinity"), Decimal("0.175")),
]


def _paye(taxable: Decimal) -> Decimal:
    remaining = taxable
    tax = Decimal("0")
    lower = Decimal("0")
    for upper, rate in PAYE_BRACKETS:
        band = min(remaining, upper - lower)
        if band <= 0:
            break
        tax += band * rate
        remaining -= band
        lower = upper
    return tax.quantize(Decimal("0.01"))


def calculate_payslip(structure, period_year: int, period_month: int, unpaid_leave_days: Decimal = Decimal("0")):
    days_in_month = monthrange(period_year, period_month)[1]
    daily_rate = structure.base_salary / days_in_month
    prorated_base = structure.base_salary - (daily_rate * unpaid_leave_days)

    allowances_total = sum((Decimal(str(a["amount"])) for a in structure.allowances), Decimal("0"))
    gross = prorated_base + allowances_total

    line_items = [
        {"label": "Base salary (prorated)", "amount": str(prorated_base)},
        *[{"label": a["name"], "amount": str(a["amount"])} for a in structure.allowances],
        {"label": "Gross", "amount": str(gross)},
    ]

    running = gross
    for d in structure.deductions:
        if "percent" in d:
            amount = (gross * Decimal(str(d["percent"])) / 100).quantize(Decimal("0.01"))
        else:
            amount = Decimal(str(d["amount"]))
        running -= amount
        line_items.append({"label": d["name"], "amount": str(-amount)})

    paye = _paye(running)
    line_items.append({"label": "PAYE", "amount": str(-paye)})
    net = running - paye

    total_deductions = gross - net

    return {
        "gross": gross.quantize(Decimal("0.01")),
        "total_deductions": total_deductions.quantize(Decimal("0.01")),
        "net": net.quantize(Decimal("0.01")),
        "line_items": line_items,
    }


def run_payroll(payroll_run):
    from employees.models import Employment

    from .models import Payslip, SalaryStructure

    period_start = timezone.datetime(payroll_run.period_year, payroll_run.period_month, 1).date()
    employments = Employment.objects.filter(organisation=payroll_run.organisation, status="active")

    for employment in employments:
        structure = (
            SalaryStructure.objects.filter(person=employment.person, effective_from__lte=period_start)
            .order_by("-effective_from")
            .first()
        )
        if not structure:
            continue
        result = calculate_payslip(structure, payroll_run.period_year, payroll_run.period_month)
        Payslip.objects.update_or_create(
            run=payroll_run,
            person=employment.person,
            defaults=result,
        )
