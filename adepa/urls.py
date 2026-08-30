from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from interviews.views import AgoraWebhookView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/auth/", include("accounts.urls")),
    path("api/v1/careers/", include("recruitment.public_urls")),  # UNAUTHENTICATED
    path("api/v1/", include("orgs.urls")),
    path("api/v1/", include("people.urls")),
    path("api/v1/", include("recruitment.urls")),
    path("api/v1/", include("interviews.urls")),
    path("api/v1/", include("employees.urls")),
    path("api/v1/", include("attendance.urls")),
    path("api/v1/", include("payroll.urls")),
    path("api/v1/", include("performance.urls")),
    path("api/v1/", include("ai.urls")),
    path("api/v1/", include("onboarding.urls")),
    path("api/v1/", include("offboarding.urls")),
    path("api/v1/", include("assets.urls")),
    path("api/v1/", include("helpdesk.urls")),
    path("api/v1/", include("audit.urls")),
    path("api/v1/", include("documents.urls")),
    path("api/v1/webhooks/agora/", AgoraWebhookView.as_view(), name="agora-webhook"),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]
