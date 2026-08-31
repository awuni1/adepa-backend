from django.db.models import Max
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.views import OrgScopedViewSet
from notifications.events import emit
from people.models import Person

from .agora import AgoraCloudRecording, build_rtc_token, verify_webhook_signature
from .models import InterviewParticipant, InterviewSession
from .serializers import (
    InterviewArtifactSerializer,
    InterviewSessionSerializer,
    ScheduleInterviewSerializer,
)


class IsSessionParticipant(permissions.BasePermission):
    """Declared participants can always join. HR/admin can also join any
    interview in their own org for oversight, even if not explicitly added
    as a participant — the token view adds them as an attendee on the fly."""

    def has_object_permission(self, request, view, obj):
        if obj.participants.filter(person__user=request.user).exists():
            return True
        return request.user.role in ("hr", "admin") and obj.organisation_id == request.user.organisation_id


class InterviewSessionViewSet(OrgScopedViewSet):
    serializer_class = InterviewSessionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["kind", "status"]

    def get_queryset(self):
        qs = InterviewSession.objects.filter(organisation=self.request.user.organisation).prefetch_related(
            "participants__person"
        )
        if self.request.query_params.get("mine") == "true":
            qs = qs.filter(participants__person__user=self.request.user)
        return qs.distinct()

    def create(self, request, *args, **kwargs):
        serializer = ScheduleInterviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        session = InterviewSession.objects.create(
            organisation=request.user.organisation,
            kind=data["kind"],
            application_id=data.get("application_id"),
            title=data["title"],
            scheduled_at=data["scheduled_at"],
            duration_minutes=data["duration_minutes"],
            recording_enabled=data["recording_enabled"],
        )

        # The candidate's person id is always first in participant_person_ids
        # for an interview (see ScheduleForm on the frontend), but nothing
        # previously tagged them as Role.CANDIDATE — they just got lumped in
        # as HOST, which meant nothing downstream (e.g. "who do we email the
        # invite to?") could actually identify the candidate.
        candidate_person_id = None
        if data["kind"] == InterviewSession.Kind.INTERVIEW and data.get("application_id"):
            from recruitment.models import Application

            candidate_person_id = str(
                Application.objects.values_list("person_id", flat=True).get(id=data["application_id"])
            )

        host_assigned = False
        for i, person_id in enumerate(data["participant_person_ids"], start=1):
            if candidate_person_id and str(person_id) == candidate_person_id:
                role = InterviewParticipant.Role.CANDIDATE
            elif not host_assigned:
                role = InterviewParticipant.Role.HOST
                host_assigned = True
            else:
                role = InterviewParticipant.Role.ATTENDEE
            InterviewParticipant.objects.create(session=session, person_id=person_id, role=role, agora_uid=i)
        emit("interview.scheduled", {"session_id": str(session.id)})
        return Response(InterviewSessionSerializer(session).data, status=status.HTTP_201_CREATED)

    def perform_update(self, serializer):
        emit("interview.rescheduled", {"session_id": str(serializer.instance.id)})
        serializer.save()

    @action(detail=True, methods=["get"], permission_classes=[permissions.IsAuthenticated, IsSessionParticipant],
            throttle_classes=[], url_path="token")
    def token(self, request, pk=None):
        session = self.get_object()
        participant = session.participants.filter(person__user=request.user).first()
        if not participant:
            # HR/admin joining for oversight without being a declared participant.
            next_uid = (session.participants.aggregate(m=Max("agora_uid"))["m"] or 0) + 1
            participant = InterviewParticipant.objects.create(
                session=session, person=request.user.person,
                role=InterviewParticipant.Role.ATTENDEE, agora_uid=next_uid,
            )
        rtc_token = build_rtc_token(session.channel_name, participant.agora_uid)
        return Response({"token": rtc_token, "uid": participant.agora_uid, "channel": session.channel_name})

    @action(detail=True, methods=["post"], url_path="start-recording")
    def start_recording(self, request, pk=None):
        session = self.get_object()
        recorder = AgoraCloudRecording()
        resource_id = recorder.acquire(session.channel_name, "0")
        storage_config = {"vendor": 1, "region": 0, "bucket": "", "accessKey": "", "secretKey": ""}
        sid = recorder.start(session.channel_name, "0", resource_id, storage_config)
        session.recording_resource_id = resource_id
        session.recording_sid = sid
        session.status = InterviewSession.Status.LIVE
        session.started_at = timezone.now()
        session.save(update_fields=["recording_resource_id", "recording_sid", "status", "started_at"])
        return Response(InterviewSessionSerializer(session).data)

    @action(detail=True, methods=["post"], url_path="stop-recording")
    def stop_recording(self, request, pk=None):
        session = self.get_object()
        recorder = AgoraCloudRecording()
        recorder.stop(session.channel_name, "0", session.recording_resource_id, session.recording_sid)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"])
    def end(self, request, pk=None):
        from ai.tasks import summarise_interview

        session = self.get_object()
        session.status = InterviewSession.Status.COMPLETED
        session.ended_at = timezone.now()
        session.save(update_fields=["status", "ended_at"])
        summarise_interview.delay(str(session.id))
        return Response(InterviewSessionSerializer(session).data)

    @action(detail=True, methods=["get"])
    def artifact(self, request, pk=None):
        session = self.get_object()
        artifact = getattr(session, "artifact", None)
        if not artifact:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(InterviewArtifactSerializer(artifact).data)


class MyUpcomingInterviewsView(viewsets.ReadOnlyModelViewSet):
    serializer_class = InterviewSessionSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        # "Upcoming" means still joinable — not started, or in progress — rather
        # than a hard cutoff on scheduled_at, so a session doesn't vanish from
        # the list just because someone's a few minutes late.
        return (
            InterviewSession.objects.filter(
                participants__person__user=self.request.user,
                status__in=[InterviewSession.Status.SCHEDULED, InterviewSession.Status.LIVE],
            )
            .prefetch_related("participants__person")
            .order_by("scheduled_at")
            .distinct()
        )


class AgoraWebhookView(APIView):
    """Receives Agora's cloud-recording-complete webhook; downstream Celery task
    pulls the file and sends it to Gemini for transcription (§8.6)."""

    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        import json

        from ai.tasks import summarise_interview

        signature = request.headers.get("Agora-Signature-V2")
        if not verify_webhook_signature(request.body, signature):
            return Response(status=status.HTTP_403_FORBIDDEN)

        payload = json.loads(request.body)
        sid = payload.get("payload", {}).get("sid") or payload.get("sid")
        session = InterviewSession.objects.filter(recording_sid=sid).first()
        if session:
            summarise_interview.delay(str(session.id))
        return Response(status=status.HTTP_200_OK)
