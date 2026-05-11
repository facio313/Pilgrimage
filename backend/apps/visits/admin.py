from django.contrib import admin

from .models import GpsLog, VisitLog


@admin.register(VisitLog)
class VisitLogAdmin(admin.ModelAdmin):
    list_display = ("user", "spot", "status", "stay_minutes", "certified_at")
    list_filter = ("status",)


@admin.register(GpsLog)
class GpsLogAdmin(admin.ModelAdmin):
    list_display = ("user", "recorded_at")
