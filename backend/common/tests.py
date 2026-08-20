import os
import stat
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase
from rest_framework.test import APITestCase

from common.edge_secret import _validate_file_permissions, load_edge_secret


class EdgeSecretTests(SimpleTestCase):
    def test_disabled_sso_does_not_require_a_secret(self):
        self.assertEqual(load_edge_secret(enabled=False, file_path="", fallback=""), b"")

    def test_file_secret_takes_precedence_and_accepts_owner_only_permissions(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "edge-secret"
            path.write_text("f" * 40 + "\n")
            path.chmod(0o600)
            secret = load_edge_secret(enabled=True, file_path=str(path), fallback="x" * 40)
        self.assertEqual(secret, b"f" * 40)

    def test_accepts_root_owned_0640_file_for_non_root_gid_zero_runtime(self):
        metadata = SimpleNamespace(st_mode=stat.S_IFREG | 0o640, st_uid=0, st_gid=0)
        with (
            patch("common.edge_secret.os.geteuid", return_value=10001),
            patch("common.edge_secret.os.getegid", return_value=0),
        ):
            _validate_file_permissions(metadata)

    def test_rejects_root_owned_0640_file_without_effective_gid_zero(self):
        metadata = SimpleNamespace(st_mode=stat.S_IFREG | 0o640, st_uid=0, st_gid=0)
        with (
            patch("common.edge_secret.os.geteuid", return_value=10001),
            patch("common.edge_secret.os.getegid", return_value=10001),
            self.assertRaises(ImproperlyConfigured),
        ):
            _validate_file_permissions(metadata)

    def test_rejects_short_or_overexposed_secret_files(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "edge-secret"
            path.write_text("short")
            path.chmod(0o600)
            with self.assertRaises(ImproperlyConfigured):
                load_edge_secret(enabled=True, file_path=str(path), fallback="")

            path.write_text("f" * 40)
            path.chmod(0o644)
            with self.assertRaises(ImproperlyConfigured):
                load_edge_secret(enabled=True, file_path=str(path), fallback="")

    def test_rejects_symlink_secret_file(self):
        if not hasattr(os, "symlink"):
            self.skipTest("symlinks are unavailable")
        with TemporaryDirectory() as directory:
            target = Path(directory) / "target"
            target.write_text("f" * 40)
            target.chmod(0o600)
            link = Path(directory) / "edge-secret"
            link.symlink_to(target)
            with self.assertRaises(ImproperlyConfigured):
                load_edge_secret(enabled=True, file_path=str(link), fallback="")

    def test_environment_fallback_must_be_at_least_32_printable_ascii_bytes(self):
        with self.assertRaises(ImproperlyConfigured):
            load_edge_secret(enabled=True, file_path="", fallback="too-short")
        with self.assertRaises(ImproperlyConfigured):
            load_edge_secret(enabled=True, file_path="", fallback="x" * 31 + "\n")
        self.assertEqual(
            load_edge_secret(enabled=True, file_path="", fallback="x" * 32),
            b"x" * 32,
        )


class ReadinessTests(APITestCase):
    @patch("common.health.check_redis")
    @patch("common.health.check_database")
    def test_health_checks_database_and_redis_and_ignores_auth_headers(self, database, redis):
        response = self.client.get(
            "/api/health/",
            HTTP_AUTHORIZATION="Bearer forged-token",
            HTTP_REMOTE_USER="forged-user",
            HTTP_X_PORTFOLIO_EDGE_SECRET="forged-edge-secret",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["dependencies"], {"database": "ok", "redis": "ok"})
        database.assert_called_once_with()
        redis.assert_called_once_with()

    @patch("common.health.check_redis", side_effect=ConnectionError)
    @patch("common.health.check_database")
    def test_health_returns_503_without_leaking_dependency_details(self, database, redis):
        response = self.client.get("/api/health/")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.data, {"status": "unavailable"})
        database.assert_called_once_with()
        redis.assert_called_once_with()
