from datetime import timedelta

from django.contrib.gis.db.models.functions import Distance
from django.utils import timezone

from apps.spots.models import TouristSpot

from .models import GpsLog, VisitLog

GPS_CERT_RADIUS_M = 200
GPS_CERT_MIN_MINUTES = 30
GPS_CERT_GRACE_MINUTES = 10
GPS_LOG_INTERVAL_SEC = 30
SPOOF_MAX_KMH = 200


class CertificationError(Exception):
    pass


def _haversine_km(p1, p2) -> float:
    # Both points are GEOS Point in SRID 4326. Use PostGIS distance via DB if available;
    # but here we already have the geometry objects, fall back to spherical math.
    from math import asin, cos, radians, sin, sqrt

    lon1, lat1, lon2, lat2 = map(radians, [p1.x, p1.y, p2.x, p2.y])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 2 * 6371 * asin(sqrt(a))


def detect_spoof(prev_log: GpsLog, next_log: GpsLog) -> bool:
    seconds = (next_log.recorded_at - prev_log.recorded_at).total_seconds()
    if seconds <= 0:
        return False
    distance_km = _haversine_km(prev_log.location, next_log.location)
    speed_kmh = distance_km / (seconds / 3600)
    return speed_kmh > SPOOF_MAX_KMH


def certify_visit(user, spot: TouristSpot) -> VisitLog:
    """
    Inspect recent GPS logs and decide CERTIFIED / REJECTED for the given spot.

    Rule:
      - Within GPS_CERT_RADIUS_M of spot.location
      - Stayed at least GPS_CERT_MIN_MINUTES, allowing a single gap of
        up to GPS_CERT_GRACE_MINUTES outside the radius.
      - Reject if any consecutive pair of logs implies speed > SPOOF_MAX_KMH.
    """
    visit_log, _ = VisitLog.objects.get_or_create(user=user, spot=spot)

    if visit_log.status == VisitLog.Status.CERTIFIED:
        return visit_log

    window_start = timezone.now() - timedelta(hours=12)
    logs = list(
        GpsLog.objects.filter(user=user, recorded_at__gte=window_start)
        .order_by("recorded_at")
        .annotate(distance=Distance("location", spot.location))
    )

    if not logs:
        return visit_log

    for prev, nxt in zip(logs, logs[1:]):
        if detect_spoof(prev, nxt):
            visit_log.status = VisitLog.Status.REJECTED
            visit_log.save(update_fields=["status"])
            return visit_log

    stay_start = None
    stay_end = None
    cumulative_seconds = 0.0
    last_inside_at = None

    for log in logs:
        inside = log.distance.m <= GPS_CERT_RADIUS_M
        if inside:
            if stay_start is None:
                stay_start = log.recorded_at
            elif last_inside_at is not None:
                gap = (log.recorded_at - last_inside_at).total_seconds()
                if gap > GPS_CERT_GRACE_MINUTES * 60:
                    stay_start = log.recorded_at
                    cumulative_seconds = 0.0
                else:
                    cumulative_seconds += gap
            stay_end = log.recorded_at
            last_inside_at = log.recorded_at

    stay_minutes = int(cumulative_seconds // 60)

    if stay_minutes >= GPS_CERT_MIN_MINUTES:
        visit_log.status = VisitLog.Status.CERTIFIED
        visit_log.stay_start_at = stay_start
        visit_log.stay_end_at = stay_end
        visit_log.stay_minutes = stay_minutes
        visit_log.certified_at = timezone.now()
        visit_log.save(
            update_fields=[
                "status",
                "stay_start_at",
                "stay_end_at",
                "stay_minutes",
                "certified_at",
            ]
        )

    return visit_log
