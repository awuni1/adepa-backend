from rest_framework import serializers

from people.serializers import PersonSerializer

from .models import InterviewParticipant, InterviewSession


class InterviewParticipantSerializer(serializers.ModelSerializer):
    # Nested, not just the FK id — every consumer (participant lists, video
    # tile labels, "with X" summaries) needs the name/avatar, and this is
    # read-only everywhere it's used (participants are set via
    # ScheduleInterviewSerializer.participant_person_ids, never through this
    # serializer), so nesting here doesn't affect writes.
    person = PersonSerializer(read_only=True)

    class Meta:
        model = InterviewParticipant
        fields = ["id", "session", "person", "role", "agora_uid", "joined_at", "left_at"]


class InterviewSessionSerializer(serializers.ModelSerializer):
    participants = InterviewParticipantSerializer(many=True, read_only=True)

    class Meta:
        model = InterviewSession
        fields = [
            "id", "organisation", "kind", "application", "title", "scheduled_at",
            "duration_minutes", "channel_name", "status", "recording_enabled",
            "recording_consent_ack", "started_at", "ended_at", "participants",
            "created_at", "updated_at",
        ]
        read_only_fields = ["channel_name", "status", "started_at", "ended_at"]


class ScheduleInterviewSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=InterviewSession.Kind.choices)
    application_id = serializers.UUIDField(required=False, allow_null=True)
    title = serializers.CharField(max_length=200)
    scheduled_at = serializers.DateTimeField()
    duration_minutes = serializers.IntegerField(default=45)
    participant_person_ids = serializers.ListField(child=serializers.UUIDField())
    recording_enabled = serializers.BooleanField(default=True)


class InterviewArtifactSerializer(serializers.ModelSerializer):
    class Meta:
        from ai.models import InterviewArtifact

        model = InterviewArtifact
        fields = ["id", "session", "transcript", "summary", "scorecard_draft", "model_used", "created_at"]
