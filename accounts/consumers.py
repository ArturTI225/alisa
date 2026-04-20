"""
Per-user notification WebSocket. One group per user (`user_<id>`).

accounts.utils.notify_user() already calls channel_layer.group_send with
`type: "notify.message"` — this consumer just forwards the payload to the
connected browser so toasts / bell updates render live.
"""

from channels.generic.websocket import AsyncJsonWebsocketConsumer


def group_name_for(user_id: int) -> str:
    return f"user_{user_id}"


class NotificationConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            await self.close(code=4401)
            return

        self.group_name = group_name_for(user.id)
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def notify_message(self, event):
        await self.send_json({"event": event.get("event", "notification"), "payload": event.get("payload", {})})
