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
    class Meta:
        model = Announcement
        fields = ["id", "organisation", "title", "body", "created_by", "created_at"]
        read_only_fields = ["organisation", "created_by"]


class PolicyDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = PolicyDocument
        fields = ["id", "organisation", "title", "category", "file", "uploaded_by", "created_at"]
        read_only_fields = ["organisation", "uploaded_by"]
