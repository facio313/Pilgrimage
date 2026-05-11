from rest_framework import serializers

from apps.spots.models import TouristSpot
from apps.spots.serializers import SpotListSerializer

from .models import Route, RouteShare, RouteSpot
from .services import estimate_route_metrics, order_by_nearest_neighbor


class RouteSpotReadSerializer(serializers.ModelSerializer):
    spot = SpotListSerializer(read_only=True)

    class Meta:
        model = RouteSpot
        fields = (
            "spot",
            "sequence_order",
            "segment_distance_km",
            "segment_cost",
            "segment_duration_minutes",
        )


class RouteSerializer(serializers.ModelSerializer):
    route_spots = RouteSpotReadSerializer(many=True, read_only=True)
    spot_ids = serializers.ListField(
        child=serializers.UUIDField(), write_only=True, allow_empty=False,
    )

    class Meta:
        model = Route
        fields = (
            "id",
            "creator",
            "title",
            "theme_tags",
            "transport_mode",
            "total_distance_km",
            "total_estimated_cost",
            "is_public",
            "fork_from",
            "created_at",
            "updated_at",
            "route_spots",
            "spot_ids",
        )
        read_only_fields = (
            "id",
            "creator",
            "total_distance_km",
            "total_estimated_cost",
            "fork_from",
            "created_at",
            "updated_at",
        )

    def create(self, validated_data):
        spot_ids = validated_data.pop("spot_ids")
        ordered_ids = order_by_nearest_neighbor(spot_ids)
        spots_by_id = {
            s.id: s for s in TouristSpot.objects.filter(id__in=ordered_ids)
        }
        ordered_spots = [spots_by_id[sid] for sid in ordered_ids]

        total_distance, total_cost, segments = estimate_route_metrics(
            ordered_spots, validated_data.get("transport_mode", "")
        )

        validated_data["creator"] = self.context["request"].user
        validated_data["total_distance_km"] = total_distance
        validated_data["total_estimated_cost"] = total_cost
        route = Route.objects.create(**validated_data)

        RouteSpot.objects.bulk_create([
            RouteSpot(
                route=route,
                spot_id=seg["spot_id"],
                sequence_order=idx,
                segment_distance_km=seg["segment_distance_km"],
                segment_cost=seg["segment_cost"],
                segment_duration_minutes=seg["segment_duration_minutes"],
            )
            for idx, seg in enumerate(segments)
        ])
        return route


class RouteShareSerializer(serializers.ModelSerializer):
    class Meta:
        model = RouteShare
        fields = ("id", "route", "share_token", "expires_at")
        read_only_fields = ("id", "share_token")
