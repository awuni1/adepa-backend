from django.utils import timezone
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.permissions import IsHRorAdmin
from accounts.views import OrgScopedViewSet

from .models import Ticket, TicketComment, TicketType
from .serializers import TicketCommentSerializer, TicketSerializer, TicketTypeSerializer


class ReadForOrgWriteForHRMixin:
    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [permissions.IsAuthenticated()]
        return [IsHRorAdmin()]


class TicketTypeViewSet(ReadForOrgWriteForHRMixin, OrgScopedViewSet):
    serializer_class = TicketTypeSerializer
    queryset = TicketType.objects.all()


class TicketViewSet(OrgScopedViewSet):
    serializer_class = TicketSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["status", "priority", "ticket_type"]

    def get_queryset(self):
        user = self.request.user
        qs = (
            Ticket.objects.filter(organisation=user.organisation)
            .select_related("raised_by", "ticket_type", "assigned_to")
            .prefetch_related("comments__author")
        )
        if user.role not in ("hr", "admin"):
            qs = qs.filter(raised_by__user=user)
        return qs

    def perform_create(self, serializer):
        serializer.save(organisation=self.request.user.organisation, raised_by=self.request.user.person)

    @action(detail=True, methods=["post"], permission_classes=[IsHRorAdmin])
    def assign(self, request, pk=None):
        ticket = self.get_object()
        ticket.assigned_to_id = request.data.get("assigned_to")
        ticket.status = Ticket.Status.IN_PROGRESS
        ticket.save(update_fields=["assigned_to", "status"])
        return Response(TicketSerializer(ticket).data)

    @action(detail=True, methods=["post"], permission_classes=[IsHRorAdmin])
    def resolve(self, request, pk=None):
        ticket = self.get_object()
        ticket.status = Ticket.Status.RESOLVED
        ticket.resolved_at = timezone.now()
        ticket.save(update_fields=["status", "resolved_at"])
        return Response(TicketSerializer(ticket).data)

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        ticket = self.get_object()
        ticket.status = Ticket.Status.CLOSED
        ticket.save(update_fields=["status"])
        return Response(TicketSerializer(ticket).data)


class TicketCommentViewSet(viewsets.ModelViewSet):
    serializer_class = TicketCommentSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        return TicketComment.objects.filter(ticket__organisation=self.request.user.organisation)

    def perform_create(self, serializer):
        serializer.save(author=self.request.user.person)
