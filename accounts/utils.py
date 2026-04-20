from typing import Optional

from django.conf import settings
from django.utils import timezone

from config.observability import get_current_request_id

try:
    from asgiref.sync import async_to_sync
    from channels.layers import get_channel_layer
except ImportError:  # channels optional
    async_to_sync = None
    get_channel_layer = None

from .models import Notification
from .models import AuditLog


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
    request_id: str = "",
) -> Optional[Notification]:
    notif_type = notif_type or Notification.Type.GENERAL
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

    resolved_request_id = request_id or get_current_request_id(default="")
    payload = {
        "id": notif.id,
        "type": notif.type,
        "title": notif.title,
        "body": notif.body,
        "link": notif.link,
        "is_read": notif.is_read,
        "created_at": notif.created_at.isoformat(),
    }
    if resolved_request_id:
        payload["request_id"] = resolved_request_id

    _push_ws(
        user.id,
        payload,
    )
    return notif


def scan_uploaded_file(uploaded_file) -> bool:
    """
    Basic antivirus hook. If settings.VIRUS_SCAN_HANDLER is provided,
    it will be called with the uploaded file; returning False raises a reject.
    The default is a no-op placeholder to allow later integration.
    """
    handler = getattr(settings, "VIRUS_SCAN_HANDLER", None)
    if callable(handler):
        return bool(handler(uploaded_file))
    return True


def log_audit(
    actor,
    action: str,
    target_obj=None,
    metadata: Optional[dict] = None,
    request=None,
):
    """
    Append-only audit log helper. target_obj may be a model instance.
    """
    target_model = ""
    target_id = ""
    if target_obj is not None:
        target_model = target_obj.__class__.__name__
        target_id = getattr(target_obj, "pk", "") or ""
    meta = metadata or {}
    if request is not None:
        ip = request.META.get("REMOTE_ADDR") or ""
        ua = request.META.get("HTTP_USER_AGENT") or ""
        if ip:
            meta.setdefault("ip", ip)
        if ua:
            meta.setdefault("user_agent", ua)
    return AuditLog.objects.create(
        actor=actor if getattr(actor, "id", None) else None,
        action=action,
        target_model=target_model,
        target_id=str(target_id),
        metadata=meta,
    )
