from rest_framework import generics

from accounts.permissions import IsHRorAdmin

from .models import AuditLog
from .serializers import AuditLogSerializer


class AuditLogListView(generics.ListAPIView):
    serializer_class = AuditLogSerializer
    permission_classes = [IsHRorAdmin]
    filterset_fields = ["model_name", "action"]

    def get_queryset(self):
        return AuditLog.objects.filter(organisation=self.request.user.organisation).select_related("actor")
