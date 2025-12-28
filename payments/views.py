from rest_framework import permissions, viewsets

from .models import Payment
from .serializers import PaymentSerializer


class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if getattr(user, "is_provider", False):
            return Payment.objects.filter(provider=user).select_related("booking")
        return Payment.objects.filter(booking__client=user).select_related(
            "booking"
        )
