import uuid

from django.conf import settings
from django.db import models


class Route(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="routes",
    )
    title = models.CharField(max_length=200)
    theme_tags = models.JSONField(default=list, blank=True)
    transport_mode = models.CharField(max_length=50, blank=True, default="")
    total_distance_km = models.DecimalField(
        max_digits=8, decimal_places=2, default=0
    )
    total_estimated_cost = models.IntegerField(default=0)
    is_public = models.BooleanField(default=False)
    fork_from = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="forks",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "routes"

    def __str__(self):
        return self.title


class RouteSpot(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    route = models.ForeignKey(
        Route,
        on_delete=models.CASCADE,
        related_name="route_spots",
    )
    spot = models.ForeignKey(
        "spots.TouristSpot",
        on_delete=models.CASCADE,
        related_name="route_spots",
    )
    sequence_order = models.SmallIntegerField()
    segment_distance_km = models.DecimalField(
        max_digits=6, decimal_places=2, default=0
    )
    segment_cost = models.IntegerField(default=0)
    segment_duration_minutes = models.IntegerField(default=0)

    class Meta:
        db_table = "route_spots"
        constraints = [
            models.UniqueConstraint(
                fields=["route", "sequence_order"],
                name="unique_route_sequence",
            ),
        ]

    def __str__(self):
        return f"{self.route.title} - #{self.sequence_order}"


class RouteShare(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    route = models.ForeignKey(
        Route,
        on_delete=models.CASCADE,
        related_name="shares",
    )
    share_token = models.UUIDField(default=uuid.uuid4, unique=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "route_shares"
