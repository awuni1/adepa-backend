from django.db.models import Q
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from accounts.permissions import IsManagerOrHRorAdmin
from notifications.events import emit

from .geofencing import within_any_zone
from .models import AttendanceRecord, GeofenceZone, LeaveBalance, LeaveRequest, LeaveType
from .serializers import (
    AttendanceRecordSerializer,
    GeofenceZoneSerializer,
    LeaveBalanceSerializer,
    LeaveRequestSerializer,
    LeaveTypeSerializer,
)

GRACE_MINUTES = 15
GRACE_HOUR = 9  # org start-of-day, kept simple for the scaffold


class ClockInView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        person = request.user.person
        lat, lng = request.data.get("lat"), request.data.get("lng")

        zones = GeofenceZone.objects.filter(organisation=person.organisation, is_active=True)
        if zones.exists():
            if lat is None or lng is None:
                return Response({"code": "location_required"}, status=status.HTTP_400_BAD_REQUEST)
            if not within_any_zone(float(lat), float(lng), zones):
                return Response({"code": "outside_geofence"}, status=status.HTTP_403_FORBIDDEN)

        today = timezone.localdate()
        record, _ = AttendanceRecord.objects.get_or_create(person=person, date=today)
        if record.clock_in:
            return Response({"code": "already_clocked_in"}, status=status.HTTP_409_CONFLICT)
        now = timezone.now()
        record.clock_in = now
        record.status = "late" if now.hour > GRACE_HOUR or (now.hour == GRACE_HOUR and now.minute > GRACE_MINUTES) else "present"
        if lat is not None and lng is not None:
            record.clock_in_lat, record.clock_in_lng = float(lat), float(lng)
            record.save(update_fields=["clock_in", "status", "clock_in_lat", "clock_in_lng"])
        else:
            record.save(update_fields=["clock_in", "status"])
        return Response(AttendanceRecordSerializer(record).data)


class GeofenceZoneViewSet(ModelViewSet):
    serializer_class = GeofenceZoneSerializer
    permission_classes = [IsManagerOrHRorAdmin]

    def get_queryset(self):
        return GeofenceZone.objects.filter(organisation=self.request.user.organisation)

    def perform_create(self, serializer):
        serializer.save(organisation=self.request.user.organisation)


class ClockOutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        person = request.user.person
        today = timezone.localdate()
        try:
            record = AttendanceRecord.objects.get(person=person, date=today)
        except AttendanceRecord.DoesNotExist:
            return Response({"code": "not_clocked_in"}, status=status.HTTP_409_CONFLICT)
        record.clock_out = timezone.now()
        record.save(update_fields=["clock_out"])
        return Response(AttendanceRecordSerializer(record).data)


class MyAttendanceView(generics.ListAPIView):
    serializer_class = AttendanceRecordSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        qs = AttendanceRecord.objects.filter(person=self.request.user.person)
        month = self.request.query_params.get("month")
        if month:
            year, mon = month.split("-")
            qs = qs.filter(date__year=year, date__month=mon)
        return qs


class AttendanceViewSet(ReadOnlyModelViewSet):
    serializer_class = AttendanceRecordSerializer
    permission_classes = [IsManagerOrHRorAdmin]
    filterset_fields = ["person", "person__employment__department", "date"]

    def get_queryset(self):
        return AttendanceRecord.objects.filter(
            person__organisation=self.request.user.organisation
        ).select_related("person")


class LeaveTypeViewSet(ModelViewSet):
    serializer_class = LeaveTypeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [permissions.IsAuthenticated()]
        return [IsManagerOrHRorAdmin()]

    def get_queryset(self):
        return LeaveType.objects.filter(organisation=self.request.user.organisation)

    def perform_create(self, serializer):
        serializer.save(organisation=self.request.user.organisation)


class LeaveRequestViewSet(ModelViewSet):
    serializer_class = LeaveRequestSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["status", "person"]

    def get_queryset(self):
        user = self.request.user
        qs = LeaveRequest.objects.filter(person__organisation=user.organisation).select_related(
            "person", "leave_type"
        )
        if user.role in ("hr", "admin"):
            return qs
        if self.request.query_params.get("mine_to_approve") == "true":
            return qs.filter(person__employment__manager__user=user)
        # Own requests, plus (for managers) requests from direct reports — the latter
        # is needed so approve/reject's get_object() can find the request even though
        # those detail actions aren't hitting the list endpoint with ?mine_to_approve=true.
        visible = Q(person__user=user)
        if user.role == "manager":
            visible |= Q(person__employment__manager__user=user)
        return qs.filter(visible)

    def perform_create(self, serializer):
        leave_request = serializer.save(person=self.request.user.person)
        emit("leave.requested", {"leave_request_id": str(leave_request.id)})

    @action(detail=True, methods=["post"], permission_classes=[IsManagerOrHRorAdmin])
    def approve(self, request, pk=None):
        leave_request = self.get_object()
        balance = LeaveBalance.objects.get(
            person=leave_request.person, leave_type=leave_request.leave_type, year=leave_request.start_date.year
        )
        balance.taken += leave_request.days
        balance.save(update_fields=["taken"])

        leave_request.status = LeaveRequest.Status.APPROVED
        leave_request.approver = request.user.person
        leave_request.decided_at = timezone.now()
        leave_request.save(update_fields=["status", "approver", "decided_at"])
        emit("leave.approved", {"leave_request_id": str(leave_request.id)})
        return Response(LeaveRequestSerializer(leave_request).data)

    @action(detail=True, methods=["post"], permission_classes=[IsManagerOrHRorAdmin])
    def reject(self, request, pk=None):
        leave_request = self.get_object()
        leave_request.status = LeaveRequest.Status.REJECTED
        leave_request.approver = request.user.person
        leave_request.decided_at = timezone.now()
        leave_request.save(update_fields=["status", "approver", "decided_at"])
        emit("leave.rejected", {"leave_request_id": str(leave_request.id)})
        return Response(LeaveRequestSerializer(leave_request).data)


class MyLeaveBalancesView(generics.ListAPIView):
    serializer_class = LeaveBalanceSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        return LeaveBalance.objects.filter(person=self.request.user.person)
