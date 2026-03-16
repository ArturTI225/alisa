from rest_framework import serializers

from accounts.serializers import UserSerializer
from .models import Review
from bookings.models import HelpRequest


class ReviewSerializer(serializers.ModelSerializer):
    from_user = UserSerializer(read_only=True)
    to_user = UserSerializer(read_only=True)
    to_user_id = serializers.PrimaryKeyRelatedField(
        source="to_user",
        queryset=UserSerializer.Meta.model.objects.all(),
        write_only=True,
    )
    help_request = serializers.PrimaryKeyRelatedField(read_only=True)
    help_request_id = serializers.PrimaryKeyRelatedField(
        source="help_request",
        queryset=HelpRequest.objects.all(),
        required=False,
        allow_null=True,
        write_only=True,
    )

    class Meta:
        model = Review
        fields = [
            "id",
            "from_user",
            "to_user",
            "to_user_id",
            "booking",
            "ad",
            "help_request",
            "help_request_id",
            "rating",
            "comment",
            "photo",
            "created_at",
        ]
        read_only_fields = ["id", "from_user", "to_user", "help_request", "created_at"]

    def validate(self, attrs):
        request_user = self.context["request"].user
        to_user = attrs.get("to_user")
        if to_user == request_user:
            raise serializers.ValidationError("Nu poți lăsa review pentru tine.")
        booking = attrs.get("booking")
        ad = attrs.get("ad")
        help_request = attrs.get("help_request")
        provided = [bool(booking), bool(ad), bool(help_request)]
        if sum(provided) != 1:
            raise serializers.ValidationError("Leagă review-ul de exact o entitate: booking, help request sau anunt.")

        if booking:
            from bookings.models import Booking  # local import

            if booking.status not in [Booking.Status.COMPLETED, Booking.Status.AWAITING_CLIENT]:
                raise serializers.ValidationError("Review permis doar dupa finalizare.")
            if request_user not in [booking.client, booking.provider]:
                raise serializers.ValidationError("Nu ai participat la acest booking.")
            other = booking.provider if request_user == booking.client else booking.client
            if to_user != other:
                raise serializers.ValidationError("Review trebuie sa fie pentru cealalta parte.")
        if ad:
            from ads.models import Ad  # local import

            if ad.status not in [Ad.Status.IN_PROGRESS, Ad.Status.COMPLETED]:
                raise serializers.ValidationError("Review permis doar dupa inceperea lucrarii.")
            participants = [ad.client, ad.assigned_craftsman]
            if request_user not in participants:
                raise serializers.ValidationError("Nu ai participat la acest anunt.")
            other = ad.assigned_craftsman if request_user == ad.client else ad.client
            if not other:
                raise serializers.ValidationError("Nu exista inca un prestator asignat.")
            if to_user != other:
                raise serializers.ValidationError("Review trebuie sa fie pentru cealalta parte.")
        if help_request:
            if help_request.status != HelpRequest.Status.DONE:
                raise serializers.ValidationError("Review permis doar dupa finalizare.")
            participants = [help_request.created_by, help_request.matched_volunteer]
            if request_user not in participants:
                raise serializers.ValidationError("Nu ai participat la aceasta cerere.")
            other = (
                help_request.matched_volunteer
                if request_user == help_request.created_by
                else help_request.created_by
            )
            if not other:
                raise serializers.ValidationError("Nu exista voluntar asignat pentru aceasta cerere.")
            if to_user != other:
                raise serializers.ValidationError("Review trebuie sa fie pentru cealalta parte.")

        return attrs
