from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import DocumentRequestViewSet, MyDocumentRequestsView

router = DefaultRouter()
router.register("documents/requests", DocumentRequestViewSet, basename="document-request")

urlpatterns = [
    path("me/documents/", MyDocumentRequestsView.as_view(), name="my-documents"),
    *router.urls,
]
