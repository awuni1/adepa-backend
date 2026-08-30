from rest_framework.routers import DefaultRouter

from .views import AnnouncementViewSet, DepartmentViewSet, OrganisationViewSet, PolicyDocumentViewSet

router = DefaultRouter()
router.register("organisation", OrganisationViewSet, basename="organisation")
router.register("departments", DepartmentViewSet, basename="department")
router.register("announcements", AnnouncementViewSet, basename="announcement")
router.register("compliance/documents", PolicyDocumentViewSet, basename="policy-document")

urlpatterns = router.urls
