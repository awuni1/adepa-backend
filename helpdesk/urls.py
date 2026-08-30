from rest_framework.routers import DefaultRouter

from .views import TicketCommentViewSet, TicketTypeViewSet, TicketViewSet

router = DefaultRouter()
router.register("helpdesk/ticket-types", TicketTypeViewSet, basename="ticket-type")
router.register("helpdesk/comments", TicketCommentViewSet, basename="ticket-comment")
router.register("helpdesk/tickets", TicketViewSet, basename="ticket")

urlpatterns = router.urls
