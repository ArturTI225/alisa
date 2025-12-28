from rest_framework import permissions, viewsets
from django.db.models import Q

from accounts.utils import notify_user
from accounts.models import Notification
from .models import Review
from .serializers import ReviewSerializer


class ReviewViewSet(viewsets.ModelViewSet):
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        target = self.request.query_params.get("user")
        qs = Review.objects.select_related(
            "from_user", "to_user", "ad", "booking"
        )
        if target:
            return qs.filter(to_user_id=target)
        return qs.filter(Q(from_user=user) | Q(to_user=user))

    def perform_create(self, serializer):
        review = serializer.save(from_user=self.request.user)
        notify_user(
            user=review.to_user,
            notif_type=Notification.Type.REVIEW,
            title="Ai primit o recenzie",
            body=review.comment[:140],
            link="",
        )
