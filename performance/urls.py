from rest_framework.routers import DefaultRouter

from .views import FeedbackNoteViewSet, PerformanceReviewViewSet, ReviewCycleViewSet

router = DefaultRouter()
router.register("performance/cycles", ReviewCycleViewSet, basename="review-cycle")
router.register("performance/feedback-notes", FeedbackNoteViewSet, basename="feedback-note")
router.register("performance/reviews", PerformanceReviewViewSet, basename="performance-review")

urlpatterns = router.urls
