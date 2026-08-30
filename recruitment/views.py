from django.utils import timezone
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.permissions import IsHRorAdmin, IsManagerOrHRorAdmin
from accounts.views import OrgScopedViewSet
from notifications.events import emit

from .models import Application, ApplicationNote, JobPosting, Scorecard
from .permissions import CanManageJobPosting
from .serializers import (
    ApplicationDetailSerializer,
    ApplicationListSerializer,
    ApplicationNoteSerializer,
    ApplyForJobSerializer,
    HireSerializer,
    JobPostingSerializer,
    PublicJobPostingDetailSerializer,
    PublicJobPostingListSerializer,
    ScorecardSerializer,
    StageChangeSerializer,
)


# ---- Public careers portal (no auth, throttled) ----------------------------

class PublicJobPostingListView(generics.ListAPIView):
    serializer_class = PublicJobPostingListSerializer
    permission_classes = [permissions.AllowAny]
    filterset_fields = ["department", "location", "employment_type"]
    search_fields = ["title", "description"]

    def get_queryset(self):
        return JobPosting.objects.filter(status=JobPosting.Status.OPEN)


class PublicJobPostingDetailView(generics.RetrieveAPIView):
    serializer_class = PublicJobPostingDetailSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = "slug"

    def get_queryset(self):
        return JobPosting.objects.filter(status=JobPosting.Status.OPEN)


class ApplyForJobView(generics.CreateAPIView):
    serializer_class = ApplyForJobSerializer
    permission_classes = [permissions.AllowAny]
    throttle_scope = "public_apply"

    def get_job(self):
        return JobPosting.objects.get(slug=self.kwargs["slug"], status=JobPosting.Status.OPEN)

    def create(self, request, *args, **kwargs):
        job = self.get_job()
        if Application.objects.filter(job=job, person__email__iexact=request.data.get("email")).exists():
            return Response({"code": "already_applied"}, status=status.HTTP_409_CONFLICT)
        serializer = self.get_serializer(data=request.data, context={"job": job})
        serializer.is_valid(raise_exception=True)
        application = serializer.save()
        return Response({"id": application.id}, status=status.HTTP_201_CREATED)


# ---- Internal ATS -----------------------------------------------------------

class JobPostingViewSet(OrgScopedViewSet):
    serializer_class = JobPostingSerializer
    permission_classes = [CanManageJobPosting]
    queryset = JobPosting.objects.all()
    filterset_fields = ["status", "department"]
    search_fields = ["title"]

    def perform_create(self, serializer):
        serializer.save(organisation=self.request.user.organisation, created_by=self.request.user)

    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        job = self.get_object()
        job.status = JobPosting.Status.OPEN
        job.save(update_fields=["status"])
        return Response(self.get_serializer(job).data)

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        job = self.get_object()
        job.status = JobPosting.Status.CLOSED
        job.save(update_fields=["status"])
        return Response(self.get_serializer(job).data)


class ApplicationViewSet(viewsets.ModelViewSet):
    permission_classes = [IsManagerOrHRorAdmin]
    filterset_fields = ["job", "stage"]
    ordering_fields = ["created_at", "screening__score"]

    def get_queryset(self):
        qs = Application.objects.filter(job__organisation=self.request.user.organisation).select_related(
            "job", "person", "screening"
        )
        if self.action == "retrieve":
            qs = qs.prefetch_related("notes__author")
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return ApplicationListSerializer
        return ApplicationDetailSerializer

    @action(detail=True, methods=["patch"], url_path="stage")
    def change_stage(self, request, pk=None):
        application = self.get_object()
        serializer = StageChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_stage = serializer.validated_data["stage"]

        if not application.can_transition_to(new_stage):
            return Response(
                {"code": "invalid_transition", "message": f"Cannot move from {application.stage} to {new_stage}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        application.stage = new_stage
        application.stage_history.append({
            "stage": new_stage,
            "at": timezone.now().isoformat(),
            "by": request.user.id,
            "note": serializer.validated_data.get("note", ""),
        })
        application.save(update_fields=["stage", "stage_history"])
        emit("application.stage_changed", {"application_id": str(application.id), "stage": new_stage})
        return Response(ApplicationDetailSerializer(application).data)

    @action(detail=True, methods=["post"], url_path="notes")
    def add_note(self, request, pk=None):
        application = self.get_object()
        serializer = ApplicationNoteSerializer(data={**request.data, "application": application.id})
        serializer.is_valid(raise_exception=True)
        serializer.save(author=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], permission_classes=[IsHRorAdmin])
    def hire(self, request, pk=None):
        from employees.services import hire_from_application

        application = self.get_object()
        serializer = HireSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        employment = hire_from_application(application, **serializer.validated_data)
        return Response({"employment_id": employment.id}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"], url_path="screening")
    def screening(self, request, pk=None):
        application = self.get_object()
        result = getattr(application, "screening", None)
        if not result:
            return Response(status=status.HTTP_404_NOT_FOUND)
        from ai.serializers import AIScreeningResultSerializer

        return Response(AIScreeningResultSerializer(result).data)

    @action(detail=True, methods=["post"], url_path="screening/rerun", permission_classes=[IsHRorAdmin])
    def rerun_screening(self, request, pk=None):
        from ai.tasks import screen_resume

        application = self.get_object()
        screen_resume.delay(str(application.id))
        return Response(status=status.HTTP_202_ACCEPTED)


class ScorecardViewSet(viewsets.ModelViewSet):
    serializer_class = ScorecardSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Scorecard.objects.all()

    def perform_create(self, serializer):
        serializer.save(interviewer=self.request.user)


# ---- Candidate portal --------------------------------------------------------

class MyApplicationsView(generics.ListAPIView):
    serializer_class = ApplicationDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        return Application.objects.filter(person__user=self.request.user)


class WithdrawApplicationView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Application.objects.filter(person__user=self.request.user)

    def post(self, request, pk=None):
        application = self.get_queryset().get(pk=pk)
        if not application.can_transition_to(Application.Stage.WITHDRAWN):
            return Response(status=status.HTTP_400_BAD_REQUEST)
        application.stage = Application.Stage.WITHDRAWN
        application.save(update_fields=["stage"])
        return Response(status=status.HTTP_204_NO_CONTENT)
