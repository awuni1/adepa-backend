from rest_framework import serializers

from people.models import Person
from people.serializers import PersonSerializer

from .models import Application, ApplicationNote, JobPosting, Scorecard


class JobPostingSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source="department.name", read_only=True)

    class Meta:
        model = JobPosting
        fields = [
            "id", "organisation", "department", "department_name", "title", "slug", "description",
            "requirements", "location", "employment_type", "salary_min", "salary_max",
            "status", "closes_at", "created_by", "created_at", "updated_at",
        ]
        read_only_fields = ["created_by"]


class PublicJobPostingListSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobPosting
        fields = ["id", "title", "slug", "location", "employment_type", "department", "closes_at"]


class PublicJobPostingDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobPosting
        fields = [
            "id", "title", "slug", "description", "requirements", "location",
            "employment_type", "salary_min", "salary_max", "closes_at",
        ]


class ApplyForJobSerializer(serializers.Serializer):
    """Multipart apply form (§7.1): finds-or-creates Person by (org, email)."""

    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=32, required=False, allow_blank=True)
    cover_letter = serializers.CharField(required=False, allow_blank=True)
    cv_file = serializers.FileField()
    answers = serializers.JSONField(required=False, default=dict)

    MAX_CV_SIZE = 5 * 1024 * 1024

    def validate_cv_file(self, value):
        if value.size > self.MAX_CV_SIZE:
            raise serializers.ValidationError("CV must be 5 MB or smaller.")
        allowed = {"application/pdf", "application/msword",
                   "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
        if value.content_type not in allowed:
            raise serializers.ValidationError("CV must be a PDF, DOC, or DOCX file.")
        return value

    def create(self, validated_data):
        job = self.context["job"]
        person, _ = Person.objects.get_or_create(
            organisation=job.organisation,
            email__iexact=validated_data["email"],
            defaults={
                "email": validated_data["email"],
                "first_name": validated_data["first_name"],
                "last_name": validated_data["last_name"],
                "phone": validated_data.get("phone", ""),
            },
        )
        application = Application.objects.create(
            job=job,
            person=person,
            cover_letter=validated_data.get("cover_letter", ""),
            cv_file=validated_data["cv_file"],
            answers=validated_data.get("answers", {}),
            stage_history=[{"stage": Application.Stage.RECEIVED, "at": None, "by": None}],
        )
        return application


class ApplicationNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApplicationNote
        fields = ["id", "application", "author", "body", "created_at"]
        read_only_fields = ["author"]


class ScorecardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Scorecard
        fields = [
            "id", "interview", "interviewer", "ratings", "overall",
            "recommendation", "comments", "ai_draft", "created_at",
        ]
        read_only_fields = ["interviewer", "ai_draft"]


class ApplicationListSerializer(serializers.ModelSerializer):
    person = PersonSerializer(read_only=True)
    job_title = serializers.CharField(source="job.title", read_only=True)
    screening_score = serializers.DecimalField(
        source="screening.score", max_digits=5, decimal_places=2, read_only=True, default=None
    )

    class Meta:
        model = Application
        fields = ["id", "job", "job_title", "person", "stage", "source", "screening_score", "created_at"]


class ApplicationDetailSerializer(serializers.ModelSerializer):
    person = PersonSerializer(read_only=True)
    job_title = serializers.CharField(source="job.title", read_only=True)
    notes = ApplicationNoteSerializer(many=True, read_only=True)

    class Meta:
        model = Application
        fields = [
            "id", "job", "job_title", "person", "stage", "cover_letter", "cv_file", "answers",
            "source", "stage_history", "notes", "created_at", "updated_at",
        ]


class StageChangeSerializer(serializers.Serializer):
    stage = serializers.ChoiceField(choices=Application.Stage.choices)
    note = serializers.CharField(required=False, allow_blank=True)


class HireSerializer(serializers.Serializer):
    job_title = serializers.CharField(max_length=200)
    department_id = serializers.UUIDField()
    manager_id = serializers.UUIDField(required=False, allow_null=True)
    start_date = serializers.DateField()
    base_salary = serializers.DecimalField(max_digits=12, decimal_places=2)
    allowances = serializers.JSONField(required=False, default=list)
    deductions = serializers.JSONField(required=False, default=list)
