from rest_framework import serializers

from apps.visits.models import VisitLog

from .models import Review


class ReviewSerializer(serializers.ModelSerializer):
    visit_log_id = serializers.PrimaryKeyRelatedField(
        queryset=VisitLog.objects.all(),
        source="visit_log",
        write_only=True,
    )
    user_nickname = serializers.CharField(source="user.nickname", read_only=True)

    class Meta:
        model = Review
        fields = (
            "id",
            "visit_log_id",
            "spot",
            "user",
            "user_nickname",
            "rating",
            "body",
            "entrance_fee",
            "food_cost",
            "other_cost",
            "photo_paths",
            "created_at",
        )
        read_only_fields = ("id", "spot", "user", "created_at")

    def validate(self, attrs):
        request = self.context["request"]
        visit_log = attrs["visit_log"]

        if visit_log.user_id != request.user.id:
            raise serializers.ValidationError(
                {"visit_log_id": "visit_log does not belong to current user"}
            )
        if visit_log.status != VisitLog.Status.CERTIFIED:
            raise serializers.ValidationError(
                {"visit_log_id": "review allowed only for CERTIFIED visit"}
            )
        if Review.objects.filter(visit_log=visit_log).exists():
            raise serializers.ValidationError(
                {"visit_log_id": "review already exists for this visit"}
            )

        photos = attrs.get("photo_paths") or []
        if len(photos) > 5:
            raise serializers.ValidationError(
                {"photo_paths": "up to 5 photos allowed"}
            )
        return attrs

    def create(self, validated_data):
        visit_log = validated_data["visit_log"]
        validated_data["user"] = self.context["request"].user
        validated_data["spot"] = visit_log.spot
        return super().create(validated_data)
