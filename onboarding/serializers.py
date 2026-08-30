from rest_framework import serializers

from .models import OnboardingStage, OnboardingTaskTemplate, PersonOnboarding, PersonOnboardingTask


class OnboardingTaskTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = OnboardingTaskTemplate
        fields = ["id", "stage", "title", "description", "is_required"]


class OnboardingStageSerializer(serializers.ModelSerializer):
    task_templates = OnboardingTaskTemplateSerializer(many=True, read_only=True)

    class Meta:
        model = OnboardingStage
        fields = ["id", "organisation", "title", "sequence", "is_final_stage", "task_templates"]
        read_only_fields = ["organisation"]


class PersonOnboardingTaskSerializer(serializers.ModelSerializer):
    title = serializers.CharField(source="task_template.title", read_only=True)
    description = serializers.CharField(source="task_template.description", read_only=True)
    is_required = serializers.BooleanField(source="task_template.is_required", read_only=True)

    class Meta:
        model = PersonOnboardingTask
        fields = ["id", "task_template", "title", "description", "is_required", "status", "completed_at"]
        read_only_fields = ["completed_at"]


class PersonOnboardingSerializer(serializers.ModelSerializer):
    tasks = PersonOnboardingTaskSerializer(many=True, read_only=True)
    person_name = serializers.SerializerMethodField()
    stage_title = serializers.CharField(source="current_stage.title", read_only=True)

    class Meta:
        model = PersonOnboarding
        fields = [
            "id", "person", "person_name", "current_stage", "stage_title",
            "status", "started_at", "completed_at", "tasks",
        ]

    def get_person_name(self, obj):
        return f"{obj.person.first_name} {obj.person.last_name}"
