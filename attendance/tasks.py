from celery import shared_task
from django.utils import timezone

from .models import AttendanceRecord, LeaveBalance, LeaveType


@shared_task
def close_day():
    """Beat job (23:55 daily, §5.1): marks anyone without a clock-in today absent."""
    from people.models import Person

    today = timezone.localdate()
    employed = Person.objects.filter(lifecycle_stage=Person.LifecycleStage.EMPLOYEE, employment__status="active")
    clocked_in_ids = AttendanceRecord.objects.filter(date=today).values_list("person_id", flat=True)
    for person in employed.exclude(id__in=clocked_in_ids):
        AttendanceRecord.objects.create(person=person, date=today, status="absent")


@shared_task
def accrue_leave():
    """Beat job (1st of month, §5.1): credits monthly leave accrual per LeaveType."""
    from people.models import Person

    year = timezone.localdate().year
    for leave_type in LeaveType.objects.all():
        monthly = leave_type.days_per_year / 12
        people = Person.objects.filter(
            organisation=leave_type.organisation,
            lifecycle_stage=Person.LifecycleStage.EMPLOYEE,
        )
        for person in people:
            balance, _ = LeaveBalance.objects.get_or_create(
                person=person, leave_type=leave_type, year=year, defaults={"entitled": 0}
            )
            balance.entitled += monthly
            balance.save(update_fields=["entitled"])
