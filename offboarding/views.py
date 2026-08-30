from datetime import date

from django.core import exceptions as django_exceptions
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.permissions import IsHRorAdmin
from accounts.views import OrgScopedViewSet
from people.models import Person

from .models import OffboardingStage, OffboardingTaskTemplate, PersonOffboarding, PersonOffboardingTask
from .serializers import (
    OffboardingStageSerializer,
    OffboardingTaskTemplateSerializer,
    PersonOffboardingSerializer,
    PersonOffboardingTaskSerializer,
)


class ReadForOrgWriteForHRMixin:
    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [permissions.IsAuthenticated()]
        return [IsHRorAdmin()]


class OffboardingStageViewSet(ReadForOrgWriteForHRMixin, OrgScopedViewSet):
    serializer_class = OffboardingStageSerializer
    queryset = OffboardingStage.objects.all()


class OffboardingTaskTemplateViewSet(viewsets.ModelViewSet):
    serializer_class = OffboardingTaskTemplateSerializer
    permission_classes = [IsHRorAdmin]

    def get_queryset(self):
        return OffboardingTaskTemplate.objects.filter(stage__organisation=self.request.user.organisation)


class PersonOffboardingViewSet(viewsets.ModelViewSet):
    serializer_class = PersonOffboardingSerializer
    permission_classes = [IsHRorAdmin]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        return (
            PersonOffboarding.objects.filter(person__organisation=self.request.user.organisation)
            .select_related("person", "current_stage")
            .prefetch_related("tasks__task_template")
        )

    def create(self, request, *args, **kwargs):
        try:
            person = Person.objects.get(id=request.data.get("person"), organisation=request.user.organisation)
        except (Person.DoesNotExist, ValueError, TypeError, django_exceptions.ValidationError):
            return Response({"detail": "A valid person is required."}, status=400)
        first_stage = (
            OffboardingStage.objects.filter(organisation=request.user.organisation).order_by("sequence").first()
        )
        if not first_stage:
            return Response({"detail": "No offboarding stages configured yet."}, status=400)
        offboarding, created = PersonOffboarding.objects.get_or_create(
            person=person,
            defaults={
                "current_stage": first_stage,
                "exit_reason": request.data.get("exit_reason", ""),
                "notice_starts": request.data.get("notice_starts"),
                "notice_ends": request.data.get("notice_ends"),
                "initiated_by": request.user,
            },
        )
        if created:
            for template in first_stage.task_templates.all():
                PersonOffboardingTask.objects.create(person_offboarding=offboarding, task_template=template)
        return Response(PersonOffboardingSerializer(offboarding).data, status=201)

    @action(detail=True, methods=["post"])
    def advance(self, request, pk=None):
        offboarding = self.get_object()
        next_stage = (
            OffboardingStage.objects.filter(
                organisation=offboarding.person.organisation, sequence__gt=offboarding.current_stage.sequence
            )
            .order_by("sequence")
            .first()
        )
        if not next_stage:
            offboarding.status = PersonOffboarding.Status.COMPLETED
            offboarding.completed_at = timezone.now()
            offboarding.save(update_fields=["status", "completed_at"])

            person = offboarding.person
            employment = getattr(person, "employment", None)
            if employment:
                employment.status = employment.__class__.Status.EXITED
                employment.end_date = employment.end_date or date.today()
                employment.save(update_fields=["status", "end_date"])
            person.lifecycle_stage = Person.LifecycleStage.ALUMNI
            person.save(update_fields=["lifecycle_stage"])

            return Response(PersonOffboardingSerializer(offboarding).data)
        offboarding.current_stage = next_stage
        offboarding.save(update_fields=["current_stage"])
        for template in next_stage.task_templates.all():
            PersonOffboardingTask.objects.get_or_create(person_offboarding=offboarding, task_template=template)
        return Response(PersonOffboardingSerializer(offboarding).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        offboarding = self.get_object()
        offboarding.status = PersonOffboarding.Status.CANCELLED
        offboarding.save(update_fields=["status"])
        return Response(PersonOffboardingSerializer(offboarding).data)


class PersonOffboardingTaskViewSet(viewsets.ModelViewSet):
    serializer_class = PersonOffboardingTaskSerializer
    permission_classes = [IsHRorAdmin]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        return PersonOffboardingTask.objects.filter(
            person_offboarding__person__organisation=self.request.user.organisation
        )

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        task = self.get_object()
        task.status = PersonOffboardingTask.Status.DONE
        task.completed_at = timezone.now()
        task.completed_by = request.user
        task.save(update_fields=["status", "completed_at", "completed_by"])
        return Response(PersonOffboardingTaskSerializer(task).data)
