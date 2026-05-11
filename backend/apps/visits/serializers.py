from django.contrib.gis.geos import Point
from rest_framework import serializers

from .models import GpsLog, VisitLog


class GpsLogSerializer(serializers.ModelSerializer):
    lat = serializers.FloatField(write_only=True)
    lng = serializers.FloatField(write_only=True)

    class Meta:
        model = GpsLog
        fields = ("id", "lat", "lng", "recorded_at")
        read_only_fields = ("id",)

    def create(self, validated_data):
        lat = validated_data.pop("lat")
        lng = validated_data.pop("lng")
        validated_data["location"] = Point(lng, lat, srid=4326)
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)


class VisitLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = VisitLog
        fields = (
            "id",
            "spot",
            "status",
            "stay_start_at",
            "stay_end_at",
            "stay_minutes",
            "certified_at",
        )
        read_only_fields = fields
