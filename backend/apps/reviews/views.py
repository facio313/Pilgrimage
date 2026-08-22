from rest_framework import mixins, viewsets
from rest_framework.exceptions import ValidationError

from apps.users.permissions import IsPortfolioUserOrReadOnly

from .models import Review
from .serializers import ReviewSerializer


class ReviewViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = ReviewSerializer
    permission_classes = [IsPortfolioUserOrReadOnly]

    def get_queryset(self):
        qs = Review.objects.select_related("user", "spot").order_by("-rating", "-created_at")
        spot_id = self.request.query_params.get("spot_id")
        if self.action == "list":
            if not spot_id:
                raise ValidationError({"spot_id": "spot_id is required"})
            qs = qs.filter(spot_id=spot_id)
        return qs
