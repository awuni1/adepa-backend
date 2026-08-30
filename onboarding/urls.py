from rest_framework.routers import DefaultRouter

from .views import (
    OnboardingStageViewSet,
    OnboardingTaskTemplateViewSet,
    PersonOnboardingTaskViewSet,
    PersonOnboardingViewSet,
)

router = DefaultRouter()
router.register("onboarding/stages", OnboardingStageViewSet, basename="onboarding-stage")
router.register("onboarding/task-templates", OnboardingTaskTemplateViewSet, basename="onboarding-task-template")
router.register("onboarding/tasks", PersonOnboardingTaskViewSet, basename="onboarding-task")
router.register("onboarding", PersonOnboardingViewSet, basename="onboarding")

urlpatterns = router.urls
