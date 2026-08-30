from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsHRorAdmin

from .models import AttritionFlag, ChatSession
from .serializers import (
    AttritionFlagSerializer,
    ChatRequestSerializer,
    InterviewSlotSuggestionSerializer,
    JobDescriptionDraftSerializer,
)
from .services import draft_job_description


class ChatView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_scope = "chatbot"

    def post(self, request):
        from .services import chat_reply

        serializer = ChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        person = request.user.person

        session_id = serializer.validated_data.get("session_id")
        if session_id:
            session = ChatSession.objects.get(id=session_id, person=person)
        else:
            session = ChatSession.objects.create(person=person)

        reply = chat_reply(person, serializer.validated_data["message"], session)
        return Response({"reply": reply, "session_id": session.id})


class JobDescriptionDraftView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = JobDescriptionDraftSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        draft = draft_job_description(**serializer.validated_data)
        return Response({"description": draft})


class InterviewSlotSuggestionView(APIView):
    """Smart scheduling suggestions (§7.2, §9.8). Kept as a simple
    availability-overlap heuristic — swap in a Gemini call once real
    calendars/availability data exists to reason over."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = InterviewSlotSuggestionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response({"suggestions": [], "note": "No calendar data source configured yet."})


class AttritionFlagListView(generics.ListAPIView):
    serializer_class = AttritionFlagSerializer
    permission_classes = [IsHRorAdmin]
    filterset_fields = ["risk_level"]

    def get_queryset(self):
        qs = AttritionFlag.objects.filter(person__organisation=self.request.user.organisation)
        if self.request.query_params.get("unacknowledged") == "true":
            qs = qs.filter(acknowledged_by__isnull=True)
        return qs
