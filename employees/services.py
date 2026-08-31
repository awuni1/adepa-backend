from datetime import date

from django.db import transaction
from django.utils import timezone
from django.utils.crypto import get_random_string

from accounts.models import User
from notifications.events import emit
from payroll.models import SalaryStructure
from people.models import Person

from .models import Employment, RoleHistory

# Excludes visually-ambiguous characters (0/O, 1/l/I) since this gets typed
# from an email, not pasted.
_PASSWORD_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789"


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

    # Provision a login only if this person doesn't already have one — an
    # existing employee applying to an internal posting keeps their real
    # account and password untouched; only a genuinely new hire gets a
    # system-generated temporary one, emailed via person.hired below.
    temp_password = None
    if person.user_id is None:
        temp_password = get_random_string(12, _PASSWORD_ALPHABET)
        user = User.objects.create_user(
            username=person.email,
            email=person.email,
            password=temp_password,
            role=User.Role.EMPLOYEE,
            organisation=application.job.organisation,
            first_name=person.first_name,
            last_name=person.last_name,
            must_change_password=True,
        )
        person.user = user
        person.save(update_fields=["user"])

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

    # temp_password (only set when a login was actually provisioned above)
    # rides in the event payload purely so the welcome email can include it —
    # it's never written to the database. It does sit briefly in the Celery
    # broker until the email task picks it up, which is the one real
    # tradeoff of this pattern; the password is forced to be changed on
    # first login regardless.
    emit(
        "person.hired",
        {"person_id": str(person.id), "employment_id": str(employment.id), "temp_password": temp_password},
    )
    return employment
