import uuid

from django.conf import settings
from django.contrib.gis.db import models as gis_models
from django.db import models


class VisitLog(models.Model):
    class Status(models.TextChoices):
        UNVISITED = "UNVISITED", "미방문"
        CERTIFIED = "CERTIFIED", "인증완료"
        REJECTED = "REJECTED", "거부"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="visit_logs",
    )
    spot = models.ForeignKey(
        "spots.TouristSpot",
        on_delete=models.CASCADE,
        related_name="visit_logs",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.UNVISITED,
    )
    stay_start_at = models.DateTimeField(null=True, blank=True)
    stay_end_at = models.DateTimeField(null=True, blank=True)
    stay_minutes = models.IntegerField(default=0)
    certified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "visit_logs"

    def __str__(self):
        return f"{self.user} - {self.spot} ({self.status})"


class GpsLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="gps_logs",
    )
    location = gis_models.PointField(srid=4326)
    recorded_at = models.DateTimeField()

    class Meta:
        db_table = "gps_logs"
        indexes = [
            models.Index(
                fields=["user", "recorded_at"],
                name="idx_gpslog_user_recorded",
            ),
        ]
