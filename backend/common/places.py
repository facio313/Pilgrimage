import hashlib
import json
import logging
import math
import re
from urllib.parse import urlencode, urlsplit

import httpx
from django.http import HttpResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.spots.models import GooglePlaceCache
from common.places_client import PlacesUnavailableError, request_google

logger = logging.getLogger(__name__)
PLACE_ID = re.compile(r"[A-Za-z0-9_-]{1,200}\Z")
MAX_PHOTO_BYTES = 5 * 1024 * 1024
PHOTO_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif", "image/avif"}


def _nearby_key(lat, lng):
    return f"{float(lat):.4f}:{float(lng):.4f}"


def _photo_url(place_id):
    if not PLACE_ID.fullmatch(place_id):
        return ""
    # Relative to apiClient.baseURL, including deployments under a path prefix.
    return "/places/photo/?" + urlencode({"place_id": place_id})


def _serialize_places(data):
    return [{
        "placeId": place.get("id", ""),
        "name": place.get("displayName", {}).get("text", ""),
        "address": place.get("formattedAddress", ""),
        "rating": place.get("rating"),
        "userRatingCount": place.get("userRatingCount"),
        "photoUrl": _photo_url(place.get("id", "")),
        "googleMapsUri": place.get("googleMapsUri", ""),
    } for place in data.get("places", [])]


def _cache_to_result(cached):
    return {
        "placeId": cached.place_id,
        "name": cached.name,
        "address": cached.address,
        "rating": cached.rating,
        "userRatingCount": cached.user_rating_count,
        # Never read legacy photo_url: it may contain a previously exposed key.
        "photoUrl": _photo_url(cached.place_id),
        "googleMapsUri": cached.google_maps_uri,
    }


def _unavailable(field, error):
    message = (
        "오늘의 Google 정보 조회 한도에 도달했습니다. 잠시 후 다시 확인해 주세요."
        if error.reason == "daily_limit" else "Google 정보를 일시적으로 불러올 수 없습니다."
    )
    return Response({field: [], "status": error.reason, "message": message})


@api_view(["GET"])
@permission_classes([AllowAny])
def place_nearby(request):
    query = request.query_params.get("query", "").strip()[:500]
    try:
        lat = float(request.query_params["lat"])
        lng = float(request.query_params["lng"])
        if not math.isfinite(lat) or not math.isfinite(lng) or not -90 <= lat <= 90 or not -180 <= lng <= 180:
            raise ValueError
    except (KeyError, TypeError, ValueError):
        return Response({"results": []}, status=400)

    key = _nearby_key(lat, lng)
    cached = GooglePlaceCache.objects.filter(lookup_key=key).first()
    if cached is not None:
        return Response({"results": [_cache_to_result(cached)] if cached.place_id else []})

    location_circle = {"circle": {"center": {"latitude": lat, "longitude": lng}, "radius": 500.0}}
    # Two searches cannot fit the daily budget. Use the supplied place name
    # directly instead of spending the budget on a preceding empty Nearby call.
    try:
        if query:
            data = request_google("text", body={
                "textQuery": query, "locationBias": location_circle, "maxResultCount": 1, "languageCode": "ko",
            })
        else:
            data = request_google("nearby", body={
                "locationRestriction": location_circle, "maxResultCount": 1, "languageCode": "ko",
            })
        results = _serialize_places(data)
    except PlacesUnavailableError as error:
        # Limits and temporary failures must not become permanent empty cache entries.
        return _unavailable("results", error)

    if results:
        place = results[0]
        GooglePlaceCache.objects.get_or_create(lookup_key=key, defaults={
            "place_id": place["placeId"], "name": place["name"], "address": place["address"],
            "rating": place["rating"], "user_rating_count": place["userRatingCount"],
            "google_maps_uri": place["googleMapsUri"],
        })
    else:
        GooglePlaceCache.objects.get_or_create(lookup_key=key)
    return Response({"results": results})


@api_view(["GET"])
@permission_classes([AllowAny])
def place_reviews(request):
    place_id = request.query_params.get("place_id", "")
    if not PLACE_ID.fullmatch(place_id):
        return Response({"reviews": []}, status=400)
    cached = GooglePlaceCache.objects.filter(place_id=place_id, reviews_fetched=True).first()
    if cached is not None:
        return Response({"reviews": cached.reviews})
    try:
        data = request_google("reviews", resource=place_id, params={"languageCode": "ko"})
    except PlacesUnavailableError as error:
        return _unavailable("reviews", error)
    reviews = [{
        "author": review.get("authorAttribution", {}).get("displayName", ""),
        "rating": review.get("rating"),
        "text": review.get("text", {}).get("text", ""),
        "relativeTime": review.get("relativePublishTimeDescription", ""),
    } for review in data.get("reviews", [])[:3]]
    updated = GooglePlaceCache.objects.filter(place_id=place_id).update(reviews=reviews, reviews_fetched=True)
    if not updated:
        GooglePlaceCache.objects.create(
            lookup_key="review:" + hashlib.sha256(place_id.encode()).hexdigest(),
            place_id=place_id, reviews=reviews, reviews_fetched=True,
        )
    return Response({"reviews": reviews})


def _photo_host_allowed(url):
    try:
        parsed = urlsplit(url)
        return (
            parsed.scheme == "https" and parsed.hostname is not None
            and parsed.hostname.endswith(".googleusercontent.com")
            and parsed.port in (None, 443) and parsed.username is None and parsed.password is None
        )
    except ValueError:
        return False


@api_view(["GET"])
@permission_classes([AllowAny])
def place_photo(request):
    place_id = request.query_params.get("place_id", "")
    if not PLACE_ID.fullmatch(place_id) or not GooglePlaceCache.objects.filter(place_id=place_id).exists():
        return HttpResponse(status=404)
    try:
        # Photo resource names expire and must not be cached. The photos-only
        # Details mask is the free Essentials IDs Only SKU.
        data = request_google("photo_metadata", resource=place_id)
        photos = data.get("photos", [])
        if not photos:
            return HttpResponse(status=404)
        photo = photos[0]
        name = photo.get("name", "")
        if not re.fullmatch(r"places/" + re.escape(place_id) + r"/photos/[A-Za-z0-9_-]{1,2048}", name):
            return HttpResponse(status=502)
        media = request_google("photo", resource=name, params={"maxWidthPx": 400, "skipHttpRedirect": "true"})
        uri = media.get("photoUri", "")
        if not _photo_host_allowed(uri):
            return HttpResponse(status=502)
        # A separate request sends NO Google API key to the image host and never
        # follows redirects. Neither the upstream URL nor its headers reach users.
        with httpx.stream("GET", uri, timeout=5, follow_redirects=False) as image:
            image.raise_for_status()
            content_type = image.headers.get("content-type", "").split(";", 1)[0]
            if content_type not in PHOTO_TYPES:
                return HttpResponse(status=502)
            content = bytearray()
            for chunk in image.iter_bytes():
                content.extend(chunk)
                if len(content) > MAX_PHOTO_BYTES:
                    return HttpResponse(status=502)
    except PlacesUnavailableError as error:
        return HttpResponse(status=429 if error.reason == "daily_limit" else 503)
    except (httpx.HTTPError, ValueError, TypeError):
        logger.warning("Google Places photo unavailable")
        return HttpResponse(status=502)
    response = HttpResponse(bytes(content), content_type=content_type)
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    # Plain text authors are rendered with textContent by the frontend.
    authors = [str(author.get("displayName", ""))[:200] for author in photo.get("authorAttributions", [])[:10]]
    response["X-Photo-Authors"] = json.dumps(authors, ensure_ascii=True)
    return response
