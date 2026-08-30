from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from accounts.permissions import IsHRorAdmin, IsManagerOrHRorAdmin
from notifications.events import emit

from .models import FeedbackNote, PerformanceReview, ReviewCycle
from .serializers import FeedbackNoteSerializer, PerformanceReviewSerializer, ReviewCycleSerializer


class ReviewCycleViewSet(ModelViewSet):
    serializer_class = ReviewCycleSerializer
    permission_classes = [IsHRorAdmin]

    def get_queryset(self):
        return ReviewCycle.objects.filter(organisation=self.request.user.organisation)

    def perform_create(self, serializer):
        serializer.save(organisation=self.request.user.organisation)


class FeedbackNoteViewSet(ModelViewSet):
    serializer_class = FeedbackNoteSerializer
    permission_classes = [IsManagerOrHRorAdmin]

    def get_queryset(self):
        return FeedbackNote.objects.filter(person__organisation=self.request.user.organisation)

    def perform_create(self, serializer):
        serializer.save(author=self.request.user.person)


class PerformanceReviewViewSet(ModelViewSet):
    serializer_class = PerformanceReviewSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["person", "cycle", "status"]

    def get_queryset(self):
        user = self.request.user
        qs = PerformanceReview.objects.filter(person__organisation=user.organisation).select_related(
            "cycle", "person", "reviewer"
        )
        if user.role == "manager":
            return qs.filter(reviewer__user=user)
        if user.role in ("hr", "admin"):
            return qs
        return qs.filter(person__user=user)

    def perform_create(self, serializer):
        serializer.save(reviewer=self.request.user.person)

    @action(detail=True, methods=["post"], url_path="ai-draft", permission_classes=[IsManagerOrHRorAdmin])
    def ai_draft(self, request, pk=None):
        from ai.services import draft_performance_review

        review = self.get_object()
        review.ai_draft_summary = draft_performance_review(review)
        review.save(update_fields=["ai_draft_summary"])
        return Response(PerformanceReviewSerializer(review).data)

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        review = self.get_object()
        review.status = PerformanceReview.Status.SUBMITTED
        review.save(update_fields=["status"])
        emit("review.submitted", {"review_id": str(review.id)})
        return Response(PerformanceReviewSerializer(review).data)

    @action(detail=True, methods=["post"])
    def acknowledge(self, request, pk=None):
        review = self.get_object()
        review.status = PerformanceReview.Status.ACKNOWLEDGED
        review.save(update_fields=["status"])
        return Response(PerformanceReviewSerializer(review).data)
