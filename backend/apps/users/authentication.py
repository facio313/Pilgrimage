import hmac
from dataclasses import dataclass

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.settings import api_settings

INVALID_IDENTITY_MESSAGE = "A validated proxy identity is required."
PORTFOLIO_ROLE_ORDER = ("user", "developer", "admin")
PORTFOLIO_ROLE_RANK = {
    role: rank for rank, role in enumerate(PORTFOLIO_ROLE_ORDER)
}
PORTFOLIO_GROUP_CONTRACT = {
    "user": ("user",),
    "user,developer": ("user", "developer"),
    "user,developer,admin": ("user", "developer", "admin"),
}


@dataclass(frozen=True)
class TrustedSsoIdentity:
    subject: str
    email: str
    display_name: str
    groups: tuple[str, ...]
    role: str


def constant_time_equal(left: str, right: str) -> bool:
    return hmac.compare_digest(left.encode("utf-8"), right.encode("utf-8"))


def _valid_header_value(value: str, max_length: int) -> bool:
    return (
        bool(value)
        and len(value) <= max_length
        and not any(ord(character) < 32 or ord(character) == 127 for character in value)
    )


def _trusted_role_groups(raw_groups: object) -> tuple[tuple[str, ...], str]:
    if not isinstance(raw_groups, str) or not _valid_header_value(raw_groups, 1024):
        raise AuthenticationFailed(INVALID_IDENTITY_MESSAGE)
    groups = PORTFOLIO_GROUP_CONTRACT.get(raw_groups)
    if groups is None:
        raise AuthenticationFailed(INVALID_IDENTITY_MESSAGE)
    role = groups[-1]
    return groups, role


def trusted_sso_identity(request) -> TrustedSsoIdentity:
    provided_secret = request.META.get("HTTP_X_PORTFOLIO_EDGE_SECRET", "")
    expected_secret = settings.PILGRIMAGE_SSO_EDGE_SECRET
    if isinstance(expected_secret, str):
        expected_secret = expected_secret.encode("ascii")
    try:
        provided_secret_bytes = provided_secret.encode("ascii")
    except UnicodeEncodeError as exc:
        raise AuthenticationFailed(INVALID_IDENTITY_MESSAGE) from exc
    if not hmac.compare_digest(provided_secret_bytes, expected_secret):
        raise AuthenticationFailed(INVALID_IDENTITY_MESSAGE)

    raw_subject = request.META.get("HTTP_REMOTE_USER", "")
    subject = raw_subject.strip()
    email = request.META.get("HTTP_REMOTE_EMAIL", "").strip().lower()
    display_name = request.META.get("HTTP_REMOTE_NAME", "").strip()
    groups, role = _trusted_role_groups(request.META.get("HTTP_REMOTE_GROUPS", ""))
    if raw_subject != subject or not _valid_header_value(subject, 255) or not _valid_header_value(email, 254):
        raise AuthenticationFailed(INVALID_IDENTITY_MESSAGE)
    if display_name and not _valid_header_value(display_name, 254):
        raise AuthenticationFailed(INVALID_IDENTITY_MESSAGE)
    try:
        validate_email(email)
    except ValidationError as exc:
        raise AuthenticationFailed(INVALID_IDENTITY_MESSAGE) from exc
    return TrustedSsoIdentity(
        subject=subject,
        email=email,
        display_name=display_name,
        groups=groups,
        role=role,
    )


def validate_subject_binding(
    *,
    identity: TrustedSsoIdentity,
    token_subject: object,
    token_groups: object,
    token_role: object,
    user,
) -> None:
    token_value = token_subject if isinstance(token_subject, str) else ""
    user_value = user.sso_subject or ""
    if not token_value or not user_value:
        raise AuthenticationFailed("The SSO-bound token is invalid.")
    if not constant_time_equal(identity.subject, token_value) or not constant_time_equal(token_value, user_value):
        raise AuthenticationFailed("The SSO identity does not match this token.")
    if not isinstance(token_role, str) or not constant_time_equal(identity.role, token_role):
        raise AuthenticationFailed("The SSO role does not match this token.")
    if not isinstance(token_groups, list) or tuple(token_groups) != identity.groups:
        raise AuthenticationFailed("The SSO groups do not match this token.")


def validate_refresh_binding(*, request, refresh_token):
    user_id = refresh_token.get(api_settings.USER_ID_CLAIM)
    if user_id is None:
        raise AuthenticationFailed("The refresh token is invalid.")
    user = (
        get_user_model()
        .objects.filter(
            **{api_settings.USER_ID_FIELD: user_id},
            is_active=True,
        )
        .first()
    )
    if user is None:
        raise AuthenticationFailed("The refresh token is invalid.")
    if settings.PILGRIMAGE_SSO_ENABLED:
        identity = trusted_sso_identity(request)
        validate_subject_binding(
            identity=identity,
            token_subject=refresh_token.get("sso_subject"),
            token_groups=refresh_token.get("sso_groups"),
            token_role=refresh_token.get("sso_role"),
            user=user,
        )
        request.portfolio_sso_identity = identity
    return user


class SsoBoundJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        result = super().authenticate(request)
        if result is None or not settings.PILGRIMAGE_SSO_ENABLED:
            return result

        user, validated_token = result
        identity = trusted_sso_identity(request)
        validate_subject_binding(
            identity=identity,
            token_subject=validated_token.get("sso_subject"),
            token_groups=validated_token.get("sso_groups"),
            token_role=validated_token.get("sso_role"),
            user=user,
        )
        request.portfolio_sso_identity = identity
        return user, validated_token
