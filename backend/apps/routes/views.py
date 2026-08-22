from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.users.permissions import IsPortfolioUser

from .models import Route, RouteShare, RouteSpot
from .serializers import RouteSerializer, RouteShareSerializer
from .services import auto_recommend_route


class RouteViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Route.objects.all()
    serializer_class = RouteSerializer
    permission_classes = [IsPortfolioUser]

    def get_object(self):
        route = super().get_object()
        if route.creator_id != self.request.user.id and not route.is_public:
            raise PermissionDenied("not allowed")
        return route

    @action(detail=False, methods=["post"], url_path="auto")
    def auto(self, request):
        try:
            route = auto_recommend_route(request.user, request.data)
        except ValueError as exc:
            raise ValidationError({"detail": str(exc)}) from exc
        serializer = self.get_serializer(route)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="share")
    def share(self, request, pk=None):
        route = self.get_object()
        if route.creator_id != request.user.id:
            raise PermissionDenied("only creator can share")
        share = RouteShare.objects.create(route=route)
        return Response(
            RouteShareSerializer(share).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="fork")
    def fork(self, request, pk=None):
        original = self.get_object()
        forked = Route.objects.create(
            creator=request.user,
            title=f"{original.title} (fork)",
            theme_tags=original.theme_tags,
            transport_mode=original.transport_mode,
            total_distance_km=original.total_distance_km,
            total_estimated_cost=original.total_estimated_cost,
            is_public=False,
            fork_from=original,
        )
        RouteSpot.objects.bulk_create([
            RouteSpot(
                route=forked,
                spot=rs.spot,
                sequence_order=rs.sequence_order,
                segment_distance_km=rs.segment_distance_km,
                segment_cost=rs.segment_cost,
                segment_duration_minutes=rs.segment_duration_minutes,
            )
            for rs in original.route_spots.all()
        ])
        serializer = self.get_serializer(forked)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class SharedRouteView(RetrieveAPIView):
    authentication_classes = []
    serializer_class = RouteSerializer
    permission_classes = [AllowAny]
    lookup_field = "share_token"

    def get_object(self):
        token = self.kwargs[self.lookup_field]
        share = get_object_or_404(
            RouteShare.objects.filter(Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())),
            share_token=token,
        )
        return share.route
