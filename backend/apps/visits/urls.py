from django.urls import path

from .views import CertifyVisitView, GpsLogCreateView, VisitStatusView

urlpatterns = [
    path("gps/log/", GpsLogCreateView.as_view(), name="gps-log"),
    path("visits/<uuid:spot_id>/certify/", CertifyVisitView.as_view(), name="visit-certify"),
    path("visits/<uuid:spot_id>/status/", VisitStatusView.as_view(), name="visit-status"),
]
