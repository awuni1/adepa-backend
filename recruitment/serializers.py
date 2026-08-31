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
        # organisation and slug are set server-side (JobPostingViewSet.perform_create):
        # the frontend's "New posting" form never collects either, and slug is
        # derived from the title so it can't just be a plain required input.
        read_only_fields = ["created_by", "organisation", "slug"]


class PublicJobPostingListSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source="department.name", read_only=True)

    class Meta:
        model = JobPosting
        fields = [
            "id", "title", "slug", "location", "employment_type", "department", "department_name",
            "salary_min", "salary_max", "closes_at", "created_at",
        ]


class PublicJobPostingDetailSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source="department.name", read_only=True)

    class Meta:
        model = JobPosting
        fields = [
            "id", "title", "slug", "description", "requirements", "location", "department_name",
            "employment_type", "salary_min", "salary_max", "closes_at", "created_at",
        ]


class ApplyForJobSerializer(serializers.Serializer):
    """Multipart apply form (§7.1): finds-or-creates Person by (org, email)."""

    SOURCE_CHOICES = [
        ("careers_portal", "Company careers page"),
        ("job_board", "Job board"),
        ("linkedin", "LinkedIn"),
        ("referral", "Referral"),
        ("social", "Social media"),
        ("other", "Other"),
    ]

    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=32, required=False, allow_blank=True)
    location = serializers.CharField(max_length=120, required=False, allow_blank=True)
    earliest_start = serializers.CharField(max_length=120, required=False, allow_blank=True)
    source = serializers.ChoiceField(choices=SOURCE_CHOICES, required=False, default="careers_portal")
    open_to_other_roles = serializers.BooleanField(required=False, default=False)
    cover_letter = serializers.CharField(required=False, allow_blank=True)
    cv_file = serializers.FileField()
    # Free-form per-job screening questions aren't modeled yet (no per-posting
    # question config exists) — this stays for when that's built; today only
    # the flat fields above (location/earliest_start/open_to_other_roles) get
    # folded into it below.
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
        answers = validated_data.get("answers", {})
        if validated_data.get("location"):
            answers["location"] = validated_data["location"]
        if validated_data.get("earliest_start"):
            answers["earliest_start"] = validated_data["earliest_start"]
        answers["open_to_other_roles"] = validated_data.get("open_to_other_roles", False)

        application = Application.objects.create(
            job=job,
            person=person,
            cover_letter=validated_data.get("cover_letter", ""),
            cv_file=validated_data["cv_file"],
            answers=answers,
            source=validated_data.get("source", "careers_portal"),
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
