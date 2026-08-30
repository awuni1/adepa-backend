from django.db.models.signals import post_save, pre_save

from .middleware import get_current_user
from .models import AuditLog

# Only these fields are watched per model — keeps the log focused on the
# changes that actually matter for HR compliance, not every touched column.
TRACKED = {
    "employees.Employment": ["status", "job_title", "department_id", "manager_id", "end_date"],
    "payroll.SalaryStructure": ["base_salary", "effective_from"],
    "performance.PerformanceReview": ["status"],
    "payroll.PayrollRun": ["status"],
}


def _label(model):
    return f"{model._meta.app_label}.{model.__name__}"


def _org_for(instance, model_label):
    if model_label == "employees.Employment":
        return instance.organisation_id
    if model_label == "payroll.SalaryStructure":
        return instance.person.organisation_id
    if model_label == "performance.PerformanceReview":
        return instance.cycle.organisation_id
    if model_label == "payroll.PayrollRun":
        return instance.organisation_id
    return None


def _pre_save(sender, instance, **kwargs):
    label = _label(sender)
    if label not in TRACKED or not instance.pk:
        return
    try:
        instance._audit_old = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        instance._audit_old = None


def _post_save(sender, instance, created, **kwargs):
    label = _label(sender)
    fields = TRACKED.get(label)
    if not fields:
        return

    user = get_current_user()
    actor = user if (user and getattr(user, "is_authenticated", False)) else None

    if created:
        AuditLog.objects.create(
            organisation_id=_org_for(instance, label),
            actor=actor,
            model_name=label,
            object_id=str(instance.pk),
            object_repr=str(instance)[:255],
            action=AuditLog.Action.CREATE,
        )
        return

    old = getattr(instance, "_audit_old", None)
    if not old:
        return
    changes = {}
    for field in fields:
        old_val, new_val = getattr(old, field, None), getattr(instance, field, None)
        if old_val != new_val:
            changes[field] = {"old": str(old_val), "new": str(new_val)}
    if changes:
        AuditLog.objects.create(
            organisation_id=_org_for(instance, label),
            actor=actor,
            model_name=label,
            object_id=str(instance.pk),
            object_repr=str(instance)[:255],
            action=AuditLog.Action.UPDATE,
            changes=changes,
        )


def connect():
    from django.apps import apps

    for label in TRACKED:
        app_label, model_name = label.split(".")
        model = apps.get_model(app_label, model_name)
        pre_save.connect(_pre_save, sender=model, weak=False)
        post_save.connect(_post_save, sender=model, weak=False)
