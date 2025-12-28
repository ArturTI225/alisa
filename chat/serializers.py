from rest_framework import serializers

from accounts.models import User
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
            "participants",
            "participant_ids",
            "created_at",
        ]
        read_only_fields = ["id", "participants", "created_at"]


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
