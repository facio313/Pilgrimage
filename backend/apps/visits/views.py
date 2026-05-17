from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.spots.models import TouristSpot

from .models import VisitLog
from .serializers import GpsLogSerializer, VisitLogSerializer
from .services import certify_visit


class GpsLogCreateView(generics.CreateAPIView):
    serializer_class = GpsLogSerializer
    permission_classes = [IsAuthenticated]


class CertifyVisitView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, spot_id):
        spot = get_object_or_404(TouristSpot, pk=spot_id)
        visit_log = certify_visit(request.user, spot)
        serializer = VisitLogSerializer(visit_log)
        return Response(serializer.data, status=status.HTTP_200_OK)


class VisitStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, spot_id):
        certified = VisitLog.objects.filter(
            user=request.user,
            spot_id=spot_id,
            status="CERTIFIED",
        ).exists()
        return Response({"certified": certified})
