import logging

import httpx
from decouple import config
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.spots.models import GooglePlaceCache

logger = logging.getLogger(__name__)

GOOGLE_PLACES_KEY = config("GOOGLE_PLACES_KEY", default="")
NEARBY_URL = "https://places.googleapis.com/v1/places:searchNearby"
TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
PLACE_DETAIL_URL_TPL = "https://places.googleapis.com/v1/places/{place_id}"
PHOTO_URL_TPL = "https://places.googleapis.com/v1/{name}/media?maxWidthPx=400&key={key}"


def _nearby_key(lat, lng):
    return f"{float(lat):.4f}:{float(lng):.4f}"


def _serialize_places(data):
    results = []
    for place in data.get("places", []):
        photo_url = ""
        photos = place.get("photos", [])
        if photos:
            photo_ref = photos[0].get("name", "")
            if photo_ref:
                photo_url = PHOTO_URL_TPL.format(name=photo_ref, key=GOOGLE_PLACES_KEY)

        results.append({
            "placeId": place.get("id", ""),
            "name": place.get("displayName", {}).get("text", ""),
            "address": place.get("formattedAddress", ""),
            "rating": place.get("rating"),
            "userRatingCount": place.get("userRatingCount"),
            "photoUrl": photo_url,
            "googleMapsUri": place.get("googleMapsUri", ""),
        })
    return results


def _request_places(url, body, headers):
    resp = httpx.post(url, json=body, headers=headers, timeout=5)
    data = resp.json()
    if resp.status_code != 200:
        logger.warning("Google Places API error: %s %s", resp.status_code, resp.text[:300])
        return []
    return _serialize_places(data)


def _cache_to_result(cached):
    return {
        "placeId": cached.place_id,
        "name": cached.name,
        "address": cached.address,
        "rating": cached.rating,
        "userRatingCount": cached.user_rating_count,
        "photoUrl": cached.photo_url,
        "googleMapsUri": cached.google_maps_uri,
    }


@api_view(["GET"])
@permission_classes([AllowAny])
def place_nearby(request):
    lat = request.query_params.get("lat")
    lng = request.query_params.get("lng")
    query = request.query_params.get("query", "").strip()
    if not lat or not lng:
        return Response({"results": []})

    key = _nearby_key(lat, lng)

    # DB 캐시 확인 — None이 아니면 이전에 API를 호출한 기록이 있음
    cached = GooglePlaceCache.objects.filter(lookup_key=key).first()
    if cached is not None:
        if not cached.place_id:
            return Response({"results": []})
        return Response({"results": [_cache_to_result(cached)]})

    if not GOOGLE_PLACES_KEY:
        try:
            GooglePlaceCache.objects.get_or_create(lookup_key=key)
        except Exception:
            pass
        return Response({"results": []})

    location_circle = {
        "circle": {
            "center": {"latitude": float(lat), "longitude": float(lng)},
            "radius": 500.0,
        }
    }
    nearby_body = {
        "locationRestriction": location_circle,
        "maxResultCount": 1,
        "languageCode": "ko",
    }
    text_body = {
        "textQuery": query,
        "locationBias": location_circle,
        "maxResultCount": 1,
        "languageCode": "ko",
    }
    headers = {
        "X-Goog-Api-Key": GOOGLE_PLACES_KEY,
        "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,places.rating,places.userRatingCount,places.photos,places.googleMapsUri",
    }

    results = []
    try:
        results = _request_places(NEARBY_URL, nearby_body, headers)
    except Exception as e:
        logger.warning("Google Places nearby exception: %s", e)

    if not results and query:
        try:
            results = _request_places(TEXT_SEARCH_URL, text_body, headers)
        except Exception as e:
            logger.warning("Google Places text search exception: %s", e)

    # DB 저장 — 결과 없어도 저장해서 재호출 방지
    try:
        if results:
            place = results[0]
            GooglePlaceCache.objects.get_or_create(
                lookup_key=key,
                defaults={
                    "place_id": place["placeId"],
                    "name": place["name"],
                    "address": place["address"],
                    "rating": place["rating"],
                    "user_rating_count": place["userRatingCount"],
                    "photo_url": place["photoUrl"],
                    "google_maps_uri": place["googleMapsUri"],
                },
            )
        else:
            GooglePlaceCache.objects.get_or_create(lookup_key=key)
    except Exception as e:
        logger.warning("GooglePlaceCache save error: %s", e)

    return Response({"results": results})


@api_view(["GET"])
@permission_classes([AllowAny])
def place_reviews(request):
    place_id = request.query_params.get("place_id")
    if not place_id:
        return Response({"reviews": []})

    # DB 캐시 확인
    cached = GooglePlaceCache.objects.filter(place_id=place_id, reviews_fetched=True).first()
    if cached is not None:
        return Response({"reviews": cached.reviews})

    if not GOOGLE_PLACES_KEY:
        return Response({"reviews": []})

    url = PLACE_DETAIL_URL_TPL.format(place_id=place_id)
    headers = {
        "X-Goog-Api-Key": GOOGLE_PLACES_KEY,
        "X-Goog-FieldMask": "reviews",
    }

    try:
        resp = httpx.get(url, headers=headers, params={"languageCode": "ko"}, timeout=5)
        data = resp.json()
        if resp.status_code != 200:
            logger.warning("Google Places reviews error: %s %s", resp.status_code, resp.text[:300])
            return Response({"reviews": [], "_debug": {"status": resp.status_code}})
    except Exception as e:
        logger.warning("Google Places reviews exception: %s", e)
        return Response({"reviews": []})

    reviews = []
    for r in data.get("reviews", [])[:3]:
        reviews.append({
            "author": r.get("authorAttribution", {}).get("displayName", ""),
            "rating": r.get("rating"),
            "text": r.get("text", {}).get("text", ""),
            "relativeTime": r.get("relativePublishTimeDescription", ""),
        })

    # DB 저장
    try:
        updated = GooglePlaceCache.objects.filter(place_id=place_id).update(
            reviews=reviews, reviews_fetched=True
        )
        if not updated:
            GooglePlaceCache.objects.create(
                lookup_key=f"review:{place_id}",
                place_id=place_id,
                reviews=reviews,
                reviews_fetched=True,
            )
    except Exception as e:
        logger.warning("GooglePlaceCache reviews save error: %s", e)

    return Response({"reviews": reviews})
