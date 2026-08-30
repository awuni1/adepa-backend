from rest_framework import serializers

from .models import FeedbackNote, PerformanceReview, ReviewCycle


class ReviewCycleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewCycle
        fields = ["id", "organisation", "name", "starts_on", "ends_on", "is_active"]


class FeedbackNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeedbackNote
        fields = ["id", "person", "author", "cycle", "body", "created_at"]
        read_only_fields = ["author"]


class PerformanceReviewSerializer(serializers.ModelSerializer):
    cycle_name = serializers.CharField(source="cycle.name", read_only=True)
    person_name = serializers.SerializerMethodField()
    reviewer_name = serializers.SerializerMethodField()

    class Meta:
        model = PerformanceReview
        fields = [
            "id", "cycle", "cycle_name", "person", "person_name", "reviewer", "reviewer_name", "ratings", "summary",
            "ai_draft_summary", "status", "created_at",
        ]
        read_only_fields = ["reviewer", "ai_draft_summary", "status"]

    def get_person_name(self, obj):
        return f"{obj.person.first_name} {obj.person.last_name}"

    def get_reviewer_name(self, obj):
        return f"{obj.reviewer.first_name} {obj.reviewer.last_name}" if obj.reviewer else None
