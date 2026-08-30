from rest_framework import serializers

from .models import DocumentRequest


class DocumentRequestSerializer(serializers.ModelSerializer):
    person_name = serializers.SerializerMethodField()

    class Meta:
        model = DocumentRequest
        fields = [
            "id", "organisation", "person", "person_name", "title", "file", "requested_by",
            "status", "signature_name", "signed_at", "declined_reason", "created_at",
        ]
        read_only_fields = ["organisation", "requested_by", "status", "signature_name", "signed_at"]

    def get_person_name(self, obj):
        return f"{obj.person.first_name} {obj.person.last_name}"


class SignDocumentSerializer(serializers.Serializer):
    signature_name = serializers.CharField(max_length=200)


class DeclineDocumentSerializer(serializers.Serializer):
    reason = serializers.CharField(allow_blank=True, required=False)
