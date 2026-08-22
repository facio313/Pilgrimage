import uuid

from django.contrib.auth.models import AbstractUser
from django.contrib.gis.db import models as gis_models
from django.core.exceptions import ValidationError
from django.db import models


class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    email_verified = models.BooleanField(default=False)
    sso_link_allowed = models.BooleanField(default=False)
    sso_subject = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        unique=True,
        editable=False,
    )
    nickname = models.CharField(max_length=50, blank=True, default="")
    home_location = gis_models.PointField(srid=4326, null=True, blank=True)
    preferred_themes = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = "users"

    @property
    def ownership_subject(self):
        """Central subject projected through existing domain ownership FKs."""

        return self.sso_subject

    def save(self, *args, **kwargs):
        if not self._state.adding and self.pk:
            previous_subject = type(self).objects.filter(pk=self.pk).values_list("sso_subject", flat=True).first()
            if previous_subject is not None and previous_subject != self.sso_subject:
                raise ValidationError({"sso_subject": "An established SSO subject is immutable."})
        return super().save(*args, **kwargs)
