from django.urls import path

from .views import AttritionFlagListView, ChatView

urlpatterns = [
    path("ai/chat/", ChatView.as_view(), name="ai-chat"),
    path("ai/attrition-flags/", AttritionFlagListView.as_view(), name="ai-attrition-flags"),
]
