from rest_framework import permissions, viewsets

from accounts.permissions import IsHRorAdmin
from accounts.views import OrgScopedViewSet

from .models import Announcement, Department, Organisation, PolicyDocument
from .serializers import (
    AnnouncementSerializer,
    DepartmentSerializer,
    OrganisationSerializer,
    PolicyDocumentSerializer,
)


class OrganisationViewSet(viewsets.ModelViewSet):
    """Admin-only: an org manages its own record, never lists others."""

    serializer_class = OrganisationSerializer
    permission_classes = [IsHRorAdmin]

    def get_queryset(self):
        return Organisation.objects.filter(id=self.request.user.organisation_id)


class DepartmentViewSet(OrgScopedViewSet):
    serializer_class = DepartmentSerializer
    permission_classes = [IsHRorAdmin]
    queryset = Department.objects.all()


class ReadForOrgWriteForHRMixin:
    """List/retrieve: any authenticated member of the org. Write: hr/admin only."""

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [permissions.IsAuthenticated()]
        return [IsHRorAdmin()]


class AnnouncementViewSet(ReadForOrgWriteForHRMixin, OrgScopedViewSet):
    serializer_class = AnnouncementSerializer
    queryset = Announcement.objects.all()

    def perform_create(self, serializer):
        serializer.save(organisation=self.request.user.organisation, created_by=self.request.user)


class PolicyDocumentViewSet(ReadForOrgWriteForHRMixin, OrgScopedViewSet):
    serializer_class = PolicyDocumentSerializer
    queryset = PolicyDocument.objects.all()

    def perform_create(self, serializer):
        serializer.save(organisation=self.request.user.organisation, uploaded_by=self.request.user)
