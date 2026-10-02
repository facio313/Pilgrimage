from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime, timedelta
from datetime import timezone as datetime_timezone
from importlib import import_module
from threading import Barrier
from types import SimpleNamespace
from unittest.mock import patch

import httpx
from django.apps import apps
from django.db import DatabaseError, close_old_connections, connection, transaction
from django.db.models import Sum
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient, APITransactionTestCase

from apps.spots.models import GooglePlaceCache, GooglePlacesCharge

FAKE_KEY = "regression-only-key-never-sent-to-google"
LEGACY_KEY = "regression-only-previously-exposed-key"
PLACE_ID = "ChIJ_test_place"
PHOTO_NAME = f"places/{PLACE_ID}/photos/test_photo"
PHOTO_URI = "https://lh3.googleusercontent.com/test-photo"
PHOTO_BYTES = b"\x89PNG\r\n\x1a\nregression-image"


def google_response(data=None, *, status=200, content=None):
    kwargs = {"content": content} if content is not None else {"json": data or {}}
    return httpx.Response(
        status,
        request=httpx.Request("GET", "https://places.googleapis.com/v1/test"),
        **kwargs,
    )


def nearby_data():
    return {"places": [{
        "id": PLACE_ID,
        "displayName": {"text": "Test Place"},
        "formattedAddress": "Test Address",
        "rating": 4.5,
        "userRatingCount": 5,
        "googleMapsUri": "https://maps.google.com/?cid=test",
        "photos": [{"name": PHOTO_NAME}],
    }]}


@override_settings(
    GOOGLE_PLACES_ENABLED=True,
    GOOGLE_PLACES_KEY=FAKE_KEY,
    GOOGLE_PLACES_DAILY_BUDGET_KRW=99,
    GOOGLE_PLACES_USD_KRW_CEILING=2000,
)
class PlacesApiTests(APITransactionTestCase):
    """Use committed PostgreSQL state and HTTP mocks, never the paid Google API."""

    def setUp(self):
        super().setUp()
        request_patch = patch("common.places_client.httpx.request")
        stream_patch = patch("common.places.httpx.stream")
        self.google = request_patch.start()
        self.image = stream_patch.start()
        self.addCleanup(request_patch.stop)
        self.addCleanup(stream_patch.stop)
        self.google.side_effect = AssertionError("Unexpected Google request")
        self.image.side_effect = AssertionError("Unexpected image request")

    def spent(self):
        return GooglePlacesCharge.objects.aggregate(total=Sum("reserved_krw"))["total"] or 0

    def seed_place(self, **kwargs):
        return GooglePlaceCache.objects.create(
            lookup_key="37.5000:127.0000", place_id=PLACE_ID, name="Test Place", **kwargs,
        )

    def seed_charge(self, amount, *, at=None):
        return GooglePlacesCharge.objects.create(
            operation="reviews", reserved_krw=amount, reserved_at=at or timezone.now(),
        )

    def nearby(self, **params):
        return self.client.get("/api/places/nearby/", {"lat": 37.5, "lng": 127, **params})

    def reviews(self, place_id=PLACE_ID):
        return self.client.get("/api/places/reviews/", {"place_id": place_id})

    def photo(self, place_id=PLACE_ID):
        return self.client.get("/api/places/photo/", {"place_id": place_id})

    def mock_photo(self, *, uri=PHOTO_URI, status=200, content_type="image/png", content=PHOTO_BYTES):
        self.google.side_effect = [
            google_response({"photos": [{
                "name": PHOTO_NAME,
                "authorAttributions": [{"displayName": "Test Photographer"}],
            }]}),
            google_response({"photoUri": uri}),
        ]

        @contextmanager
        def stream(*args, **kwargs):
            yield httpx.Response(
                status,
                content=content,
                headers={"Content-Type": content_type, "Location": "https://example.invalid/" + FAKE_KEY},
                request=httpx.Request("GET", PHOTO_URI),
            )

        self.image.side_effect = stream

    def test_fresh_and_cached_nearby_never_return_or_persist_server_key(self):
        self.google.side_effect = None
        self.google.return_value = google_response(nearby_data())
        fresh = self.nearby()
        self.assertEqual(fresh.status_code, 200)
        place = fresh.json()["results"][0]
        self.assertEqual(place["photoUrl"], f"/places/photo/?place_id={PLACE_ID}")
        self.assertNotIn(FAKE_KEY, fresh.content.decode())
        self.assertNotIn("places.googleapis.com", fresh.content.decode())
        cached = GooglePlaceCache.objects.get(place_id=PLACE_ID)
        self.assertEqual(cached.photo_url, "")
        self.assertEqual(self.spent(), 77)

        second = APIClient().get("/api/places/nearby/", {"lat": 37.5, "lng": 127})
        self.assertEqual(second.json(), fresh.json())
        self.assertEqual(self.google.call_count, 1)
        self.assertEqual(self.spent(), 77)
        self.assertEqual(self.google.call_args.kwargs["headers"]["X-Goog-Api-Key"], FAKE_KEY)
        self.assertFalse(self.google.call_args.kwargs["follow_redirects"])

    def test_legacy_cached_photo_url_is_never_returned_even_when_disabled(self):
        self.seed_place(photo_url=f"https://places.googleapis.com/v1/{PHOTO_NAME}/media?key={LEGACY_KEY}")
        with override_settings(GOOGLE_PLACES_ENABLED=False):
            response = self.nearby()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["results"][0]["photoUrl"], f"/places/photo/?place_id={PLACE_ID}")
        self.assertNotIn(LEGACY_KEY, response.content.decode())
        self.google.assert_not_called()
        self.image.assert_not_called()
        self.assertEqual(self.spent(), 0)

    def test_named_place_uses_one_text_search_within_budget(self):
        self.google.side_effect = None
        self.google.return_value = google_response(nearby_data())
        response = self.nearby(query="Test Place")
        self.assertEqual(response.json()["results"][0]["placeId"], PLACE_ID)
        self.assertEqual(self.google.call_count, 1)
        self.assertEqual(self.spent(), 77)
        self.assertEqual(self.google.call_args.args[1], "https://places.googleapis.com/v1/places:searchText")
        self.assertEqual(self.google.call_args.kwargs["json"]["textQuery"], "Test Place")
        self.assertTrue(GooglePlaceCache.objects.exists())

    def test_successful_empty_search_can_be_cached_without_more_spend(self):
        self.google.side_effect = None
        self.google.return_value = google_response({"places": []})
        self.assertEqual(self.nearby().json(), {"results": []})
        self.assertEqual(self.nearby().json(), {"results": []})
        self.assertEqual(self.google.call_count, 1)
        self.assertEqual(self.spent(), 77)

    def test_nearby_and_reviews_share_the_same_budget(self):
        self.google.side_effect = None
        self.google.return_value = google_response(nearby_data())
        self.assertEqual(self.nearby().status_code, 200)
        response = self.reviews()
        self.assertEqual(response.json()["status"], "daily_limit")
        self.assertEqual(self.google.call_count, 1)
        self.assertEqual(self.spent(), 77)
        self.assertFalse(GooglePlaceCache.objects.get(place_id=PLACE_ID).reviews_fetched)

    def test_reviews_cache_does_not_consume_budget_again(self):
        self.google.side_effect = None
        self.google.return_value = google_response({"reviews": [{
            "authorAttribution": {"displayName": "Reviewer"},
            "rating": 5, "text": {"text": "Helpful review"},
            "relativePublishTimeDescription": "A day ago",
        }]})
        first = self.reviews()
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json()["reviews"][0]["author"], "Reviewer")
        self.assertEqual(self.spent(), 55)
        self.seed_charge(44)
        self.assertEqual(self.reviews().json(), first.json())
        self.assertEqual(self.google.call_count, 1)
        self.assertEqual(self.spent(), 99)

    def test_maximum_length_place_id_reviews_are_saved_and_reused(self):
        place_id = "P" * 200
        self.google.side_effect = None
        self.google.return_value = google_response({"reviews": [{
            "authorAttribution": {"displayName": "Reviewer"},
            "rating": 5, "text": {"text": "Long ID review"},
        }]})
        first = self.reviews(place_id)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json()["reviews"][0]["text"], "Long ID review")
        cached = GooglePlaceCache.objects.get(place_id=place_id)
        self.assertLessEqual(len(cached.lookup_key), 100)
        self.assertTrue(cached.reviews_fetched)
        self.assertEqual(self.reviews(place_id).json(), first.json())
        self.assertEqual(self.google.call_count, 1)
        self.assertEqual(self.spent(), 55)

    def test_failures_are_charged_without_negative_cache_or_key_in_logs(self):
        failures = [
            httpx.ReadTimeout("timeout " + FAKE_KEY),
            google_response(status=403, content=FAKE_KEY.encode()),
            google_response(content=("not-json " + FAKE_KEY).encode()),
            google_response(["not", "an", "object"]),
        ]
        for failure in failures:
            with self.subTest(failure=type(failure).__name__):
                GooglePlacesCharge.objects.all().delete()
                self.google.reset_mock()
                if isinstance(failure, Exception):
                    self.google.side_effect = failure
                else:
                    self.google.side_effect = None
                    self.google.return_value = failure
                with self.assertLogs("common.places_client", level="WARNING") as logs:
                    response = self.nearby(query="Test Place")
                self.assertEqual(response.json()["status"], "unavailable")
                self.assertEqual(self.spent(), 77)
                self.assertFalse(GooglePlaceCache.objects.exists())
                self.assertEqual(self.google.call_count, 1)
                self.assertNotIn(FAKE_KEY, response.content.decode())
                self.assertNotIn(FAKE_KEY, " ".join(logs.output))

    def test_failed_review_is_charged_without_marking_reviews_fetched(self):
        cached = self.seed_place()
        self.google.side_effect = httpx.ConnectError("offline")
        response = self.reviews()
        self.assertEqual(response.json()["status"], "unavailable")
        self.assertEqual(self.spent(), 55)
        cached.refresh_from_db()
        self.assertFalse(cached.reviews_fetched)

    def test_budget_database_failure_prevents_outbound_request(self):
        with patch("common.places_client.GooglePlacesBudget.objects.get_or_create", side_effect=DatabaseError):
            response = self.nearby()
        self.assertEqual(response.json()["status"], "unavailable")
        self.google.assert_not_called()
        self.image.assert_not_called()
        self.assertEqual(self.spent(), 0)
        self.assertFalse(GooglePlaceCache.objects.exists())

    def test_disabled_and_missing_key_prevent_all_google_calls(self):
        self.seed_place()
        for configuration in ({"GOOGLE_PLACES_ENABLED": False}, {"GOOGLE_PLACES_KEY": ""}):
            with self.subTest(configuration=configuration), override_settings(**configuration):
                self.assertEqual(self.nearby(lat=38).json()["status"], "disabled")
                self.assertEqual(self.reviews().json()["status"], "disabled")
                self.assertEqual(self.photo().status_code, 503)
        self.google.assert_not_called()
        self.image.assert_not_called()
        self.assertEqual(self.spent(), 0)

    def test_unsafe_budget_configuration_fails_closed(self):
        for configuration in (
            {"GOOGLE_PLACES_DAILY_BUDGET_KRW": 100},
            {"GOOGLE_PLACES_DAILY_BUDGET_KRW": 0},
            {"GOOGLE_PLACES_USD_KRW_CEILING": 1999},
        ):
            with self.subTest(configuration=configuration), override_settings(**configuration):
                self.assertEqual(self.nearby().json()["status"], "invalid_configuration")
        self.google.assert_not_called()
        self.assertEqual(self.spent(), 0)

    def test_invalid_input_is_rejected_before_spending(self):
        for params in ({}, {"lat": "nan", "lng": 127}, {"lat": 90.1, "lng": 127},
                       {"lat": 37, "lng": "inf"}, {"lat": 37, "lng": -180.1}):
            with self.subTest(params=params):
                self.assertEqual(self.client.get("/api/places/nearby/", params).status_code, 400)
        for place_id in ("", "../places:searchNearby", "test?key=bad", "x" * 201):
            with self.subTest(place_id=place_id):
                self.assertEqual(self.reviews(place_id).status_code, 400)
                self.assertEqual(self.photo(place_id).status_code, 404)
        self.assertEqual(self.photo("UnknownPlace").status_code, 404)
        self.google.assert_not_called()
        self.image.assert_not_called()
        self.assertEqual(self.spent(), 0)

    def test_photo_uses_shared_budget_and_does_not_forward_key_or_upstream_headers(self):
        self.seed_place()
        self.seed_charge(77)
        self.mock_photo()
        response = self.photo()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, PHOTO_BYTES)
        self.assertEqual(response["Content-Type"], "image/png")
        self.assertEqual(response["Cache-Control"], "private, no-store")
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        self.assertEqual(response["X-Photo-Authors"], '["Test Photographer"]')
        self.assertNotIn("Location", response)
        self.assertNotIn(FAKE_KEY, str(dict(response.items())))
        self.assertNotIn(FAKE_KEY.encode(), response.content)
        self.assertEqual(self.spent(), 94)
        self.assertEqual(list(GooglePlacesCharge.objects.values_list("operation", flat=True)),
                         ["reviews", "photo_metadata", "photo"])
        self.assertEqual(self.google.call_args_list[0].kwargs["headers"]["X-Goog-FieldMask"], "photos")
        self.assertEqual(self.google.call_args_list[1].kwargs["params"]["skipHttpRedirect"], "true")
        self.image.assert_called_once_with("GET", PHOTO_URI, timeout=5, follow_redirects=False)

    def test_photo_media_is_blocked_when_metadata_uses_last_available_budget(self):
        self.seed_place()
        self.seed_charge(83)
        self.mock_photo()
        self.assertEqual(self.photo().status_code, 429)
        self.assertEqual(self.spent(), 84)
        self.assertEqual(self.google.call_count, 1)
        self.image.assert_not_called()

    def test_photo_metadata_is_blocked_when_budget_is_exhausted(self):
        self.seed_place()
        self.seed_charge(99)
        self.assertEqual(self.photo().status_code, 429)
        self.google.assert_not_called()
        self.image.assert_not_called()
        self.assertEqual(self.spent(), 99)

    def test_photo_rejects_untrusted_hosts_before_image_download(self):
        self.seed_place()
        for uri in (
            "http://lh3.googleusercontent.com/image",
            "https://googleusercontent.com.attacker.invalid/image",
            "https://evilgoogleusercontent.com/image",
            "https://127.0.0.1/image",
            "https://user:password@lh3.googleusercontent.com/image",
            "https://lh3.googleusercontent.com:8443/image",
        ):
            with self.subTest(uri=uri):
                GooglePlacesCharge.objects.all().delete()
                self.mock_photo(uri=uri)
                self.assertEqual(self.photo().status_code, 502)
                self.assertEqual(self.spent(), 17)
        self.image.assert_not_called()

    def test_photo_rejects_mismatched_resource_before_media_request(self):
        self.seed_place()
        self.google.side_effect = None
        self.google.return_value = google_response({"photos": [{"name": "places/other/photos/photo"}]})
        self.assertEqual(self.photo().status_code, 502)
        self.assertEqual(self.spent(), 1)
        self.assertEqual(self.google.call_count, 1)
        self.image.assert_not_called()

    def test_photo_redirects_non_images_and_oversized_images_fail_without_refund(self):
        self.seed_place()
        for kwargs in ({"status": 302}, {"content_type": "text/html"}, {"content": b"12345"}):
            with self.subTest(kwargs=kwargs):
                GooglePlacesCharge.objects.all().delete()
                self.mock_photo(**kwargs)
                with patch("common.places.MAX_PHOTO_BYTES", 4):
                    response = self.photo()
                self.assertEqual(response.status_code, 502)
                self.assertNotIn("Location", response)
                self.assertNotIn(FAKE_KEY, str(dict(response.items())))
                self.assertEqual(self.spent(), 17)

    def test_rolling_24_hours_does_not_reset_at_midnight(self):
        now = datetime(2026, 10, 2, 15, 1, tzinfo=datetime_timezone.utc)
        self.seed_charge(55, at=now - timedelta(minutes=2))
        with patch("common.places_client.timezone.now", return_value=now):
            response = self.reviews()
        self.assertEqual(response.json()["status"], "daily_limit")
        self.google.assert_not_called()
        self.assertEqual(self.spent(), 55)

    def test_charge_expires_only_after_full_24_hours_and_unblocks_uncached_lookup(self):
        now = datetime(2026, 10, 2, 15, 1, tzinfo=datetime_timezone.utc)
        self.seed_charge(77, at=now - timedelta(hours=24))
        with patch("common.places_client.timezone.now", return_value=now):
            blocked = self.nearby()
        self.assertEqual(blocked.json()["status"], "daily_limit")
        self.assertFalse(GooglePlaceCache.objects.exists())
        self.google.assert_not_called()
        self.google.side_effect = None
        self.google.return_value = google_response(nearby_data())
        with patch("common.places_client.timezone.now", return_value=now + timedelta(microseconds=1)):
            allowed = self.nearby()
        self.assertEqual(allowed.status_code, 200)
        self.assertEqual(allowed.json()["results"][0]["placeId"], PLACE_ID)
        self.assertEqual(self.google.call_count, 1)

    def test_new_connection_and_client_do_not_reset_budget(self):
        self.google.side_effect = None
        self.google.return_value = google_response({"reviews": []})
        self.assertEqual(self.reviews().json(), {"reviews": []})
        connection.close()
        response = APIClient().get("/api/places/reviews/", {"place_id": "OtherPlace"})
        self.assertEqual(response.json()["status"], "daily_limit")
        self.assertEqual(self.spent(), 55)
        self.assertEqual(self.google.call_count, 1)

    def test_outer_transaction_cannot_make_an_uncommitted_paid_request(self):
        with transaction.atomic():
            response = self.nearby()
            self.assertEqual(response.json()["status"], "unavailable")
            self.assertEqual(self.spent(), 0)
        self.google.assert_not_called()
        self.assertFalse(GooglePlaceCache.objects.exists())

    def test_concurrent_postgresql_requests_cannot_overspend(self):
        self.assertEqual(connection.vendor, "postgresql", "This concurrency proof requires PostgreSQL")
        barrier = Barrier(4)
        self.google.side_effect = None
        self.google.return_value = google_response({"reviews": []})

        def request_review(index):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                response = APIClient().get("/api/places/reviews/", {"place_id": f"ConcurrentPlace{index}"})
                return response.status_code, response.json().get("status", "ok")
            finally:
                connection.close()

        with ThreadPoolExecutor(max_workers=4) as pool:
            responses = list(pool.map(request_review, range(4)))
        self.assertCountEqual(responses, [(200, "ok")] + [(200, "daily_limit")] * 3)
        self.assertEqual(self.google.call_count, 1)
        self.assertEqual(self.spent(), 55)
        self.assertEqual(GooglePlacesCharge.objects.count(), 1)

    def test_cleanup_migration_erases_legacy_urls_without_destroying_cached_data(self):
        cached = self.seed_place(
            photo_url=f"https://places.googleapis.com/v1/{PHOTO_NAME}/media?key={LEGACY_KEY}",
            reviews=[{"text": "Keep this review"}], reviews_fetched=True,
        )
        migration = import_module("apps.spots.migrations.0003_places_budget_and_clear_key_urls")
        migration.clear_key_urls(apps, SimpleNamespace(connection=connection))
        cached.refresh_from_db()
        self.assertEqual(cached.photo_url, "")
        self.assertEqual(cached.place_id, PLACE_ID)
        self.assertEqual(cached.reviews, [{"text": "Keep this review"}])
        self.assertTrue(cached.reviews_fetched)
        self.google.assert_not_called()
