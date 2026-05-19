"""
Kakao Mobility Directions API proxy.

Accepts origin/destination/waypoints, calls Kakao Mobility,
and returns simplified polyline + distance + duration.

API docs: https://developers.kakaomobility.com/docs/navi-api/directions/
"""

import logging

import httpx
from decouple import config
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

logger = logging.getLogger(__name__)

KAKAO_REST_API_KEY = config("KAKAO_REST_API_KEY", default="")
KAKAO_DIRECTIONS_URL = "https://apis-navi.kakaomobility.com/v1/directions"
KAKAO_DIRECTIONS_TIMEOUT = 5.0


def _parse_coord(value: str) -> tuple[float, float] | None:
    """Parse 'lng,lat' string into (lng, lat) tuple."""
    parts = value.split(",")
    if len(parts) != 2:
        return None
    try:
        return float(parts[0].strip()), float(parts[1].strip())
    except ValueError:
        return None


def _extract_polyline(route: dict) -> list[dict]:
    """
    Extract polyline coordinates from Kakao Mobility response.
    route.sections[].roads[].vertexes = [lng, lat, lng, lat, ...]
    Returns list of {lat, lng} dicts.
    """
    coords = []
    seen = set()
    for section in route.get("sections", []):
        for road in section.get("roads", []):
            vertexes = road.get("vertexes", [])
            for i in range(0, len(vertexes) - 1, 2):
                lng = vertexes[i]
                lat = vertexes[i + 1]
                key = (round(lat, 6), round(lng, 6))
                if key not in seen:
                    seen.add(key)
                    coords.append({"lat": lat, "lng": lng})
    return coords


def _extract_sections(route: dict) -> list[dict]:
    """Extract per-section summary (distance, duration)."""
    sections = []
    for section in route.get("sections", []):
        sections.append({
            "distance_m": section.get("distance", 0),
            "duration_sec": section.get("duration", 0),
        })
    return sections


@api_view(["GET"])
@permission_classes([AllowAny])
def directions(request):
    """
    GET /api/directions/?origin=lng,lat&destination=lng,lat&waypoints=lng,lat|lng,lat&priority=RECOMMEND

    Proxies to Kakao Mobility Directions API.
    Returns simplified polyline + distance + duration.
    """
    if not KAKAO_REST_API_KEY:
        return Response(
            {"error": {"code": "CONFIG_ERROR", "message": "KAKAO_REST_API_KEY not configured", "detail": {}}},
            status=500,
        )

    origin_raw = request.query_params.get("origin", "")
    destination_raw = request.query_params.get("destination", "")

    origin = _parse_coord(origin_raw)
    destination = _parse_coord(destination_raw)

    if not origin or not destination:
        return Response(
            {"error": {
                "code": "INVALID_PARAMS",
                "message": "origin and destination required (format: lng,lat)",
                "detail": {},
            }},
            status=400,
        )

    priority = request.query_params.get("priority", "RECOMMEND")
    if priority not in ("RECOMMEND", "DISTANCE", "TIME"):
        priority = "RECOMMEND"

    params = {
        "origin": origin_raw,
        "destination": destination_raw,
        "priority": priority,
    }

    waypoints_raw = request.query_params.get("waypoints", "")
    if waypoints_raw:
        params["waypoints"] = waypoints_raw

    headers = {
        "Authorization": f"KakaoAK {KAKAO_REST_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        with httpx.Client(timeout=KAKAO_DIRECTIONS_TIMEOUT) as client:
            resp = client.get(KAKAO_DIRECTIONS_URL, params=params, headers=headers)
    except httpx.TimeoutException:
        return Response(
            {"error": {"code": "UPSTREAM_TIMEOUT", "message": "Kakao Mobility API timeout", "detail": {}}},
            status=504,
        )
    except httpx.HTTPError as exc:
        logger.exception("Kakao Mobility API error")
        return Response(
            {"error": {"code": "UPSTREAM_ERROR", "message": str(exc), "detail": {}}},
            status=502,
        )

    if resp.status_code != 200:
        logger.warning("Kakao Mobility API returned %s: %s", resp.status_code, resp.text[:500])
        return Response(
            {"error": {"code": "UPSTREAM_ERROR", "message": f"Kakao API returned {resp.status_code}", "detail": {}}},
            status=502,
        )

    data = resp.json()
    routes = data.get("routes", [])
    if not routes:
        return Response(
            {"error": {"code": "NO_ROUTE", "message": "No route found", "detail": {}}},
            status=404,
        )

    route = routes[0]
    result_code = route.get("result_code", 0)
    if result_code != 0:
        return Response(
            {"error": {
                "code": "ROUTE_ERROR",
                "message": route.get("result_msg", "Unknown error"),
                "detail": {"result_code": result_code},
            }},
            status=400,
        )

    summary = route.get("summary", {})
    polyline = _extract_polyline(route)
    sections = _extract_sections(route)

    return Response({
        "polyline": polyline,
        "total_distance_m": summary.get("distance", 0),
        "total_duration_sec": summary.get("duration", 0),
        "toll_fee": summary.get("fare", {}).get("toll", 0),
        "taxi_fee": summary.get("fare", {}).get("taxi", 0),
        "sections": sections,
        "origin": {"lng": origin[0], "lat": origin[1]},
        "destination": {"lng": destination[0], "lat": destination[1]},
    })
