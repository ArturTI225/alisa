from django.db.models import Q
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.models import Notification, User
from accounts.utils import notify_user
from .models import Ad, Offer
from .serializers import AdSerializer, OfferSerializer


class AdViewSet(viewsets.ModelViewSet):
    serializer_class = AdSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        params = self.request.query_params
        qs = Ad.objects.select_related("client", "category", "assigned_craftsman")

        if getattr(user, "is_client", False):
            qs = qs.filter(client=user)
        elif getattr(user, "is_provider", False):
            mine = params.get("mine")
            if mine:
                qs = qs.filter(
                    Q(offers__craftsman=user)
                    | Q(assigned_craftsman=user)
                    | Q(client=user)
                ).distinct()
            else:
                qs = qs.filter(status=Ad.Status.OPEN)

        category = params.get("category") or params.get("category_id")
        if category:
            qs = qs.filter(category_id=category)
        city = params.get("city")
        if city:
            qs = qs.filter(city__iexact=city)
        is_urgent = params.get("is_urgent") or params.get("urgent")
        if is_urgent is not None:
            flag = str(is_urgent).lower() in ["1", "true", "yes", "y"]
            qs = qs.filter(is_urgent=flag)
        status_param = params.get("status")
        if status_param:
            qs = qs.filter(status=status_param)
        min_provider_rating = params.get("min_provider_rating")
        if min_provider_rating:
            qs = qs.filter(
                assigned_craftsman__rating_avg__gte=min_provider_rating
            )

        return qs.order_by("-is_urgent", "-created_at")

    def perform_create(self, serializer):
        if not getattr(self.request.user, "is_client", False):
            raise permissions.PermissionDenied("Doar clientii pot crea anunturi.")
        ad = serializer.save(client=self.request.user)
        if ad.is_urgent:
            recipients = User.objects.filter(
                role=User.Roles.PROVIDER,
                city__iexact=ad.city,
                provider_profile__skills__category=ad.category,
            ).distinct()
            for user in recipients:
                notify_user(
                    user=user,
                    notif_type=Notification.Type.URGENT_AD_NEARBY,
                    title="Anunt urgent in zona ta",
                    body=ad.title,
                    link=f"/ads/{ad.pk}/",
                )


class OfferViewSet(viewsets.ModelViewSet):
    serializer_class = OfferSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = Offer.objects.select_related("ad", "craftsman", "ad__client")
        if getattr(user, "is_provider", False):
            return qs.filter(craftsman=user)
        return qs.filter(ad__client=user)

    def perform_create(self, serializer):
        user = self.request.user
        if not getattr(user, "is_provider", False):
            raise permissions.PermissionDenied("Doar prestatorii pot trimite oferte.")
        ad = serializer.validated_data["ad"]
        if ad.status != Ad.Status.OPEN:
            raise permissions.PermissionDenied("Anuntul nu accepta oferte.")
        offer = serializer.save(craftsman=user)
        notify_user(
            user=ad.client,
            notif_type=Notification.Type.NEW_BID,
            title="Ai primit o oferta noua",
            body=offer.message[:140],
            link=f"/ads/{ad.pk}/",
        )

    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        offer = self.get_object()
        ad = offer.ad
        if ad.client != request.user:
            raise permissions.PermissionDenied("Doar clientul poate accepta oferta.")
        offer.status = Offer.Status.ACCEPTED
        offer.save(update_fields=["status"])
        ad.status = Ad.Status.IN_PROGRESS
        ad.assigned_craftsman = offer.craftsman
        ad.save(update_fields=["status", "assigned_craftsman", "updated_at"])
        notify_user(
            user=offer.craftsman,
            notif_type=Notification.Type.BID_ACCEPTED,
            title="Oferta acceptata",
            body=ad.title,
            link=f"/ads/{ad.pk}/",
        )
        return Response(
            OfferSerializer(offer, context=self.get_serializer_context()).data
        )

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        offer = self.get_object()
        ad = offer.ad
        if ad.client != request.user:
            raise permissions.PermissionDenied("Doar clientul poate respinge oferta.")
        offer.status = Offer.Status.REJECTED
        offer.save(update_fields=["status"])
        return Response(
            OfferSerializer(offer, context=self.get_serializer_context()).data
        )
