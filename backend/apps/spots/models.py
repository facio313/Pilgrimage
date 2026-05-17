import uuid

from django.contrib.gis.db import models as gis_models
from django.db import models


class GooglePlaceCache(models.Model):
    lookup_key = models.CharField(max_length=100, unique=True, db_index=True)
    place_id = models.CharField(max_length=200, blank=True, db_index=True)
    name = models.CharField(max_length=300, blank=True)
    address = models.CharField(max_length=500, blank=True)
    rating = models.FloatField(null=True, blank=True)
    user_rating_count = models.IntegerField(null=True, blank=True)
    photo_url = models.TextField(blank=True)
    google_maps_uri = models.TextField(blank=True)
    reviews = models.JSONField(default=list)
    reviews_fetched = models.BooleanField(default=False)
    cached_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "google_place_cache"


class TouristSpot(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    external_id = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=100, blank=True, default="")
    theme_tags = models.JSONField(default=list, blank=True)
    location = gis_models.PointField(srid=4326)
    operating_hours = models.JSONField(default=dict, blank=True)
    entrance_fee = models.IntegerField(default=0)
    address = models.CharField(max_length=300, blank=True, default="")
    avg_review_score = models.DecimalField(
        max_digits=3, decimal_places=2, default=0
    )
    avg_cost = models.IntegerField(default=0)
    avg_stay_minutes = models.IntegerField(default=0)
    synced_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "tourist_spots"

    def __str__(self):
        return self.name
