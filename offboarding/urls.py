from rest_framework.routers import DefaultRouter

from .views import (
    OffboardingStageViewSet,
    OffboardingTaskTemplateViewSet,
    PersonOffboardingTaskViewSet,
    PersonOffboardingViewSet,
)

router = DefaultRouter()
router.register("offboarding/stages", OffboardingStageViewSet, basename="offboarding-stage")
router.register("offboarding/task-templates", OffboardingTaskTemplateViewSet, basename="offboarding-task-template")
router.register("offboarding/tasks", PersonOffboardingTaskViewSet, basename="offboarding-task")
router.register("offboarding", PersonOffboardingViewSet, basename="offboarding")

urlpatterns = router.urls
