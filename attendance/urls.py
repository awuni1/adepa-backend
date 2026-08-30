from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    AttendanceViewSet,
    ClockInView,
    ClockOutView,
    GeofenceZoneViewSet,
    LeaveRequestViewSet,
    LeaveTypeViewSet,
    MyAttendanceView,
    MyLeaveBalancesView,
)

router = DefaultRouter()
router.register("attendance/geofence-zones", GeofenceZoneViewSet, basename="geofence-zone")
router.register("attendance", AttendanceViewSet, basename="attendance")
router.register("leave/types", LeaveTypeViewSet, basename="leave-type")
router.register("leave/requests", LeaveRequestViewSet, basename="leave-request")

urlpatterns = [
    path("attendance/clock-in/", ClockInView.as_view(), name="clock-in"),
    path("attendance/clock-out/", ClockOutView.as_view(), name="clock-out"),
    path("attendance/me/", MyAttendanceView.as_view(), name="my-attendance"),
    path("leave/balances/me/", MyLeaveBalancesView.as_view(), name="my-leave-balances"),
    *router.urls,
]
