from rest_framework import generics, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from accounts.permissions import IsHRorAdmin
from notifications.events import emit
from people.models import Person

from .models import EmployeeDocument
from .serializers import (
    EmployeeDocumentSerializer,
    EmployeeProfileSerializer,
    ExitEmployeeSerializer,
    SelfProfileUpdateSerializer,
)


class EmployeeViewSet(ReadOnlyModelViewSet):
    """Directory (§7.3): hr/admin see everyone; managers see their team."""

    serializer_class = EmployeeProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["employment__department", "employment__status"]
    search_fields = ["first_name", "last_name", "email"]

    def get_queryset(self):
        user = self.request.user
        qs = (
            Person.objects.filter(organisation=user.organisation, employment__isnull=False)
            .select_related("employment__department", "employment__manager")
            .prefetch_related("documents", "role_history__department")
            .order_by("first_name", "last_name")
        )
        if user.role == "manager":
            qs = qs.filter(employment__manager__user=user)
        elif user.role not in ("hr", "admin"):
            qs = qs.filter(user=user)
        return qs

    @action(detail=True, methods=["patch"], url_path="employment", permission_classes=[IsHRorAdmin])
    def update_employment(self, request, pk=None):
        person = self.get_object()
        employment = person.employment
        from .models import RoleHistory

        title_changed = "job_title" in request.data and request.data["job_title"] != employment.job_title
        dept_changed = "department" in request.data and str(request.data["department"]) != str(employment.department_id)

        for field in ("job_title", "department", "manager"):
            if field in request.data:
                setattr(employment, f"{field}_id" if field in ("department", "manager") else field,
                        request.data[field])
        employment.save()

        if title_changed or dept_changed:
            RoleHistory.objects.create(
                person=person,
                job_title=employment.job_title,
                department=employment.department,
                effective_from=request.data.get("effective_from", employment.start_date),
                change_reason=request.data.get("change_reason", "adjustment"),
            )
        return Response(EmployeeProfileSerializer(person).data)

    @action(detail=True, methods=["post"], permission_classes=[IsHRorAdmin])
    def documents(self, request, pk=None):
        person = self.get_object()
        serializer = EmployeeDocumentSerializer(data={**request.data, "person": person.id})
        serializer.is_valid(raise_exception=True)
        serializer.save(uploaded_by=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], permission_classes=[IsHRorAdmin])
    def exit(self, request, pk=None):
        person = self.get_object()
        serializer = ExitEmployeeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        employment = person.employment
        employment.end_date = serializer.validated_data["end_date"]
        employment.status = employment.Status.EXITED
        employment.save(update_fields=["end_date", "status"])

        person.lifecycle_stage = Person.LifecycleStage.ALUMNI
        person.save(update_fields=["lifecycle_stage"])

        if person.user:
            person.user.is_active = False
            person.user.save(update_fields=["is_active"])

        emit("person.exited", {"person_id": str(person.id), "reason": serializer.validated_data["reason"]})
        return Response(status=status.HTTP_204_NO_CONTENT)


class MyProfileView(generics.RetrieveUpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        return EmployeeProfileSerializer if self.request.method == "GET" else SelfProfileUpdateSerializer

    def get_object(self):
        return self.request.user.person
