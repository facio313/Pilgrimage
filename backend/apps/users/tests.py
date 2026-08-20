import uuid

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import DatabaseError, transaction
from django.test import override_settings
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

User = get_user_model()
EDGE_SECRET = "edge-secret-for-pilgrimage-tests-1234567890"


def sso_headers(
    *,
    subject="portfolio-owner",
    email="owner@example.test",
    name="Portfolio Owner",
    secret=EDGE_SECRET,
):
    return {
        "HTTP_REMOTE_USER": subject,
        "HTTP_REMOTE_EMAIL": email,
        "HTTP_REMOTE_NAME": name,
        "HTTP_X_PORTFOLIO_EDGE_SECRET": secret,
    }


@override_settings(
    PILGRIMAGE_SSO_ENABLED=True,
    PILGRIMAGE_SSO_EDGE_SECRET=EDGE_SECRET.encode("ascii"),
)
class SsoAuthenticationTests(APITestCase):
    def exchange(self, **headers):
        request_headers = sso_headers(**headers) if headers else sso_headers()
        return self.client.post("/api/auth/sso/", {}, format="json", **request_headers)

    def test_exchange_requires_identity_and_edge_secret(self):
        self.assertEqual(self.client.post("/api/auth/sso/", {}, format="json").status_code, 403)
        self.assertEqual(self.exchange(secret="wrong-edge-secret").status_code, 403)
        self.assertEqual(self.exchange(subject=" portfolio-owner").status_code, 403)

    def test_exchange_creates_subject_bound_user_and_jwt_pair(self):
        response = self.exchange()
        self.assertEqual(response.status_code, 200)
        user = User.objects.get(email="owner@example.test")
        self.assertEqual(user.sso_subject, "portfolio-owner")
        self.assertNotEqual(user.username, "portfolio-owner")
        self.assertTrue(user.email_verified)
        self.assertFalse(user.has_usable_password())
        self.assertEqual(RefreshToken(response.data["refresh"])["sso_subject"], "portfolio-owner")
        self.assertEqual(AccessToken(response.data["access"])["sso_subject"], "portfolio-owner")

        repeated = self.exchange(email="OWNER@example.test", name="Changed Name")
        self.assertEqual(repeated.status_code, 200)
        self.assertEqual(User.objects.filter(sso_subject="portfolio-owner").count(), 1)

    def test_remote_username_never_takes_over_a_local_username(self):
        local = User.objects.create_user(
            username="portfolio-owner",
            email="different@example.test",
            password="local-only-password",
        )
        response = self.exchange(email="new-owner@example.test")
        self.assertEqual(response.status_code, 200)
        local.refresh_from_db()
        self.assertIsNone(local.sso_subject)
        linked = User.objects.get(sso_subject="portfolio-owner")
        self.assertNotEqual(linked.pk, local.pk)

    def test_existing_email_requires_verified_one_time_link_approval(self):
        local = User.objects.create_user(
            username="local-user",
            email="owner@example.test",
            password="local-only-password",
        )
        self.assertEqual(self.exchange().status_code, 409)

        local.email_verified = True
        local.save(update_fields=["email_verified"])
        self.assertEqual(self.exchange().status_code, 409)

        local.sso_link_allowed = True
        local.save(update_fields=["sso_link_allowed"])
        self.assertEqual(self.exchange().status_code, 200)
        local.refresh_from_db()
        self.assertEqual(local.sso_subject, "portfolio-owner")
        self.assertFalse(local.sso_link_allowed)

        self.assertEqual(
            self.exchange(subject="different-subject", email="owner@example.test").status_code,
            409,
        )

    def test_prepare_link_command_requires_exact_unique_user(self):
        user = User.objects.create_user(
            username="local-user",
            email="owner@example.test",
            password="local-only-password",
        )
        call_command(
            "prepare_sso_link",
            user_id=str(user.pk),
            verified_email="OWNER@example.test",
            verbosity=0,
        )
        user.refresh_from_db()
        self.assertTrue(user.email_verified)
        self.assertTrue(user.sso_link_allowed)

    def test_prepare_link_command_rejects_invalid_email(self):
        user = User.objects.create_user(
            username="local-user",
            email="owner@example.test",
            password="local-only-password",
        )
        with self.assertRaises(CommandError):
            call_command(
                "prepare_sso_link",
                user_id=str(user.pk),
                verified_email="not-an-email",
                verbosity=0,
            )
        user.refresh_from_db()
        self.assertFalse(user.email_verified)
        self.assertFalse(user.sso_link_allowed)

    def test_established_subject_is_immutable(self):
        self.assertEqual(self.exchange().status_code, 200)
        user = User.objects.get(sso_subject="portfolio-owner")
        user.sso_subject = "replacement-subject"
        with self.assertRaises(ValidationError):
            user.save(update_fields=["sso_subject"])

        with self.assertRaises(DatabaseError), transaction.atomic():
            User.objects.filter(pk=user.pk).update(sso_subject=None)
        user.refresh_from_db()
        self.assertEqual(user.sso_subject, "portfolio-owner")

    def test_access_token_requires_matching_current_edge_identity(self):
        exchange = self.exchange()
        access = exchange.data["access"]
        route_url = f"/api/routes/{uuid.uuid4()}/"

        accepted = self.client.get(
            route_url,
            HTTP_AUTHORIZATION=f"Bearer {access}",
            **sso_headers(),
        )
        self.assertEqual(accepted.status_code, 404)

        missing_edge = self.client.get(
            route_url,
            HTTP_AUTHORIZATION=f"Bearer {access}",
            HTTP_REMOTE_USER="portfolio-owner",
            HTTP_REMOTE_EMAIL="owner@example.test",
        )
        self.assertEqual(missing_edge.status_code, 401)

        wrong_subject = self.client.get(
            route_url,
            HTTP_AUTHORIZATION=f"Bearer {access}",
            **sso_headers(subject="another-owner"),
        )
        self.assertEqual(wrong_subject.status_code, 401)

    def test_refresh_requires_subject_bound_token_and_current_identity(self):
        exchange = self.exchange()
        refresh = exchange.data["refresh"]

        accepted = self.client.post(
            "/api/auth/refresh/",
            {"refresh": refresh},
            format="json",
            **sso_headers(),
        )
        self.assertEqual(accepted.status_code, 200)
        self.assertEqual(AccessToken(accepted.data["access"])["sso_subject"], "portfolio-owner")

        rejected = self.client.post(
            "/api/auth/refresh/",
            {"refresh": refresh},
            format="json",
            **sso_headers(subject="another-owner"),
        )
        self.assertEqual(rejected.status_code, 401)

        user = User.objects.get(sso_subject="portfolio-owner")
        unbound = RefreshToken.for_user(user)
        rejected_unbound = self.client.post(
            "/api/auth/refresh/",
            {"refresh": str(unbound)},
            format="json",
            **sso_headers(),
        )
        self.assertEqual(rejected_unbound.status_code, 401)

    def test_logout_revokes_refresh_even_when_central_redirect_is_client_side(self):
        exchange = self.exchange()
        response = self.client.post(
            "/api/auth/logout/",
            {"refresh": exchange.data["refresh"]},
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {exchange.data['access']}",
            **sso_headers(),
        )
        self.assertEqual(response.status_code, 204)
        rejected = self.client.post(
            "/api/auth/refresh/",
            {"refresh": exchange.data["refresh"]},
            format="json",
            **sso_headers(),
        )
        self.assertEqual(rejected.status_code, 401)

    def test_disabled_linked_account_cannot_exchange(self):
        self.assertEqual(self.exchange().status_code, 200)
        User.objects.filter(sso_subject="portfolio-owner").update(is_active=False)
        self.assertEqual(self.exchange().status_code, 403)

    def test_local_registration_and_login_are_disabled(self):
        self.assertEqual(
            self.client.post(
                "/api/auth/register/",
                {"email": "new@example.test", "password": "valid password"},
                format="json",
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.post(
                "/api/auth/login/",
                {"username": "new@example.test", "password": "valid password"},
                format="json",
            ).status_code,
            403,
        )


@override_settings(PILGRIMAGE_SSO_ENABLED=False)
class LocalAuthenticationCompatibilityTests(APITestCase):
    def test_refresh_remains_compatible_when_sso_is_disabled(self):
        user = User.objects.create_user(
            username="local-user",
            email="local@example.test",
            password="local-only-password",
        )
        refresh = RefreshToken.for_user(user)
        response = self.client.post(
            "/api/auth/refresh/",
            {"refresh": str(refresh)},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
