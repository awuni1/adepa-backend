from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import AssetAssignmentViewSet, AssetCategoryViewSet, AssetViewSet, MyAssetsView

router = DefaultRouter()
router.register("assets/categories", AssetCategoryViewSet, basename="asset-category")
router.register("assets/assignments", AssetAssignmentViewSet, basename="asset-assignment")
router.register("assets", AssetViewSet, basename="asset")

urlpatterns = [
    path("me/assets/", MyAssetsView.as_view(), name="my-assets"),
    *router.urls,
]
