import uuid

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Review(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    visit_log = models.OneToOneField(
        "visits.VisitLog",
        on_delete=models.CASCADE,
        related_name="review",
    )
    spot = models.ForeignKey(
        "spots.TouristSpot",
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    rating = models.SmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    body = models.TextField(blank=True, default="")
    entrance_fee = models.IntegerField(default=0)
    food_cost = models.IntegerField(default=0)
    other_cost = models.IntegerField(default=0)
    photo_paths = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "reviews"

    def __str__(self):
        return f"{self.user} - {self.spot} ({self.rating})"
