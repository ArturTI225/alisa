from django.utils import timezone
from rest_framework import serializers

from accounts.models import Address
from accounts.serializers import AddressSerializer, UserSerializer
from services.models import Service
from services.serializers import ServiceSerializer
from .models import (
    Booking,
    BookingDispute,
    BookingEvent,
    BookingAttachment,
    DisputeMessage,
    RecurringBookingRule,
    RescheduleRequest,
)


class BookingEventSerializer(serializers.ModelSerializer):
    actor = UserSerializer(read_only=True)

    class Meta:
        model = BookingEvent
        fields = ["id", "event_type", "message", "payload", "actor", "created_at"]
        read_only_fields = fields


class BookingAttachmentSerializer(serializers.ModelSerializer):
    uploaded_by = UserSerializer(read_only=True)

    class Meta:
        model = BookingAttachment
        fields = ["id", "file", "note", "uploaded_by", "created_at"]
        read_only_fields = ["id", "uploaded_by", "created_at"]


class BookingDisputeSerializer(serializers.ModelSerializer):
    opened_by = UserSerializer(read_only=True)
    resolved_by = UserSerializer(read_only=True)
    messages = serializers.SerializerMethodField()
    assigned_to = UserSerializer(read_only=True)

    class Meta:
        model = BookingDispute
        fields = [
            "id",
            "status",
            "reason",
            "resolution_note",
            "opened_by",
            "assigned_to",
            "resolved_by",
            "created_at",
            "resolved_at",
            "messages",
            "escalated_at",
        ]
        read_only_fields = fields

    def get_messages(self, obj):
        qs = obj.messages.select_related("author")
        return DisputeMessageSerializer(qs, many=True).data


class DisputeMessageSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)

    class Meta:
        model = DisputeMessage
        fields = ["id", "author", "text", "attachment", "created_at"]
        read_only_fields = ["id", "author", "created_at"]


class RescheduleRequestSerializer(serializers.ModelSerializer):
    requested_by = UserSerializer(read_only=True)
    responded_by = UserSerializer(read_only=True)

    class Meta:
        model = RescheduleRequest
        fields = [
            "id",
            "status",
            "proposed_start",
            "proposed_duration_minutes",
            "note",
            "requested_by",
            "responded_by",
            "created_at",
            "responded_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "requested_by",
            "responded_by",
            "created_at",
            "responded_at",
        ]


class BookingSerializer(serializers.ModelSerializer):
    client = UserSerializer(read_only=True)
    provider = UserSerializer(read_only=True)
    accepted_by = UserSerializer(read_only=True)
    service = ServiceSerializer(read_only=True)
    service_id = serializers.PrimaryKeyRelatedField(
        queryset=Service.objects.filter(is_active=True),
        source="service",
        write_only=True,
    )
    address = AddressSerializer(read_only=True)
    address_id = serializers.PrimaryKeyRelatedField(
        queryset=Address.objects.all(),
        source="address",
        write_only=True,
    )
    canceled_by = UserSerializer(read_only=True)
    reschedule_requests = RescheduleRequestSerializer(many=True, read_only=True)
    events = BookingEventSerializer(many=True, read_only=True)
    dispute = BookingDisputeSerializer(read_only=True)
    attachments = BookingAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = Booking
        fields = [
            "id",
            "client",
            "provider",
            "service",
            "service_id",
            "address",
            "address_id",
            "description",
            "is_urgent",
            "urgency_level",
            "scheduled_start",
            "duration_minutes",
            "price_estimated",
            "price_final",
            "started_at",
            "completed_at",
            "client_confirmed_at",
            "client_confirmation_note",
            "status",
            "payment_status",
            "created_at",
            "accepted_at",
            "accepted_by",
            "cancel_reason",
            "canceled_at",
            "canceled_by",
            "reschedule_requests",
            "dispute",
            "attachments",
            "events",
        ]
        read_only_fields = [
            "id",
            "client",
            "provider",
            "status",
            "payment_status",
            "created_at",
            "accepted_at",
            "accepted_by",
            "started_at",
            "completed_at",
            "client_confirmed_at",
            "client_confirmation_note",
            "cancel_reason",
            "canceled_at",
            "canceled_by",
            "reschedule_requests",
            "dispute",
            "attachments",
            "events",
        ]

    def create(self, validated_data):
        validated_data["client"] = self.context["request"].user
        return super().create(validated_data)


class BookingCancelSerializer(serializers.Serializer):
    reason = serializers.CharField(
        required=False, allow_blank=True, max_length=255
    )

class BookingCompleteSerializer(serializers.Serializer):
    price_final = serializers.DecimalField(
        max_digits=8, decimal_places=2, required=True
    )
    extra_costs = serializers.JSONField(required=False)
    note = serializers.CharField(
        required=False, allow_blank=True, max_length=255
    )


class ClientConfirmationSerializer(serializers.Serializer):
    note = serializers.CharField(
        required=False, allow_blank=True, max_length=255
    )


class DisputeMessageCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DisputeMessage
        fields = ["text", "attachment"]


class BookingRepeatSerializer(serializers.Serializer):
    scheduled_start = serializers.DateTimeField(required=False)
    duration_minutes = serializers.IntegerField(required=False, min_value=15)


class RecurringRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecurringBookingRule
        fields = [
            "id",
            "service",
            "address",
            "description",
            "start_date",
            "start_time",
            "duration_minutes",
            "frequency",
            "occurrences",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["id", "is_active", "created_at"]


class RecurringRuleCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecurringBookingRule
        fields = [
            "service",
            "address",
            "description",
            "start_date",
            "start_time",
            "duration_minutes",
            "frequency",
            "occurrences",
        ]


class BookingAcceptSerializer(serializers.Serializer):
    note = serializers.CharField(
        required=False, allow_blank=True, max_length=255
    )


class RescheduleDecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["accept", "decline"])


class RescheduleRequestCreateSerializer(serializers.ModelSerializer):
    proposed_duration_minutes = serializers.IntegerField(min_value=15)

    def validate_proposed_start(self, value):
        if value < timezone.now():
            raise serializers.ValidationError(
                "Alege un interval din viitor."
            )
        return value

    class Meta:
        model = RescheduleRequest
        fields = ["proposed_start", "proposed_duration_minutes", "note"]
