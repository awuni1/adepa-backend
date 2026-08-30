from datetime import date

from django.db import transaction
from django.utils import timezone

from notifications.events import emit
from payroll.models import SalaryStructure
from people.models import Person

from .models import Employment, RoleHistory


def _next_employee_no(organisation) -> str:
    year = timezone.now().year
    count = Employment.objects.filter(organisation=organisation, start_date__year=year).count() + 1
    return f"ADP-{year}-{count:04d}"


@transaction.atomic
def hire_from_application(
    application,
    job_title: str,
    department_id,
    start_date: date,
    base_salary,
    manager_id=None,
    allowances=None,
    deductions=None,
):
    """Flow C (§2.3): transition Person -> employee, create Employment, wire up
    payroll/leave from the contract. Nothing already on the record — CV,
    interview notes, scorecards — is re-entered."""

    person: Person = application.person
    person.lifecycle_stage = Person.LifecycleStage.EMPLOYEE
    person.save(update_fields=["lifecycle_stage"])

    employment = Employment.objects.create(
        person=person,
        organisation=application.job.organisation,
        department_id=department_id,
        job_title=job_title,
        manager_id=manager_id,
        employee_no=_next_employee_no(application.job.organisation),
        start_date=start_date,
        hired_from_application=application,
    )

    RoleHistory.objects.create(
        person=person,
        job_title=job_title,
        department_id=department_id,
        effective_from=start_date,
        change_reason="hire",
    )

    SalaryStructure.objects.create(
        person=person,
        base_salary=base_salary,
        allowances=allowances or [],
        deductions=deductions or [],
        effective_from=start_date,
    )

    application.stage = application.Stage.HIRED
    application.save(update_fields=["stage"])

    emit("person.hired", {"person_id": str(person.id), "employment_id": str(employment.id)})
    return employment
