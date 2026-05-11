from django.contrib import admin
from django.urls import include, path

from common.health import health_check
from common.places import place_nearby, place_reviews

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health_check),
    path("api/places/nearby/", place_nearby),
    path("api/places/reviews/", place_reviews),
    path("api/auth/", include("apps.users.urls")),
    path("api/spots/", include("apps.spots.urls")),
    path("api/reviews/", include("apps.reviews.urls")),
    path("api/", include("apps.visits.urls")),
    path("api/", include("apps.routes.urls")),
]
