from rest_framework import generics, permissions, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .serializers import CandidateRegisterSerializer, ChangePasswordSerializer, MeSerializer
from .tokens import AdepaTokenObtainPairSerializer


class OrgScopedViewSet(viewsets.ModelViewSet):
    """Base viewset — every queryset is scoped to the caller's organisation (§6.2)."""

    def get_queryset(self):
        return super().get_queryset().filter(organisation=self.request.user.organisation)

    def perform_create(self, serializer):
        serializer.save(organisation=self.request.user.organisation)


class AdepaTokenObtainPairView(TokenObtainPairView):
    serializer_class = AdepaTokenObtainPairSerializer


class TokenRefreshCookieView(TokenRefreshView):
    """Alias kept for symmetry with §6.4's endpoint list; behaviour is stock simplejwt."""


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        refresh = request.data.get("refresh")
        if refresh:
            RefreshToken(refresh).blacklist()
        return Response(status=204)


class CandidateRegisterView(generics.CreateAPIView):
    serializer_class = CandidateRegisterSerializer
    permission_classes = [permissions.AllowAny]


class MeView(generics.RetrieveAPIView):
    serializer_class = MeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class ChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=204)
