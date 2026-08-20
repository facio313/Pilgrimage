from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APITestCase

User = get_user_model()


@override_settings(PILGRIMAGE_SSO_ENABLED=True)
class SsoAuthenticationTests(APITestCase):
    def test_exchange_requires_validated_proxy_headers(self):
        response = self.client.post("/api/auth/sso/", {}, format="json")
        self.assertEqual(response.status_code, 401)

    def test_exchange_creates_unusable_user_and_returns_jwt_pair(self):
        response = self.client.post(
            "/api/auth/sso/",
            {},
            format="json",
            HTTP_REMOTE_USER="portfolio-owner",
            HTTP_REMOTE_EMAIL="owner@example.test",
            HTTP_REMOTE_NAME="Portfolio Owner",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        user = User.objects.get(email="owner@example.test")
        self.assertFalse(user.has_usable_password())
        self.assertEqual(user.nickname, "Portfolio Owner")

        repeated = self.client.post(
            "/api/auth/sso/",
            {},
            format="json",
            HTTP_REMOTE_USER="portfolio-owner",
            HTTP_REMOTE_EMAIL="OWNER@example.test",
            HTTP_REMOTE_NAME="Changed Name",
        )
        self.assertEqual(repeated.status_code, 200)
        self.assertEqual(User.objects.filter(email__iexact="owner@example.test").count(), 1)

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
