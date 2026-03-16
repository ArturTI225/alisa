from django.utils import timezone
from django.conf import settings
from rest_framework import serializers

from accounts.models import Address
from accounts.serializers import AddressSerializer, UserSerializer
from accounts.utils import scan_uploaded_file
from services.models import Service, ServiceCategory
from services.serializers import ServiceSerializer, ServiceCategorySerializer
from .models import (
    Booking,
    BookingDispute,
    BookingEvent,
    BookingAttachment,
    HelpRequest,
    HelpRequestAttachment,
    VolunteerApplication,
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

    def validate_file(self, value):
        if not value:
            return value
        max_size = getattr(settings, "MAX_UPLOAD_SIZE", 0)
        if max_size and value.size > max_size:
            raise serializers.ValidationError("Fi?ier prea mare.")
        allowed = getattr(settings, "ALLOWED_UPLOAD_MIME_TYPES", [])
        content_type = getattr(value, "content_type", "")
        if allowed and content_type and content_type not in allowed:
            raise serializers.ValidationError("Tip fi?ier neacceptat.")
        if scan_uploaded_file(value) is False:
            raise serializers.ValidationError("Fi?ier respins la scanarea antivirus.")
        return value


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
            "started_at",
            "completed_at",
            "client_confirmed_at",
            "client_confirmation_note",
            "status",
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


class HelpRequestAttachmentSerializer(serializers.ModelSerializer):
    uploaded_by = UserSerializer(read_only=True)

    class Meta:
        model = HelpRequestAttachment
        fields = ["id", "file", "note", "uploaded_by", "created_at"]
        read_only_fields = ["id", "uploaded_by", "created_at"]

    def validate_file(self, value):
        if not value:
            return value
        max_size = getattr(settings, "MAX_UPLOAD_SIZE", 0)
        if max_size and value.size > max_size:
            raise serializers.ValidationError("Fi?ier prea mare.")
        allowed = getattr(settings, "ALLOWED_UPLOAD_MIME_TYPES", [])
        content_type = getattr(value, "content_type", "")
        if allowed and content_type and content_type not in allowed:
            raise serializers.ValidationError("Tip fi?ier neacceptat.")
        if scan_uploaded_file(value) is False:
            raise serializers.ValidationError("Fi?ier respins la scanarea antivirus.")
        return value


class VolunteerApplicationSerializer(serializers.ModelSerializer):
    volunteer = UserSerializer(read_only=True)
    help_request = serializers.PrimaryKeyRelatedField(
        queryset=HelpRequest.objects.all(), write_only=True
    )

    class Meta:
        model = VolunteerApplication
        fields = [
            "id",
            "volunteer",
            "help_request",
            "message",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "volunteer", "status", "created_at", "updated_at"]


class HelpRequestSerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)
    matched_volunteer = UserSerializer(read_only=True)
    applications = VolunteerApplicationSerializer(many=True, read_only=True)
    attachments = serializers.SerializerMethodField()
    category = ServiceCategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=ServiceCategory.objects.filter(is_active=True),
        source="category",
        write_only=True,
    )

    class Meta:
        model = HelpRequest
        fields = [
            "id",
            "title",
            "description",
            "category",
            "category_id",
            "city",
            "region",
            "urgency",
            "status",
            "matched_volunteer",
            "accepted_at",
            "started_at",
            "completed_at",
            "canceled_at",
            "cancel_reason",
            "is_locked",
            "created_at",
            "updated_at",
            "created_by",
            "applications",
            "attachments",
        ]
        read_only_fields = [
            "id",
            "status",
            "matched_volunteer",
            "accepted_at",
            "started_at",
            "completed_at",
            "canceled_at",
            "cancel_reason",
            "is_locked",
            "created_at",
            "updated_at",
            "created_by",
            "applications",
            "attachments",
        ]

    def get_attachments(self, obj):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        allowed = False
        if user and user.is_authenticated:
            if user.is_staff or user == obj.created_by or user == obj.matched_volunteer:
                allowed = True
        if not allowed:
            return []
        return HelpRequestAttachmentSerializer(obj.attachments.all(), many=True, context=self.context).data

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        return super().create(validated_data)

    def validate_title(self, value):
        if len(value.strip()) < 5:
            raise serializers.ValidationError("Titlul trebuie să aibă cel puțin 5 caractere.")
        return value

    def validate_description(self, value):
        if len(value.strip()) < 10:
            raise serializers.ValidationError("Descrierea trebuie să aibă cel puțin 10 caractere.")
        return value
