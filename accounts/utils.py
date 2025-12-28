from typing import Optional

try:
    from asgiref.sync import async_to_sync
    from channels.layers import get_channel_layer
except ImportError:  # channels optional
    async_to_sync = None
    get_channel_layer = None

from .models import Notification


NOTIF_PREF_FIELD = {
    Notification.Type.NEW_MESSAGE: "chat_messages",
    Notification.Type.NEW_BID: "bids",
    Notification.Type.BID_ACCEPTED: "bids",
    Notification.Type.URGENT_AD_NEARBY: "urgent_ads",
    Notification.Type.REVIEW: "reviews",
}


def _push_ws(user_id: int, payload: dict):
    if not (async_to_sync and get_channel_layer):
        return
    layer = get_channel_layer()
    if not layer:
        return
    async_to_sync(layer.group_send)(
        f"user_{user_id}",
        {"type": "notify.message", "event": "notification", "payload": payload},
    )


def notify_user(
    user,
    notif_type: str,
    title: str,
    body: str = "",
    link: str = "",
) -> Optional[Notification]:
    pref = getattr(user, "notification_pref", None)
    pref_field = NOTIF_PREF_FIELD.get(notif_type)
    if pref and pref_field and not getattr(pref, pref_field, True):
        return None
    notif = Notification.objects.create(
        user=user,
        type=notif_type,
        title=title,
        body=body or "",
        link=link or "",
    )
    _push_ws(
        user.id,
        {
            "id": notif.id,
            "type": notif.type,
            "title": notif.title,
            "body": notif.body,
            "link": notif.link,
            "is_read": notif.is_read,
            "created_at": notif.created_at.isoformat(),
        },
    )
    return notif
