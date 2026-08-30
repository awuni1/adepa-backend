from django.urls import path
from rest_framework.routers import DefaultRouter

from ai.views import InterviewSlotSuggestionView

from .views import AgoraWebhookView, InterviewSessionViewSet, MyUpcomingInterviewsView

router = DefaultRouter()
router.register("interviews", InterviewSessionViewSet, basename="interview")

urlpatterns = [
    path("me/interviews/", MyUpcomingInterviewsView.as_view({"get": "list"}), name="my-interviews"),
    path("ai/interview-slots/", InterviewSlotSuggestionView.as_view(), name="ai-interview-slots"),
    path("webhooks/agora-recording/", AgoraWebhookView.as_view(), name="agora-webhook"),
    *router.urls,
]
