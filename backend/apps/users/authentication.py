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
PORTFOLIO_ROLE_ORDER = ("user", "admin", "chief-admin")
PORTFOLIO_ROLE_RANK = {
    role: rank for rank, role in enumerate(PORTFOLIO_ROLE_ORDER)
}
PORTFOLIO_V2_MARKER = "portfolio-v2"
PORTFOLIO_LEGACY_VERSION = "portfolio-v1"
PILGRIMAGE_ENTITLEMENT = "access-pilgrimage"
PORTFOLIO_GRANT_ORDER = (
    "access-react",
    "access-vue",
    "access-dukkeobi",
    "access-ddit-finalproject",
    "access-monitor",
    PILGRIMAGE_ENTITLEMENT,
    "access-multtara",
    "access-feelmyrythm",
    "access-garak",
)
PORTFOLIO_GRANT_RANK = {
    grant: rank for rank, grant in enumerate(PORTFOLIO_GRANT_ORDER)
}
PORTFOLIO_LEGACY_CONTRACT = {
    "user": "user",
    "user,developer": "user",
    "user,developer,admin": "chief-admin",
}


@dataclass(frozen=True)
class TrustedSsoIdentity:
    subject: str
    email: str
    display_name: str
    role: str
    entitlement: str
    contract_version: str


def constant_time_equal(left: str, right: str) -> bool:
    return hmac.compare_digest(left.encode("utf-8"), right.encode("utf-8"))


def _valid_header_value(value: str, max_length: int) -> bool:
    return (
        bool(value)
        and len(value) <= max_length
        and not any(ord(character) < 32 or ord(character) == 127 for character in value)
    )


def _trusted_assignment(raw_groups: object) -> tuple[str, str]:
    if not isinstance(raw_groups, str) or not _valid_header_value(raw_groups, 1024):
        raise AuthenticationFailed(INVALID_IDENTITY_MESSAGE)

    legacy_role = PORTFOLIO_LEGACY_CONTRACT.get(raw_groups)
    if legacy_role is not None:
        return legacy_role, PORTFOLIO_LEGACY_VERSION

    groups = raw_groups.split(",")
    if not groups or groups[0] != "user":
        raise AuthenticationFailed(INVALID_IDENTITY_MESSAGE)

    marker_index = 1
    role = "user"
    if len(groups) > marker_index and groups[marker_index] == "admin":
        role = "admin"
        marker_index += 1
        if len(groups) > marker_index and groups[marker_index] == "chief-admin":
            role = "chief-admin"
            marker_index += 1

    if len(groups) <= marker_index or groups[marker_index] != PORTFOLIO_V2_MARKER:
        raise AuthenticationFailed(INVALID_IDENTITY_MESSAGE)

    grants = groups[marker_index + 1 :]
    if role == "chief-admin":
        if grants:
            raise AuthenticationFailed(INVALID_IDENTITY_MESSAGE)
        return role, PORTFOLIO_V2_MARKER

    previous_rank = -1
    for grant in grants:
        rank = PORTFOLIO_GRANT_RANK.get(grant)
        if rank is None or rank <= previous_rank:
            raise AuthenticationFailed(INVALID_IDENTITY_MESSAGE)
        previous_rank = rank

    if PILGRIMAGE_ENTITLEMENT not in grants:
        raise AuthenticationFailed(INVALID_IDENTITY_MESSAGE)
    return role, PORTFOLIO_V2_MARKER


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
    role, contract_version = _trusted_assignment(
        request.META.get("HTTP_REMOTE_GROUPS", "")
    )
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
        role=role,
        entitlement=PILGRIMAGE_ENTITLEMENT,
        contract_version=contract_version,
    )


def validate_subject_binding(
    *,
    identity: TrustedSsoIdentity,
    token_subject: object,
    token_role: object,
    token_entitlement: object,
    token_contract_version: object,
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
    if not isinstance(token_entitlement, str) or not constant_time_equal(
        identity.entitlement, token_entitlement
    ):
        raise AuthenticationFailed("The SSO entitlement does not match this token.")
    if not isinstance(token_contract_version, str) or not constant_time_equal(
        identity.contract_version, token_contract_version
    ):
        raise AuthenticationFailed("The SSO contract version does not match this token.")


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
            token_role=refresh_token.get("sso_role"),
            token_entitlement=refresh_token.get("sso_entitlement"),
            token_contract_version=refresh_token.get("sso_contract_version"),
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
            token_role=validated_token.get("sso_role"),
            token_entitlement=validated_token.get("sso_entitlement"),
            token_contract_version=validated_token.get("sso_contract_version"),
            user=user,
        )
        request.portfolio_sso_identity = identity
        return user, validated_token
