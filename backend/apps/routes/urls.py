from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import RouteViewSet, SharedRouteView

router = DefaultRouter()
router.register("routes", RouteViewSet, basename="route")

urlpatterns = router.urls + [
    path(
        "shared/<uuid:share_token>/",
        SharedRouteView.as_view(),
        name="route-shared",
    ),
]
