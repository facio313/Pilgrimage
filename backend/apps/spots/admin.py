from django.contrib.gis import admin

from .models import TouristSpot


@admin.register(TouristSpot)
class TouristSpotAdmin(admin.GISModelAdmin):
    list_display = ("name", "external_id", "category", "address")
    search_fields = ("name", "external_id", "address")
