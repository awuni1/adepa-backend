from rest_framework import serializers

from .models import AttendanceRecord, GeofenceZone, LeaveBalance, LeaveRequest, LeaveType


class AttendanceRecordSerializer(serializers.ModelSerializer):
    person_name = serializers.SerializerMethodField()

    class Meta:
        model = AttendanceRecord
        fields = [
            "id", "person", "person_name", "date", "clock_in", "clock_out", "source", "status",
            "clock_in_lat", "clock_in_lng",
        ]
        read_only_fields = ["person", "date", "clock_in", "clock_out", "status", "clock_in_lat", "clock_in_lng"]

    def get_person_name(self, obj):
        return f"{obj.person.first_name} {obj.person.last_name}"


class GeofenceZoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = GeofenceZone
        fields = ["id", "organisation", "name", "latitude", "longitude", "radius_meters", "is_active"]
        read_only_fields = ["organisation"]


class LeaveTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = ["id", "organisation", "name", "days_per_year", "paid"]


class LeaveRequestSerializer(serializers.ModelSerializer):
    person_name = serializers.SerializerMethodField()
    leave_type_name = serializers.CharField(source="leave_type.name", read_only=True)
    balance_remaining = serializers.SerializerMethodField()

    class Meta:
        model = LeaveRequest
        fields = [
            "id", "person", "person_name", "leave_type", "leave_type_name", "start_date", "end_date", "days",
            "reason", "status", "approver", "decided_at", "created_at", "balance_remaining",
        ]
        read_only_fields = ["person", "status", "approver", "decided_at"]

    def get_person_name(self, obj):
        return f"{obj.person.first_name} {obj.person.last_name}"

    def get_balance_remaining(self, obj):
        balance = LeaveBalance.objects.filter(
            person=obj.person, leave_type=obj.leave_type, year=obj.start_date.year
        ).first()
        if not balance:
            return None
        return str(balance.entitled - balance.taken)

    def validate(self, attrs):
        from django.utils import timezone

        person = self.context["request"].user.person
        year = attrs["start_date"].year
        try:
            balance = LeaveBalance.objects.get(person=person, leave_type=attrs["leave_type"], year=year)
        except LeaveBalance.DoesNotExist as exc:
            raise serializers.ValidationError("No leave balance configured for this type/year.") from exc

        remaining = balance.entitled - balance.taken
        if attrs["days"] > remaining:
            raise serializers.ValidationError(f"Only {remaining} day(s) remaining for {attrs['leave_type'].name}.")
        return attrs


class LeaveBalanceSerializer(serializers.ModelSerializer):
    remaining = serializers.SerializerMethodField()
    leave_type_name = serializers.CharField(source="leave_type.name", read_only=True)

    class Meta:
        model = LeaveBalance
        fields = ["id", "leave_type", "leave_type_name", "year", "entitled", "taken", "remaining"]

    def get_remaining(self, obj):
        return obj.entitled - obj.taken
