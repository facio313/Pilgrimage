"""The only boundary for Google Places requests and their committed cost reservations."""

import logging
from datetime import timedelta
from decimal import ROUND_CEILING, Decimal

import httpx
from django.conf import settings
from django.db import DatabaseError, transaction
from django.db.models import Sum
from django.utils import timezone

from apps.spots.models import GooglePlacesBudget, GooglePlacesCharge

logger = logging.getLogger(__name__)

# USD/request, first paid tier, checked 2026-10-02. Fixed masks below determine SKU.
# https://developers.google.com/maps/billing-and-pricing/pricing
SEARCH_FIELDS = (
    "places.id,places.displayName,places.formattedAddress,places.rating,"
    "places.userRatingCount,places.googleMapsUri"
)
OPERATIONS = {
    "nearby": ("POST", "places:searchNearby", SEARCH_FIELDS, Decimal("0.035")),
    "text": ("POST", "places:searchText", SEARCH_FIELDS, Decimal("0.035")),
    "reviews": ("GET", "places/{resource}", "reviews", Decimal("0.025")),
    "photo_metadata": ("GET", "places/{resource}", "photos", Decimal("0")),
    "photo": ("GET", "{resource}/media", "", Decimal("0.007")),
}


class PlacesUnavailableError(Exception):
    def __init__(self, reason):
        self.reason = reason
        super().__init__(reason)


def reserve_cost(operation):
    if not settings.GOOGLE_PLACES_ENABLED or not settings.GOOGLE_PLACES_KEY:
        raise PlacesUnavailableError("disabled")
    budget = settings.GOOGLE_PLACES_DAILY_BUDGET_KRW
    exchange_ceiling = settings.GOOGLE_PLACES_USD_KRW_CEILING
    if not 0 < budget < 100 or exchange_ceiling < 2000:
        raise PlacesUnavailableError("invalid_configuration")
    # Even free photo metadata reserves 1 KRW so it cannot be requested indefinitely.
    cost = max(1, int((OPERATIONS[operation][3] * exchange_ceiling * Decimal("1.10")).to_integral_value(
        rounding=ROUND_CEILING,
    )))
    try:
        # durable=True refuses a surrounding production transaction: the charge
        # must COMMIT before the request, even if its caller later fails.
        with transaction.atomic(durable=True):
            GooglePlacesBudget.objects.get_or_create(pk=1)
            GooglePlacesBudget.objects.select_for_update().get(pk=1)
            now = timezone.now()
            spent = GooglePlacesCharge.objects.filter(
                reserved_at__gte=now - timedelta(hours=24),
            ).aggregate(total=Sum("reserved_krw"))["total"] or 0
            if spent + cost > budget:
                raise PlacesUnavailableError("daily_limit")
            GooglePlacesCharge.objects.create(operation=operation, reserved_krw=cost, reserved_at=now)
    except (DatabaseError, RuntimeError):
        logger.warning("Google Places budget storage unavailable")
        raise PlacesUnavailableError("unavailable") from None


def request_google(operation, *, resource="", body=None, params=None):
    method, path, fields, _ = OPERATIONS[operation]
    reserve_cost(operation)
    headers = {"X-Goog-Api-Key": settings.GOOGLE_PLACES_KEY}
    if fields:
        headers["X-Goog-FieldMask"] = fields
    try:
        response = httpx.request(
            method,
            "https://places.googleapis.com/v1/" + path.format(resource=resource),
            headers=headers,
            json=body,
            params=params,
            timeout=5,
            follow_redirects=False,
        )
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise ValueError("invalid response")
        return data
    except (httpx.HTTPError, ValueError):
        # Do not log upstream bodies, request URLs or exception text: old URLs
        # and unexpected upstream errors can contain credentials.
        logger.warning("Google Places request failed (%s)", operation)
        raise PlacesUnavailableError("unavailable") from None
