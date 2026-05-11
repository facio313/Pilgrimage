from dataclasses import dataclass
from math import asin, cos, radians, sin, sqrt

from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D

from apps.spots.models import TouristSpot

from .models import Route, RouteSpot

TRANSPORT_COST_PER_KM = {
    "car": 1700 / 12,  # KRW per km, fuel only
    "bus": 100,
    "train": 100,
    "walking": 0,
    "bicycle": 0,
    "mixed": 100,
}

DEFAULT_AVG_SPEED_KMH = {
    "car": 50,
    "bus": 30,
    "train": 60,
    "walking": 4,
    "bicycle": 15,
    "mixed": 30,
}


def haversine_km(lng1, lat1, lng2, lat2) -> float:
    lon1, la1, lon2, la2 = map(radians, [lng1, lat1, lng2, lat2])
    dlon = lon2 - lon1
    dlat = la2 - la1
    a = sin(dlat / 2) ** 2 + cos(la1) * cos(la2) * sin(dlon / 2) ** 2
    return 2 * 6371 * asin(sqrt(a))


def order_by_nearest_neighbor(spot_ids: list, start_lng=None, start_lat=None) -> list:
    """
    F02 — Nearest-neighbor TSP approximation.
    Returns spot ids reordered by NN traversal.
    """
    spots = {
        s.id: s for s in TouristSpot.objects.filter(id__in=spot_ids)
    }
    remaining = [spots[sid] for sid in spot_ids if sid in spots]
    if not remaining:
        return []

    if start_lng is None or start_lat is None:
        current = remaining.pop(0)
    else:
        current = min(
            remaining,
            key=lambda s: haversine_km(start_lng, start_lat, s.location.x, s.location.y),
        )
        remaining.remove(current)

    ordered = [current]
    while remaining:
        nxt = min(
            remaining,
            key=lambda s: haversine_km(
                ordered[-1].location.x, ordered[-1].location.y,
                s.location.x, s.location.y,
            ),
        )
        remaining.remove(nxt)
        ordered.append(nxt)
    return [s.id for s in ordered]


def estimate_route_metrics(spots, transport_mode: str):
    """
    Compute total distance, total cost, per-segment distance/cost/duration.
    `spots` is an ordered iterable of TouristSpot.
    Returns (total_distance_km, total_cost, segments[]).
    """
    cost_per_km = TRANSPORT_COST_PER_KM.get(transport_mode, 100)
    speed_kmh = DEFAULT_AVG_SPEED_KMH.get(transport_mode, 30)

    total_distance = 0.0
    total_cost = 0
    segments = []

    prev = None
    for spot in spots:
        if prev is None:
            segments.append({
                "spot_id": spot.id,
                "segment_distance_km": 0.0,
                "segment_cost": 0,
                "segment_duration_minutes": 0,
            })
        else:
            d = haversine_km(
                prev.location.x, prev.location.y,
                spot.location.x, spot.location.y,
            )
            seg_cost = int(d * cost_per_km)
            seg_minutes = int((d / speed_kmh) * 60) if speed_kmh else 0
            segments.append({
                "spot_id": spot.id,
                "segment_distance_km": round(d, 2),
                "segment_cost": seg_cost,
                "segment_duration_minutes": seg_minutes,
            })
            total_distance += d
            total_cost += seg_cost + (spot.entrance_fee or 0)
        prev = spot

    return round(total_distance, 2), total_cost, segments


@dataclass(frozen=True)
class ThemeWeights:
    review: float
    cost: float
    distance: float
    congestion: float


THEME_WEIGHTS: dict[str, ThemeWeights] = {
    "mixed":    ThemeWeights(review=0.40, cost=0.20, distance=0.20, congestion=0.20),
    "nature":   ThemeWeights(review=0.50, cost=0.10, distance=0.30, congestion=0.10),
    "heritage": ThemeWeights(review=0.50, cost=0.15, distance=0.25, congestion=0.10),
    "urban":    ThemeWeights(review=0.30, cost=0.30, distance=0.20, congestion=0.20),
    "festival": ThemeWeights(review=0.40, cost=0.15, distance=0.15, congestion=0.30),
    "leisure":  ThemeWeights(review=0.40, cost=0.20, distance=0.30, congestion=0.10),
    "shopping": ThemeWeights(review=0.30, cost=0.30, distance=0.30, congestion=0.10),
    "food":     ThemeWeights(review=0.40, cost=0.20, distance=0.30, congestion=0.10),
    "camping":  ThemeWeights(review=0.40, cost=0.20, distance=0.30, congestion=0.10),
    "medical":  ThemeWeights(review=0.50, cost=0.20, distance=0.20, congestion=0.10),
    "family":   ThemeWeights(review=0.50, cost=0.15, distance=0.25, congestion=0.10),
}

# Seoul City Hall — fallback origin when user has no home_location set
DEFAULT_ORIGIN = (126.9783882, 37.5666103)


def _spot_origin_distance_km(spot: TouristSpot, origin_lng: float, origin_lat: float) -> float:
    return haversine_km(origin_lng, origin_lat, spot.location.x, spot.location.y)


def _score_spot(
    spot: TouristSpot,
    origin_lng: float,
    origin_lat: float,
    weights: ThemeWeights,
) -> float:
    """
    score = w1·review_score + w2·(1/cost) + w3·(1/distance) + w4·congestion_penalty

    - cost is entrance_fee + avg_cost (KRW). 1/cost is normalized per 10,000 KRW.
    - distance is from origin in km.
    - congestion data is unavailable until KTO sync covers it; treat as 0.
    """
    rating = float(spot.avg_review_score or 0)
    cost = max(int(spot.entrance_fee or 0) + int(spot.avg_cost or 0), 1)
    distance_km = max(_spot_origin_distance_km(spot, origin_lng, origin_lat), 0.1)

    return (
        weights.review * rating
        + weights.cost * (10_000 / cost)
        + weights.distance * (1 / distance_km)
        + weights.congestion * 0.0
    )


def auto_recommend_route(user, params: dict) -> Route:
    """
    F03 — Auto route recommendation.

    params keys:
      theme (required), n_spots, budget_max, min_rating, max_distance_km, transport_mode
    """
    theme = params.get("theme")
    if not theme or theme not in THEME_WEIGHTS:
        raise ValueError(f"unknown or missing theme: {theme!r}")

    n_spots = int(params.get("n_spots") or 5)
    budget_max = int(params.get("budget_max") or 0)
    min_rating = float(params.get("min_rating") or 0)
    max_distance_km = float(params.get("max_distance_km") or 100)
    transport_mode = str(params.get("transport_mode") or "mixed")

    if n_spots < 1:
        raise ValueError("n_spots must be >= 1")

    weights = THEME_WEIGHTS[theme]

    home = getattr(user, "home_location", None)
    if home is not None:
        origin_lng, origin_lat = home.x, home.y
    else:
        origin_lng, origin_lat = DEFAULT_ORIGIN

    origin = Point(origin_lng, origin_lat, srid=4326)
    candidates = list(
        TouristSpot.objects.filter(
            theme_tags__contains=[theme],
            avg_review_score__gte=min_rating,
            location__distance_lte=(origin, D(km=max_distance_km)),
        )
    )

    if not candidates:
        raise ValueError("no spots match the criteria")

    scored = sorted(
        candidates,
        key=lambda s: _score_spot(s, origin_lng, origin_lat, weights),
        reverse=True,
    )

    current_n = min(n_spots, len(scored))
    final_spots: list[TouristSpot] = []
    final_segments: list[dict] = []
    total_distance = 0.0
    total_cost = 0

    while current_n >= 1:
        top = scored[:current_n]
        ordered_ids = order_by_nearest_neighbor(
            [s.id for s in top],
            start_lng=origin_lng,
            start_lat=origin_lat,
        )
        spots_by_id = {s.id: s for s in top}
        ordered = [spots_by_id[sid] for sid in ordered_ids]
        total_distance, total_cost, segments = estimate_route_metrics(ordered, transport_mode)
        if budget_max == 0 or total_cost <= budget_max:
            final_spots = ordered
            final_segments = segments
            break
        current_n -= 1

    if not final_spots:
        raise ValueError("budget too low for any candidate")

    route = Route.objects.create(
        creator=user,
        title=f"자동 추천 ({theme})",
        theme_tags=[theme],
        transport_mode=transport_mode,
        total_distance_km=total_distance,
        total_estimated_cost=total_cost,
        is_public=False,
    )
    RouteSpot.objects.bulk_create([
        RouteSpot(
            route=route,
            spot_id=seg["spot_id"],
            sequence_order=idx,
            segment_distance_km=seg["segment_distance_km"],
            segment_cost=seg["segment_cost"],
            segment_duration_minutes=seg["segment_duration_minutes"],
        )
        for idx, seg in enumerate(final_segments)
    ])
    return route
