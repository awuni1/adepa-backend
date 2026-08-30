from django.urls import path

from .views import ApplyForJobView, PublicJobPostingDetailView, PublicJobPostingListView

urlpatterns = [
    path("jobs/", PublicJobPostingListView.as_view(), name="public-jobs"),
    path("jobs/<slug:slug>/", PublicJobPostingDetailView.as_view(), name="public-job-detail"),
    path("jobs/<slug:slug>/apply/", ApplyForJobView.as_view(), name="public-job-apply"),
]
