from rest_framework import serializers

from .models import OffboardingStage, OffboardingTaskTemplate, PersonOffboarding, PersonOffboardingTask


class OffboardingTaskTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = OffboardingTaskTemplate
        fields = ["id", "stage", "title", "is_required"]


class OffboardingStageSerializer(serializers.ModelSerializer):
    task_templates = OffboardingTaskTemplateSerializer(many=True, read_only=True)

    class Meta:
        model = OffboardingStage
        fields = ["id", "organisation", "title", "sequence", "is_final_stage", "task_templates"]
        read_only_fields = ["organisation"]


class PersonOffboardingTaskSerializer(serializers.ModelSerializer):
    title = serializers.CharField(source="task_template.title", read_only=True)
    is_required = serializers.BooleanField(source="task_template.is_required", read_only=True)

    class Meta:
        model = PersonOffboardingTask
        fields = ["id", "task_template", "title", "is_required", "status", "completed_at"]
        read_only_fields = ["completed_at"]


class PersonOffboardingSerializer(serializers.ModelSerializer):
    tasks = PersonOffboardingTaskSerializer(many=True, read_only=True)
    person_name = serializers.SerializerMethodField()
    stage_title = serializers.CharField(source="current_stage.title", read_only=True)

    class Meta:
        model = PersonOffboarding
        fields = [
            "id", "person", "person_name", "current_stage", "stage_title", "status",
            "exit_reason", "notice_starts", "notice_ends", "started_at", "completed_at", "tasks",
        ]
        read_only_fields = ["started_at", "completed_at"]

    def get_person_name(self, obj):
        return f"{obj.person.first_name} {obj.person.last_name}"
