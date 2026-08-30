from django.utils import timezone
from rest_framework import generics, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.permissions import IsHRorAdmin
from accounts.views import OrgScopedViewSet

from .models import Asset, AssetAssignment, AssetCategory
from .serializers import AssetAssignmentSerializer, AssetCategorySerializer, AssetSerializer


class ReadForOrgWriteForHRMixin:
    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [permissions.IsAuthenticated()]
        return [IsHRorAdmin()]


class AssetCategoryViewSet(ReadForOrgWriteForHRMixin, OrgScopedViewSet):
    serializer_class = AssetCategorySerializer
    queryset = AssetCategory.objects.all()


class AssetViewSet(OrgScopedViewSet):
    serializer_class = AssetSerializer
    permission_classes = [IsHRorAdmin]
    queryset = Asset.objects.all()
    filterset_fields = ["status", "category"]


class AssetAssignmentViewSet(viewsets.ModelViewSet):
    serializer_class = AssetAssignmentSerializer
    permission_classes = [IsHRorAdmin]
    http_method_names = ["get", "post", "head", "options"]
    filterset_fields = ["status", "person"]

    def get_queryset(self):
        return AssetAssignment.objects.filter(
            asset__organisation=self.request.user.organisation
        ).select_related("asset", "person")

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        asset = Asset.objects.get(id=response.data["asset"])
        asset.status = Asset.Status.ASSIGNED
        asset.save(update_fields=["status"])
        return response

    def perform_create(self, serializer):
        serializer.save(assigned_by=self.request.user)

    @action(detail=True, methods=["post"])
    def mark_returned(self, request, pk=None):
        assignment = self.get_object()
        assignment.status = AssetAssignment.Status.RETURNED
        assignment.return_date = timezone.localdate()
        assignment.return_condition = request.data.get("return_condition", "")
        assignment.save(update_fields=["status", "return_date", "return_condition"])
        assignment.asset.status = Asset.Status.AVAILABLE
        assignment.asset.save(update_fields=["status"])
        return Response(AssetAssignmentSerializer(assignment).data)


class MyAssetsView(generics.ListAPIView):
    serializer_class = AssetAssignmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        return AssetAssignment.objects.filter(person__user=self.request.user).select_related("asset", "person")
