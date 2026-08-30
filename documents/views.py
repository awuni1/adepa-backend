from django.utils import timezone
from rest_framework import generics, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.permissions import IsHRorAdmin
from accounts.views import OrgScopedViewSet

from .models import DocumentRequest
from .serializers import DeclineDocumentSerializer, DocumentRequestSerializer, SignDocumentSerializer


class DocumentRequestViewSet(OrgScopedViewSet):
    serializer_class = DocumentRequestSerializer
    permission_classes = [IsHRorAdmin]
    http_method_names = ["get", "post", "head", "options"]
    filterset_fields = ["status", "person"]
    queryset = DocumentRequest.objects.select_related("person")

    def perform_create(self, serializer):
        serializer.save(organisation=self.request.user.organisation, requested_by=self.request.user)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def sign(self, request, pk=None):
        doc = self.get_object()
        if doc.person.user_id != request.user.id:
            return Response(status=403)
        serializer = SignDocumentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        doc.status = DocumentRequest.Status.SIGNED
        doc.signature_name = serializer.validated_data["signature_name"]
        doc.signed_at = timezone.now()
        doc.signed_ip = request.META.get("REMOTE_ADDR")
        doc.save(update_fields=["status", "signature_name", "signed_at", "signed_ip"])
        return Response(DocumentRequestSerializer(doc).data)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def decline(self, request, pk=None):
        doc = self.get_object()
        if doc.person.user_id != request.user.id:
            return Response(status=403)
        serializer = DeclineDocumentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        doc.status = DocumentRequest.Status.DECLINED
        doc.declined_reason = serializer.validated_data.get("reason", "")
        doc.save(update_fields=["status", "declined_reason"])
        return Response(DocumentRequestSerializer(doc).data)


class MyDocumentRequestsView(generics.ListAPIView):
    serializer_class = DocumentRequestSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        return DocumentRequest.objects.filter(person__user=self.request.user).select_related("person")
