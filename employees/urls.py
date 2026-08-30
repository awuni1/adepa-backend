from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import EmployeeViewSet, MyProfileView

router = DefaultRouter()
router.register("employees", EmployeeViewSet, basename="employee")

urlpatterns = [
    path("me/profile/", MyProfileView.as_view(), name="my-profile"),
    *router.urls,
]
