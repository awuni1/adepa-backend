from django.core import exceptions as django_exceptions
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.permissions import IsHRorAdmin
from accounts.views import OrgScopedViewSet

from .models import OnboardingStage, OnboardingTaskTemplate, PersonOnboarding, PersonOnboardingTask
from .serializers import (
    OnboardingStageSerializer,
    OnboardingTaskTemplateSerializer,
    PersonOnboardingSerializer,
    PersonOnboardingTaskSerializer,
)


class ReadForOrgWriteForHRMixin:
    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [permissions.IsAuthenticated()]
        return [IsHRorAdmin()]


class OnboardingStageViewSet(ReadForOrgWriteForHRMixin, OrgScopedViewSet):
    serializer_class = OnboardingStageSerializer
    queryset = OnboardingStage.objects.all()


class OnboardingTaskTemplateViewSet(viewsets.ModelViewSet):
    serializer_class = OnboardingTaskTemplateSerializer
    permission_classes = [IsHRorAdmin]

    def get_queryset(self):
        return OnboardingTaskTemplate.objects.filter(stage__organisation=self.request.user.organisation)


class PersonOnboardingViewSet(viewsets.ModelViewSet):
    serializer_class = PersonOnboardingSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]
    pagination_class = None

    def get_queryset(self):
        user = self.request.user
        qs = (
            PersonOnboarding.objects.filter(person__organisation=user.organisation)
            .select_related("person", "current_stage")
            .prefetch_related("tasks__task_template")
        )
        if user.role not in ("hr", "admin"):
            qs = qs.filter(person__user=user)
        return qs

    def create(self, request, *args, **kwargs):
        if request.user.role not in ("hr", "admin"):
            return Response(status=status.HTTP_403_FORBIDDEN)
        from people.models import Person

        try:
            person = Person.objects.get(id=request.data.get("person"), organisation=request.user.organisation)
        except (Person.DoesNotExist, ValueError, TypeError, django_exceptions.ValidationError):
            return Response({"detail": "A valid person is required."}, status=400)
        first_stage = (
            OnboardingStage.objects.filter(organisation=request.user.organisation).order_by("sequence").first()
        )
        if not first_stage:
            return Response({"detail": "No onboarding stages configured yet."}, status=400)
        onboarding, created = PersonOnboarding.objects.get_or_create(
            person=person, defaults={"current_stage": first_stage}
        )
        if created:
            for template in first_stage.task_templates.all():
                PersonOnboardingTask.objects.create(person_onboarding=onboarding, task_template=template)
        return Response(PersonOnboardingSerializer(onboarding).data, status=201)

    @action(detail=True, methods=["post"], permission_classes=[IsHRorAdmin])
    def advance(self, request, pk=None):
        onboarding = self.get_object()
        next_stage = (
            OnboardingStage.objects.filter(
                organisation=onboarding.person.organisation, sequence__gt=onboarding.current_stage.sequence
            )
            .order_by("sequence")
            .first()
        )
        if not next_stage:
            onboarding.status = PersonOnboarding.Status.COMPLETED
            onboarding.completed_at = timezone.now()
            onboarding.save(update_fields=["status", "completed_at"])
            return Response(PersonOnboardingSerializer(onboarding).data)
        onboarding.current_stage = next_stage
        onboarding.save(update_fields=["current_stage"])
        for template in next_stage.task_templates.all():
            PersonOnboardingTask.objects.get_or_create(person_onboarding=onboarding, task_template=template)
        return Response(PersonOnboardingSerializer(onboarding).data)


class PersonOnboardingTaskViewSet(viewsets.ModelViewSet):
    serializer_class = PersonOnboardingTaskSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        qs = PersonOnboardingTask.objects.filter(person_onboarding__person__organisation=user.organisation)
        if user.role not in ("hr", "admin"):
            qs = qs.filter(person_onboarding__person__user=user)
        return qs

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        task = self.get_object()
        task.status = PersonOnboardingTask.Status.DONE
        task.completed_at = timezone.now()
        task.completed_by = request.user
        task.save(update_fields=["status", "completed_at", "completed_by"])
        return Response(PersonOnboardingTaskSerializer(task).data)
