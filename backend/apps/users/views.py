from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import CustomTokenObtainPairSerializer, RegisterSerializer

User = get_user_model()


def _sso_disabled_response():
    return Response(
        {"detail": "Use the portfolio single sign-on service."},
        status=status.HTTP_403_FORBIDDEN,
    )


def _trusted_identity(request):
    username = request.META.get("HTTP_REMOTE_USER", "").strip()
    email = request.META.get("HTTP_REMOTE_EMAIL", "").strip().lower()
    display_name = request.META.get("HTTP_REMOTE_NAME", "").strip()
    values = (username, email, display_name)
    if (
        not username
        or not email
        or any(
            len(value) > 254 or any(ord(character) < 32 or ord(character) == 127 for character in value)
            for value in values
        )
    ):
        return None
    try:
        validate_email(email)
    except ValidationError:
        return None
    return username, email, display_name


def _get_or_create_sso_user(email, display_name):
    existing = User.objects.filter(email__iexact=email).first()
    if existing:
        return existing
    nickname = (display_name or email.split("@", 1)[0])[:50]
    try:
        with transaction.atomic():
            user = User(email=email, username=email, nickname=nickname)
            user.set_unusable_password()
            user.save()
            return user
    except IntegrityError:
        return User.objects.get(email__iexact=email)


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        if settings.PILGRIMAGE_SSO_ENABLED:
            return _sso_disabled_response()
        return super().post(request, *args, **kwargs)


class LoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        if settings.PILGRIMAGE_SSO_ENABLED:
            return _sso_disabled_response()
        return super().post(request, *args, **kwargs)


class SsoExchangeView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        if not settings.PILGRIMAGE_SSO_ENABLED:
            return Response({"detail": "SSO is not enabled."}, status=status.HTTP_404_NOT_FOUND)
        identity = _trusted_identity(request)
        if identity is None:
            return Response(
                {"detail": "A validated proxy identity is required."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        _, email, display_name = identity
        user = _get_or_create_sso_user(email, display_name)
        if not user.is_active:
            return Response({"detail": "This account is disabled."}, status=status.HTTP_403_FORBIDDEN)
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "email": user.email,
                "nickname": user.nickname,
            }
        )
