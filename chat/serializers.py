from django.conf import settings
from rest_framework import serializers

from accounts.models import User
from accounts.utils import scan_uploaded_file
from .models import ChatMessage, Conversation


class ConversationSerializer(serializers.ModelSerializer):
    participants = serializers.PrimaryKeyRelatedField(
        many=True, read_only=True
    )
    participant_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        write_only=True,
        required=False,
        queryset=User.objects.all(),
        source="participants",
    )

    class Meta:
        model = Conversation
        fields = [
            "id",
            "ad",
            "booking",
            "help_request",
            "participants",
            "participant_ids",
            "created_at",
        ]
        read_only_fields = ["id", "participants", "created_at"]

    def validate(self, attrs):
        help_request = attrs.get("help_request")
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if help_request and user and user.is_authenticated:
            allowed = user.is_staff or user in [
                help_request.created_by,
                help_request.matched_volunteer,
            ]
            if not allowed:
                raise serializers.ValidationError(
                    "Nu poti crea conversatie pentru aceasta cerere."
                )
        return attrs


class ChatMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source="sender.display_name", read_only=True)
    conversation = serializers.PrimaryKeyRelatedField(
        queryset=Conversation.objects.all()
    )
    booking = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = ChatMessage
        fields = [
            "id",
            "conversation",
            "booking",
            "sender",
            "sender_name",
            "text",
            "attachment",
            "created_at",
        ]
        read_only_fields = ["id", "sender_name", "created_at", "sender"]

    def validate_attachment(self, value):
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
