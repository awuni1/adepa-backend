from rest_framework import serializers

from people.serializers import AvatarURLMixin, PersonSerializer

from .models import EmployeeDocument, Employment, RoleHistory


class RoleHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = RoleHistory
        fields = ["id", "job_title", "department", "effective_from", "effective_to", "change_reason"]


class EmployeeDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeDocument
        fields = ["id", "person", "kind", "file", "uploaded_by", "created_at"]
        read_only_fields = ["uploaded_by"]


class EmploymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employment
        fields = [
            "id", "person", "organisation", "department", "job_title", "manager",
            "employee_no", "start_date", "end_date", "status", "hired_from_application",
        ]
        read_only_fields = ["employee_no", "hired_from_application"]


class EmployeeProfileSerializer(AvatarURLMixin, serializers.ModelSerializer):
    """Directory/profile view: Person + Employment + documents + role history,
    with provenance back to the hiring application (§7.3)."""

    employment = EmploymentSerializer(read_only=True)
    documents = EmployeeDocumentSerializer(many=True, read_only=True)
    role_history = RoleHistorySerializer(many=True, read_only=True)

    class Meta:
        model = PersonSerializer.Meta.model
        fields = PersonSerializer.Meta.fields + ["employment", "documents", "role_history"]


class ExitEmployeeSerializer(serializers.Serializer):
    end_date = serializers.DateField()
    reason = serializers.CharField()


class SelfProfileUpdateSerializer(AvatarURLMixin, serializers.ModelSerializer):
    """What an employee may edit on their own record — contact details and
    avatar only. Employment, documents, and lifecycle stage stay HR-only."""

    class Meta:
        model = PersonSerializer.Meta.model
        fields = ["phone", "avatar"]
