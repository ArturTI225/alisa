"""
WebSocket consumer for chat conversations.

Protocol:
  Client → Server
    {"action": "typing"}                 — broadcast "user N is typing"
    {"action": "read", "message_id": M}  — mark message M as read

  Server → Client
    {"event": "message.new", "message": {...serialized...}}
    {"event": "message.typing", "user_id": N, "display_name": "..."}
    {"event": "message.read", "message_id": M, "user_id": N}

Authentication happens via session cookie through AuthMiddlewareStack in
config/asgi.py. Participation is re-checked against the DB on connect.

Messages are not persisted here — clients POST to the existing DRF endpoint
(/api/v1/chat-messages/) and the viewset's perform_create broadcasts via the
`broadcast_message` helper below, so there is one source of truth for DB writes.
"""

import json
import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from config.observability import get_current_request_id

from .models import ChatMessage, Conversation


logger = logging.getLogger(__name__)


def group_name_for(conversation_id: int) -> str:
    return f"chat_{conversation_id}"


class ConversationConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            await self.close(code=4401)
            return

        self.conversation_id = int(self.scope["url_route"]["kwargs"]["conversation_id"])
        self.group_name = group_name_for(self.conversation_id)

        allowed = await self._is_participant(user.id, self.conversation_id)
        if not allowed:
            await self.close(code=4403)
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            return

        action = content.get("action")
        if action == "typing":
            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "chat.typing",
                    "user_id": user.id,
                    "display_name": getattr(user, "display_name", user.username),
                },
            )
        elif action == "read":
            message_id = content.get("message_id")
            if isinstance(message_id, int):
                await self._mark_read(message_id, user.id, self.conversation_id)
                await self.channel_layer.group_send(
                    self.group_name,
                    {
                        "type": "chat.read",
                        "message_id": message_id,
                        "user_id": user.id,
                    },
                )

    # --- group event handlers (names match the "type" key above) ---

    async def chat_message(self, event):
        """Fired by broadcast_message() when a new ChatMessage is created."""
        payload = {"event": "message.new", "message": event["message"]}
        request_id = event.get("request_id")
        if request_id:
            payload["request_id"] = request_id
        await self.send_json(payload)

    async def chat_typing(self, event):
        user = self.scope.get("user")
        if user and user.id == event["user_id"]:
            return  # don't echo typing back to the typer
        await self.send_json(
            {
                "event": "message.typing",
                "user_id": event["user_id"],
                "display_name": event["display_name"],
            }
        )

    async def chat_read(self, event):
        await self.send_json(
            {
                "event": "message.read",
                "message_id": event["message_id"],
                "user_id": event["user_id"],
            }
        )

    # --- db helpers ---

    @database_sync_to_async
    def _is_participant(self, user_id: int, conversation_id: int) -> bool:
        return Conversation.objects.filter(
            pk=conversation_id, participants__id=user_id
        ).exists()

    @database_sync_to_async
    def _mark_read(self, message_id: int, user_id: int, conversation_id: int) -> None:
        ChatMessage.objects.filter(
            pk=message_id,
            conversation_id=conversation_id,
            is_read=False,
        ).exclude(sender_id=user_id).update(is_read=True)


def broadcast_message(conversation_id: int, message_payload: dict, request_id: str = "") -> None:
    """
    Push a serialized message to everyone connected to a conversation.
    Called from the DRF viewset after a successful create. Safe to call from
    sync code; returns silently if channels is not configured.
    """
    try:
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer
    except ImportError:
        return

    layer = get_channel_layer()
    if layer is None:
        return

    resolved_request_id = request_id or get_current_request_id(default="")

    try:
        event = {"type": "chat.message", "message": message_payload}
        if resolved_request_id:
            event["request_id"] = resolved_request_id
        async_to_sync(layer.group_send)(group_name_for(conversation_id), event)
    except Exception:
        logger.exception("Failed to broadcast chat message for convo %s", conversation_id)
