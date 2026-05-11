import uuid

from django.contrib.auth.models import AbstractUser
from django.contrib.gis.db import models as gis_models
from django.db import models


class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    nickname = models.CharField(max_length=50, blank=True, default="")
    home_location = gis_models.PointField(srid=4326, null=True, blank=True)
    preferred_themes = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = "users"
