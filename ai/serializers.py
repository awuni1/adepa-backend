from rest_framework import serializers

from .models import AIScreeningResult, AttritionFlag


class AIScreeningResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIScreeningResult
        fields = [
            "id", "application", "score", "summary", "extracted",
            "requirement_matches", "model_used", "prompt_version", "created_at",
        ]


class AttritionFlagSerializer(serializers.ModelSerializer):
    person_name = serializers.SerializerMethodField()

    class Meta:
        model = AttritionFlag
        fields = [
            "id", "person", "person_name", "risk_level", "signals", "narrative",
            "period_start", "period_end", "acknowledged_by", "created_at",
        ]
        read_only_fields = ["acknowledged_by"]

    def get_person_name(self, obj):
        return f"{obj.person.first_name} {obj.person.last_name}"


class ChatRequestSerializer(serializers.Serializer):
    session_id = serializers.UUIDField(required=False, allow_null=True)
    message = serializers.CharField()


class JobDescriptionDraftSerializer(serializers.Serializer):
    title = serializers.CharField()
    department = serializers.CharField()
    brief = serializers.CharField()


class InterviewSlotSuggestionSerializer(serializers.Serializer):
    participant_person_ids = serializers.ListField(child=serializers.UUIDField())
    duration_minutes = serializers.IntegerField(default=45)
