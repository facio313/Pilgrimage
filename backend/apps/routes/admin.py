from django.contrib import admin

from .models import Route, RouteShare, RouteSpot


class RouteSpotInline(admin.TabularInline):
    model = RouteSpot
    extra = 0


@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = ("title", "creator", "is_public", "created_at")
    inlines = [RouteSpotInline]


@admin.register(RouteShare)
class RouteShareAdmin(admin.ModelAdmin):
    list_display = ("route", "share_token", "expires_at")
