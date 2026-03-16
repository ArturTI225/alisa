from django.conf import settings
from django.db import models


def chat_upload_path(instance, filename: str) -> str:
    convo_id = instance.conversation_id or "misc"
    return f"chat/{convo_id}/{filename}"


class Conversation(models.Model):
    ad = models.ForeignKey(
        "ads.Ad",
        related_name="conversations",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    booking = models.ForeignKey(
        "bookings.Booking",
        related_name="conversations",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    help_request = models.ForeignKey(
        "bookings.HelpRequest",
        related_name="conversations",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name="conversations", blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Conversation {self.pk}"


class ChatMessage(models.Model):
    conversation = models.ForeignKey(
        Conversation,
        related_name="messages",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    booking = models.ForeignKey(
        "bookings.Booking",
        related_name="messages",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_messages",
    )
    text = models.TextField(blank=True)
    attachment = models.FileField(
        upload_to=chat_upload_path, blank=True, null=True
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"Message #{self.pk} - convo {self.conversation_id}"
