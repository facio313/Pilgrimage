import hashlib
import uuid

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from rest_framework import generics, status
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .authentication import TrustedSsoIdentity, trusted_sso_identity, validate_refresh_binding
from .serializers import (
    CustomTokenObtainPairSerializer,
    RegisterSerializer,
    SsoBoundTokenRefreshSerializer,
)

User = get_user_model()


class SsoAccountConflictError(Exception):
    pass


def _sso_disabled_response():
    return Response(
        {"detail": "Use the portfolio single sign-on service."},
        status=status.HTTP_403_FORBIDDEN,
    )


def _internal_sso_username(subject: str) -> str:
    deterministic = f"sso_{hashlib.sha256(subject.encode('utf-8')).hexdigest()}"
    if not User.objects.filter(username=deterministic).exists():
        return deterministic
    while True:
        candidate = f"sso_{uuid.uuid4().hex}"
        if not User.objects.filter(username=candidate).exists():
            return candidate


def _sync_sso_profile(user, identity: TrustedSsoIdentity):
    update_fields = []
    if user.email.casefold() != identity.email.casefold():
        if User.objects.filter(email__iexact=identity.email).exclude(pk=user.pk).exists():
            raise SsoAccountConflictError
        user.email = identity.email
        update_fields.append("email")
    if not user.email_verified:
        user.email_verified = True
        update_fields.append("email_verified")
    nickname = (identity.display_name or identity.email.split("@", 1)[0])[:50]
    if nickname and user.nickname != nickname:
        user.nickname = nickname
        update_fields.append("nickname")
    if update_fields:
        user.save(update_fields=update_fields)
    return user


def _resolve_sso_user_locked(identity: TrustedSsoIdentity):
    linked = User.objects.select_for_update().filter(sso_subject=identity.subject).first()
    if linked is not None:
        if linked.has_usable_password():
            linked.set_unusable_password()
            linked.save(update_fields=["password"])
        if not linked.is_active:
            return linked
        return _sync_sso_profile(linked, identity)

    email_matches = list(User.objects.select_for_update().filter(email__iexact=identity.email))
    if email_matches:
        if len(email_matches) != 1:
            raise SsoAccountConflictError
        candidate = email_matches[0]
        if (
            not candidate.is_active
            or candidate.sso_subject is not None
            or not candidate.email_verified
            or not candidate.sso_link_allowed
        ):
            raise SsoAccountConflictError
        candidate.sso_subject = identity.subject
        candidate.sso_link_allowed = False
        candidate.nickname = (identity.display_name or candidate.nickname or identity.email.split("@", 1)[0])[:50]
        candidate.set_unusable_password()
        candidate.save(
            update_fields=["sso_subject", "sso_link_allowed", "nickname", "password"]
        )
        return candidate

    user = User(
        email=identity.email,
        email_verified=True,
        username=_internal_sso_username(identity.subject),
        nickname=(identity.display_name or identity.email.split("@", 1)[0])[:50],
        sso_subject=identity.subject,
    )
    user.set_unusable_password()
    user.save()
    return user


def _resolve_sso_user(identity: TrustedSsoIdentity):
    try:
        with transaction.atomic():
            return _resolve_sso_user_locked(identity)
    except IntegrityError as exc:
        concurrent = User.objects.filter(sso_subject=identity.subject).first()
        if concurrent is not None and concurrent.email.casefold() == identity.email.casefold():
            return concurrent
        raise SsoAccountConflictError from exc


def _issue_sso_token_pair(user):
    if not user.sso_subject:
        raise AuthenticationFailed("The account is not linked to an SSO subject.")
    refresh = RefreshToken.for_user(user)
    refresh["sso_subject"] = user.sso_subject
    return refresh


class RegisterView(generics.CreateAPIView):
    authentication_classes = []
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        if settings.PILGRIMAGE_SSO_ENABLED:
            return _sso_disabled_response()
        return super().post(request, *args, **kwargs)


class LoginView(TokenObtainPairView):
    authentication_classes = []
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
        identity = trusted_sso_identity(request)
        try:
            user = _resolve_sso_user(identity)
        except SsoAccountConflictError:
            return Response(
                {"detail": "This SSO identity cannot be linked automatically."},
                status=status.HTTP_409_CONFLICT,
            )
        if not user.is_active:
            return Response({"detail": "This account is disabled."}, status=status.HTTP_403_FORBIDDEN)
        refresh = _issue_sso_token_pair(user)
        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "email": user.email,
                "nickname": user.nickname,
            }
        )


class SsoBoundTokenRefreshView(TokenRefreshView):
    serializer_class = SsoBoundTokenRefreshSerializer


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        raw_refresh = request.data.get("refresh")
        if not isinstance(raw_refresh, str) or not raw_refresh:
            raise ValidationError({"refresh": "This field is required."})
        try:
            refresh = RefreshToken(raw_refresh)
            refresh_user = validate_refresh_binding(request=request, refresh_token=refresh)
            if refresh_user.pk != request.user.pk:
                raise AuthenticationFailed("The refresh token does not belong to this user.")
            refresh.blacklist()
        except TokenError as exc:
            raise InvalidToken("The refresh token is invalid or already revoked.") from exc
        return Response(status=status.HTTP_204_NO_CONTENT)
