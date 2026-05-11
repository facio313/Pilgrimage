from rest_framework import serializers

from .models import TouristSpot


class SpotListSerializer(serializers.ModelSerializer):
    lat = serializers.SerializerMethodField()
    lng = serializers.SerializerMethodField()

    class Meta:
        model = TouristSpot
        fields = (
            "id",
            "external_id",
            "name",
            "category",
            "theme_tags",
            "lat",
            "lng",
            "address",
            "avg_review_score",
        )

    def get_lat(self, obj):
        return obj.location.y if obj.location else None

    def get_lng(self, obj):
        return obj.location.x if obj.location else None


class SpotDetailSerializer(SpotListSerializer):
    class Meta(SpotListSerializer.Meta):
        fields = SpotListSerializer.Meta.fields + (
            "operating_hours",
            "entrance_fee",
            "avg_cost",
            "avg_stay_minutes",
            "synced_at",
        )
