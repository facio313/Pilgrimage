import math

from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from common.themes import THEME_CHOICES

from .models import TouristSpot
from .serializers import SpotDetailSerializer, SpotListSerializer

VALID_THEME_KEYS = {key for key, _ in THEME_CHOICES}

DIRECTIONS = [0, 45, 90, 135, 180, 225, 270, 315]
SEARCH_DISTANCE_M = 1500
SEARCH_BUFFER_M = 1500
EXCLUDE_CENTER_M = 50


def _destination_point(lat, lng, bearing_deg, distance_m):
    R = 6_371_000
    d = distance_m / R
    brng = math.radians(bearing_deg)
    lat1 = math.radians(lat)
    lng1 = math.radians(lng)
    lat2 = math.asin(
        math.sin(lat1) * math.cos(d)
        + math.cos(lat1) * math.sin(d) * math.cos(brng)
    )
    lng2 = lng1 + math.atan2(
        math.sin(brng) * math.sin(d) * math.cos(lat1),
        math.cos(d) - math.sin(lat1) * math.sin(lat2),
    )
    return math.degrees(lat2), math.degrees(lng2)


def _calc_bearing(lat1, lng1, lat2, lng2):
    lat1, lng1, lat2, lng2 = map(math.radians, [lat1, lng1, lat2, lng2])
    dlng = lng2 - lng1
    x = math.sin(dlng) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(
        lat2
    ) * math.cos(dlng)
    return (math.degrees(math.atan2(x, y)) + 360) % 360


def _haversine(lat1, lng1, lat2, lng2):
    R = 6_371_000
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlng / 2) ** 2
    )
    return 2 * R * math.asin(math.sqrt(a))


class SpotViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = TouristSpot.objects.all()
    permission_classes = [AllowAny]

    def get_permissions(self):
        if self.action == 'create':
            return [IsAuthenticated()]
        return [AllowAny()]

    def create(self, request):
        name = (request.data.get('name') or '').strip()
        address = (request.data.get('address') or '').strip()
        category = (request.data.get('category') or '').strip()
        external_id = (request.data.get('external_id') or '').strip()
        try:
            lat = float(request.data['lat'])
            lng = float(request.data['lng'])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValidationError({'lat': 'lat and lng are required'}) from exc
        if not name:
            raise ValidationError({'name': 'name is required'})
        if not external_id:
            external_id = f'kakao:{lat:.6f}:{lng:.6f}'
        spot, _ = TouristSpot.objects.get_or_create(
            external_id=external_id,
            defaults={
                'name': name,
                'location': Point(float(lng), float(lat), srid=4326),
                'address': address,
                'category': category,
                'theme_tags': [],
            },
        )
        return Response(SpotListSerializer(spot).data, status=status.HTTP_200_OK)

    def get_serializer_class(self):
        if self.action == "retrieve":
            return SpotDetailSerializer
        return SpotListSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params

        theme = params.get("theme")
        if theme:
            if theme not in VALID_THEME_KEYS:
                raise ValidationError({"theme": f"unknown theme: {theme}"})
            qs = qs.filter(theme_tags__contains=[theme])

        lat = params.get("lat")
        lng = params.get("lng")
        radius = params.get("radius")
        if lat or lng or radius:
            if not (lat and lng and radius):
                raise ValidationError(
                    {"radius": "lat, lng, radius must be provided together"}
                )
            try:
                center = Point(float(lng), float(lat), srid=4326)
                radius_m = float(radius)
            except ValueError as exc:
                raise ValidationError({"radius": "invalid numeric values"}) from exc
            qs = qs.filter(location__distance_lte=(center, D(m=radius_m)))

        return qs

    @action(detail=False, methods=["get"], url_path="nearby-recommend")
    def nearby_recommend(self, request):
        lat_str = request.query_params.get("lat")
        lng_str = request.query_params.get("lng")
        theme = request.query_params.get("theme")

        if not lat_str or not lng_str:
            raise ValidationError({"lat": "lat and lng are required"})
        try:
            center_lat = float(lat_str)
            center_lng = float(lng_str)
        except ValueError as exc:
            raise ValidationError({"lat": "invalid numeric values"}) from exc

        if theme and theme not in VALID_THEME_KEYS:
            theme = None

        center_point = Point(center_lng, center_lat, srid=4326)
        picked_ids = []
        results = []

        for bearing in DIRECTIONS:
            dir_lat, dir_lng = _destination_point(
                center_lat, center_lng, bearing, SEARCH_DISTANCE_M
            )
            dir_point = Point(dir_lng, dir_lat, srid=4326)

            qs = TouristSpot.objects.filter(
                location__distance_lte=(dir_point, D(m=SEARCH_BUFFER_M))
            ).exclude(location__distance_lte=(center_point, D(m=EXCLUDE_CENTER_M)))

            if picked_ids:
                qs = qs.exclude(id__in=picked_ids)

            if theme:
                themed = qs.filter(theme_tags__contains=[theme])
                spot = themed.order_by("-avg_review_score").first()
                if not spot:
                    spot = qs.order_by("-avg_review_score").first()
            else:
                spot = qs.order_by("-avg_review_score").first()

            if not spot:
                continue

            picked_ids.append(spot.id)
            data = SpotListSerializer(spot).data
            data["bearing"] = _calc_bearing(
                center_lat, center_lng, spot.location.y, spot.location.x
            )
            data["distance_m"] = round(
                _haversine(
                    center_lat, center_lng, spot.location.y, spot.location.x
                )
            )
            results.append(data)

        return Response(results)
