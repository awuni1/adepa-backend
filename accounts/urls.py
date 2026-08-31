from django.urls import path

from .views import (
    AdepaTokenObtainPairView,
    CandidateRegisterView,
    ChangePasswordView,
    LogoutView,
    MeView,
    TokenRefreshCookieView,
)

urlpatterns = [
    path("register/candidate/", CandidateRegisterView.as_view(), name="register-candidate"),
    path("token/", AdepaTokenObtainPairView.as_view(), name="token-obtain"),
    path("token/refresh/", TokenRefreshCookieView.as_view(), name="token-refresh"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("me/", MeView.as_view(), name="me"),
    path("change-password/", ChangePasswordView.as_view(), name="change-password"),
]
