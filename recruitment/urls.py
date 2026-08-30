from django.urls import path
from rest_framework.routers import DefaultRouter

from ai.views import JobDescriptionDraftView

from .views import (
    ApplicationViewSet,
    JobPostingViewSet,
    MyApplicationsView,
    ScorecardViewSet,
    WithdrawApplicationView,
)

router = DefaultRouter()
router.register("jobs", JobPostingViewSet, basename="job")
router.register("applications", ApplicationViewSet, basename="application")
router.register("scorecards", ScorecardViewSet, basename="scorecard")

urlpatterns = [
    path("ai/job-description/", JobDescriptionDraftView.as_view(), name="ai-job-description"),
    path("me/applications/", MyApplicationsView.as_view(), name="my-applications"),
    path("me/applications/<uuid:pk>/withdraw/", WithdrawApplicationView.as_view(), name="withdraw-application"),
    *router.urls,
]
