from rest_framework import serializers

from .models import Announcement, Department, Organisation, PolicyDocument


class OrganisationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organisation
        fields = ["id", "name", "slug", "created_at", "updated_at"]


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ["id", "organisation", "name", "created_at", "updated_at"]


class AnnouncementSerializer(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField()
    department_name = serializers.CharField(source="department.name", read_only=True, default=None)

    class Meta:
        model = Announcement
        fields = [
            "id", "organisation", "title", "body", "created_by", "created_by_name",
            "is_pinned", "department", "department_name", "created_at",
        ]
        read_only_fields = ["organisation", "created_by"]

    def get_created_by_name(self, obj):
        if not obj.created_by:
            return None
        return obj.created_by.get_full_name() or obj.created_by.username


class PolicyDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = PolicyDocument
        fields = ["id", "organisation", "title", "category", "file", "uploaded_by", "created_at"]
        read_only_fields = ["organisation", "uploaded_by"]
