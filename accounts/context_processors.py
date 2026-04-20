from django.urls import reverse

from .models import Notification, NotificationPreference


def _build_breadcrumbs(request):
    match = getattr(request, "resolver_match", None)
    if not match or not match.url_name:
        return []

    view_name = (
        f"{match.namespace}:{match.url_name}"
        if match.namespace
        else match.url_name
    )
    if view_name == "pages:home":
        return []

    crumbs = [{"label": "Acasă", "url": reverse("pages:home")}]
    pk = (match.kwargs or {}).get("pk")

    if view_name == "services:list":
        trail = [("Categorii de ajutor", None)]
    elif view_name == "pages:how_it_works":
        trail = [("Cum funcționează", None)]
    elif view_name == "pages:faq":
        trail = [("Întrebări frecvente", None)]
    elif view_name == "pages:apply":
        trail = [("Devino membru", None)]
    elif view_name == "pages:help_request_create":
        trail = [("Cerere comunitară", None)]
    elif view_name == "bookings:list":
        trail = [("Ajutorul meu", None)]
    elif view_name == "bookings:create":
        trail = [
            ("Ajutorul meu", reverse("bookings:list")),
            ("Cere ajutor", None),
        ]
    elif view_name == "bookings:detail":
        trail = [
            ("Ajutorul meu", reverse("bookings:list")),
            (f"Comanda #{pk}", None),
        ]
    elif view_name == "bookings:reschedule":
        trail = [
            ("Ajutorul meu", reverse("bookings:list")),
            (f"Comanda #{pk}", reverse("bookings:detail", args=[pk])),
            ("Reprogramare", None),
        ]
    elif view_name == "bookings:cancel":
        trail = [
            ("Ajutorul meu", reverse("bookings:list")),
            (f"Comanda #{pk}", reverse("bookings:detail", args=[pk])),
            ("Anulare", None),
        ]
    elif view_name == "bookings:complete":
        trail = [
            ("Ajutorul meu", reverse("bookings:list")),
            (f"Comanda #{pk}", reverse("bookings:detail", args=[pk])),
            ("Finalizare", None),
        ]
    elif view_name == "bookings:provider_dashboard":
        trail = [("Panou voluntar", None)]
    elif view_name == "bookings:disputes_list":
        trail = [("Dispute", None)]
    elif view_name == "chat:conversation_list":
        trail = [("Chat", None)]
    elif view_name == "chat:conversation_detail":
        trail = [
            ("Chat", reverse("chat:conversation_list")),
            (f"Conversație #{pk}", None),
        ]
    elif view_name == "accounts:profile":
        trail = [("Cont", None), ("Profil", None)]
    elif view_name == "accounts:favorites":
        trail = [
            ("Cont", reverse("accounts:profile")),
            ("Favorite", None),
        ]
    elif view_name == "accounts:notifications":
        trail = [
            ("Cont", reverse("accounts:profile")),
            ("Notificări", None),
        ]
    elif view_name == "accounts:notification_preferences":
        trail = [
            ("Cont", reverse("accounts:profile")),
            ("Notificări", reverse("accounts:notifications")),
            ("Preferințe", None),
        ]
    elif view_name == "accounts:provider_detail":
        trail = [("Prestator", None)]
    elif view_name == "accounts:login":
        trail = [("Autentificare", None)]
    elif view_name == "accounts:signup":
        trail = [("Creează cont", None)]
    else:
        trail = [(match.url_name.replace("_", " ").capitalize(), None)]

    for label, url in trail:
        crumbs.append({"label": label, "url": url})

    if crumbs:
        crumbs[-1]["url"] = None
    return crumbs


def shell_context(request):
    user = getattr(request, "user", None)
    sound_enabled = False
    unread_count = 0
    if user and user.is_authenticated:
        sound_enabled = bool(
            NotificationPreference.objects.filter(user=user)
            .values_list("in_app_sound", flat=True)
            .first()
        )
        unread_count = Notification.objects.filter(user=user, is_read=False).count()

    return {
        "breadcrumbs": _build_breadcrumbs(request),
        "ui_notification_sound_enabled": sound_enabled,
        "unread_notifications_count": unread_count,
    }
