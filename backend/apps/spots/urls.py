from rest_framework.routers import DefaultRouter

from .views import SpotViewSet

router = DefaultRouter()
router.register("", SpotViewSet, basename="spot")

urlpatterns = router.urls
