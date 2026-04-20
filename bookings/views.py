from datetime import timedelta
import csv

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import models
from django.db import transaction
from django.db.models import Avg
from django.core.files.storage import default_storage
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils.crypto import get_random_string
from django.utils import timezone
from django.utils.text import slugify
from django.views import generic, View
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.template.loader import render_to_string
from django.conf import settings
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import APIException
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle, ScopedRateThrottle
from django.core.cache import cache

from accounts.models import Address, User, Badge, Notification
from accounts.utils import notify_user, log_audit
from services.models import Service, ServiceCategory
from .utils_pdf import generate_pdf_from_html
from reviews.models import Review
from .forms import (
    BookingForm,
    CancelBookingForm,
    CompleteBookingForm,
    RescheduleRequestForm,
    ResolveDisputeForm,
    DisputeMessageForm,
    BookingRepeatForm,
    RecurringBookingForm,
    BookingAttachmentForm,
)
from .models import Availability, Booking, BookingEvent, RescheduleRequest
from .models import (
    BookingDispute,
    RecurringBookingRule,
    BookingAttachment,
    HelpRequest,
    HelpRequestAttachment,
    CompletionCertificate,
    VolunteerApplication,
)
from .storage_utils import get_signed_url
from .serializers import (
    BookingAcceptSerializer,
    BookingCancelSerializer,
    BookingCompleteSerializer,
    ClientConfirmationSerializer,
    BookingSerializer,
    BookingRepeatSerializer,
    RescheduleDecisionSerializer,
    RescheduleRequestCreateSerializer,
    RescheduleRequestSerializer,
    RecurringRuleCreateSerializer,
    RecurringRuleSerializer,
    HelpRequestSerializer,
    VolunteerApplicationSerializer,
    HelpRequestAttachmentSerializer,
)
from .utils import (
    ensure_help_request_conversation,
    ensure_booking_conversation,
    validate_provider_slot,
)


class IsHelpRequestOwnerOrAdmin(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_staff or request.user == obj.created_by or request.user == getattr(
            obj, "matched_volunteer", None
        )


class IdempotentMixin:
    """
    Simple idempotency helper using Idempotency-Key header.
    Stores short-lived keys in cache to return the existing resource on replay.
    """

    idem_ttl = 60 * 5

    def _idem_cache_key(self, scope: str, key: str) -> str:
        return f"idem:{scope}:{key}"

    def _get_cached_instance(self, model_cls, scope: str, key: str):
        existing_id = cache.get(self._idem_cache_key(scope, key))
        if existing_id:
            return model_cls.objects.filter(pk=existing_id).first()
        return None

    def _remember_instance(self, instance, scope: str, key: str):
        if not key or not instance:
            return
        cache.set(self._idem_cache_key(scope, key), instance.pk, timeout=self.idem_ttl)


class ConflictError(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Conflict cu starea curenta a resursei."
    default_code = "conflict"


class HelpRequestThrottle(ScopedRateThrottle):
    scope = "help-requests"

    def get_rate(self):
        from django.conf import settings

        rates = settings.REST_FRAMEWORK.get("DEFAULT_THROTTLE_RATES", {}) if hasattr(settings, "REST_FRAMEWORK") else {}
        return rates.get(self.scope) or super().get_rate()


def append_help_request_history(help_request: HelpRequest, new_status: str, actor):
    history = help_request.status_history or []
    history.append(
        {
            "status": new_status,
            "timestamp": timezone.now().isoformat(),
            "actor": getattr(actor, "id", None),
        }
    )
    help_request.status_history = history


def find_available_provider(service, address, start, duration_minutes: int):
    """Naive matching: find first verified provider skilled on service, available in city and slot."""
    if not service:
        return None
    end_time = start + timedelta(minutes=duration_minutes)
    weekday = start.isoweekday()

    candidates = (
        User.objects.filter(
            role=User.Roles.PROVIDER,
            provider_profile__verification_status="verified",
            provider_profile__skills=service,
        )
        .distinct()
        .order_by("first_name", "last_name")
    )
    if address and address.city:
        candidates = candidates.filter(city__iexact=address.city)

    for provider in candidates:
        if provider.availability_exceptions.filter(
            date=start.date(), is_available=False
        ).exists():
            continue
        if not Availability.objects.filter(
            provider=provider,
            weekday=weekday,
            is_active=True,
            start_time__lte=start.time(),
            end_time__gte=end_time.time(),
        ).exists():
            continue

        overlapping = Booking.objects.filter(
            provider=provider,
            status__in=[
                Booking.Status.PENDING,
                Booking.Status.CONFIRMED,
                Booking.Status.IN_PROGRESS,
                Booking.Status.RESCHEDULE_REQUESTED,
            ],
        )
        slot_free = True
        for booking in overlapping:
            if booking.scheduled_start < end_time and booking.scheduled_end > start:
                slot_free = False
                break
        if slot_free:
            return provider
    return None


class BookingListView(LoginRequiredMixin, generic.ListView):
    model = Booking
    template_name = "bookings/list.html"
    context_object_name = "bookings"

    def get_queryset(self):
        user = self.request.user
        if getattr(user, "is_provider", False):
            qs = Booking.objects.filter(provider=user).select_related(
                "service",
                "client",
                "address",
                "accepted_by",
                "dispute__opened_by",
                "dispute__resolved_by",
            ).prefetch_related(
                "events__actor",
                "reschedule_requests__requested_by",
                "reschedule_requests__responded_by",
                "dispute__messages__author",
            )
        else:
            qs = Booking.objects.filter(client=user).select_related(
                "service",
                "provider",
                "address",
                "accepted_by",
                "dispute__opened_by",
                "dispute__resolved_by",
            ).prefetch_related(
                "events__actor",
                "reschedule_requests__requested_by",
                "reschedule_requests__responded_by",
            )
        return qs.order_by("-is_urgent", "-created_at")


class BookingCreateView(generic.CreateView):
    form_class = BookingForm
    template_name = "bookings/create.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_success_url(self):
        return reverse("bookings:detail", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        categories = (
            ServiceCategory.objects.filter(is_active=True)
            .annotate(
                services_count=models.Count(
                    "services",
                    filter=models.Q(services__is_active=True),
                    distinct=True,
                )
            )
            .order_by("-services_count", "name")
        )
        ctx["categories"] = categories[:10]
        ctx["popular_services"] = (
            Service.objects.filter(is_active=True)
            .select_related("category")
            .order_by("category__name", "name")[:12]
        )
        return ctx

    def _build_guest_username(self, email: str) -> str:
        base = slugify((email or "").split("@")[0]) or "guest"
        base = base[:120]
        candidate = base
        suffix = 1
        while User.objects.filter(username=candidate).exists():
            suffix_text = f"-{suffix}"
            candidate = f"{base[:150 - len(suffix_text)]}{suffix_text}"
            suffix += 1
        return candidate

    def _create_guest_client(self, form) -> User:
        data = form.cleaned_data
        email = (data.get("guest_email") or "").strip().lower()
        user = User.objects.create_user(
            username=self._build_guest_username(email),
            password=get_random_string(24),
            email=email,
            first_name=data.get("guest_first_name", "").strip(),
            last_name=data.get("guest_last_name", "").strip(),
            phone=data.get("guest_phone", "").strip(),
            city=(data.get("guest_city") or data.get("address_city") or "").strip(),
            role=User.Roles.CLIENT,
        )
        login(
            self.request,
            user,
            backend="django.contrib.auth.backends.ModelBackend",
        )
        messages.success(
            self.request,
            "Cont de solicitant creat automat. Cererea de ajutor a fost trimisa.",
        )
        return user

    def _resolve_address(self, form, client_user: User, authenticated_user: bool) -> Address:
        resolved = form.cleaned_data.get("resolved_address")
        if resolved:
            return resolved
        data = form.cleaned_data
        city = (
            data.get("address_city")
            or data.get("guest_city")
            or ""
        ).strip()
        street = (
            data.get("address_line")
            or data.get("guest_street")
            or ""
        ).strip()
        details = (
            data.get("address_details")
            or data.get("guest_address_details")
            or ""
        ).strip()

        existing = Address.objects.filter(
            user=client_user,
            city__iexact=city,
            street__iexact=street,
            details__iexact=details,
        ).first()
        if existing:
            return existing

        return Address.objects.create(
            user=client_user,
            label="Cerere rapida",
            city=city,
            street=street,
            details=details,
            is_default=not Address.objects.filter(user=client_user).exists(),
        )

    def form_valid(self, form):
        authenticated_user = self.request.user.is_authenticated
        client_user = self.request.user if authenticated_user else self._create_guest_client(form)
        form.instance.client = client_user
        form.instance.service = form.cleaned_data["service"]
        form.instance.address = self._resolve_address(form, client_user, authenticated_user)
        if not form.instance.provider:
            candidate = find_available_provider(
                form.instance.service,
                form.instance.address,
                form.instance.scheduled_start,
                form.instance.duration_minutes,
            )
            form.instance.provider = candidate
        return super().form_valid(form)


class DisputeListView(LoginRequiredMixin, generic.ListView):
    template_name = "bookings/disputes_list.html"
    context_object_name = "disputes"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied("Doar staff-ul poate vedea disputele.")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        status_filter = self.request.GET.get("status") or "open"
        qs = BookingDispute.objects.select_related(
            "booking__client",
            "booking__provider",
            "assigned_to",
            "opened_by",
            "resolved_by",
        )
        if status_filter in ["open", "resolved"]:
            qs = qs.filter(status=status_filter)
        search = (self.request.GET.get("q") or "").strip()
        if search:
            qs = qs.filter(
                models.Q(reason__icontains=search)
                | models.Q(booking__id__icontains=search)
            )
        return qs.order_by("-created_at")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["status_filter"] = self.request.GET.get("status") or "open"
        ctx["search"] = self.request.GET.get("q") or ""
        return ctx


class BookingDetailView(LoginRequiredMixin, generic.DetailView):
    model = Booking
    template_name = "bookings/detail.html"
    context_object_name = "booking"

    def get_queryset(self):
        user = self.request.user
        return Booking.objects.filter(
            models.Q(client=user) | models.Q(provider=user)
        ).select_related(
            "service", "client", "provider", "address", "accepted_by", "dispute__opened_by", "dispute__resolved_by"
        ).prefetch_related(
            "events__actor",
            "reschedule_requests__requested_by",
            "reschedule_requests__responded_by",
            "dispute__messages__author",
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        pending_reschedule = self.object.reschedule_requests.filter(
            status=RescheduleRequest.Status.PENDING
        ).first()
        user = self.request.user
        ctx.update(
            {
                "pending_reschedule": pending_reschedule,
                "events": self.object.events.select_related("actor").all(),
                "can_manage": self.object.status
                not in [
                    Booking.Status.CANCELED,
                    Booking.Status.COMPLETED,
                    Booking.Status.DECLINED,
                    Booking.Status.DISPUTED,
                ],
                "can_provider_decide": (
                    getattr(user, "is_provider", False)
                    and self.object.provider in [None, user]
                    and self.object.status
                    in [
                        Booking.Status.PENDING,
                        Booking.Status.RESCHEDULE_REQUESTED,
                    ]
                ),
                "can_start": getattr(user, "is_provider", False)
                and self.object.provider == user
                and self.object.status == Booking.Status.CONFIRMED,
                "can_complete": getattr(user, "is_provider", False)
                and self.object.provider == user
                and self.object.status == Booking.Status.IN_PROGRESS,
                "can_client_confirm": (
                    getattr(user, "is_client", False)
                    and self.object.client == user
                    and self.object.status == Booking.Status.AWAITING_CLIENT
                ),
                "attachment_form": BookingAttachmentForm(),
                "message_form": DisputeMessageForm(),
                "attachments": self.object.attachments.select_related(
                    "uploaded_by"
                ),
            }
        )
        return ctx


class BookingRescheduleView(LoginRequiredMixin, generic.FormView):
    form_class = RescheduleRequestForm
    template_name = "bookings/reschedule.html"

    def dispatch(self, request, *args, **kwargs):
        self.booking = get_object_or_404(Booking, pk=kwargs["pk"])
        if request.user not in [self.booking.client, self.booking.provider]:
            raise PermissionDenied("Nu ai acces la aceasta cerere.")
        if self.booking.status in [
            Booking.Status.CANCELED,
            Booking.Status.COMPLETED,
            Booking.Status.IN_PROGRESS,
            Booking.Status.DECLINED,
        ]:
            messages.error(request, "Cererea nu mai poate fi reprogramata.")
            return redirect("bookings:detail", pk=self.booking.pk)
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["booking"] = self.booking
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["booking"] = self.booking
        return ctx

    def form_valid(self, form):
        data = form.cleaned_data
        reschedule_request = RescheduleRequest.objects.create(
            booking=self.booking,
            requested_by=self.request.user,
            proposed_start=data["scheduled_start"],
            proposed_duration_minutes=data["duration_minutes"],
            note=data.get("note", ""),
            previous_status=self.booking.status,
        )
        self.booking.status = Booking.Status.RESCHEDULE_REQUESTED
        self.booking.save(update_fields=["status", "updated_at"])
        self.booking.add_event(
            BookingEvent.EventType.RESCHEDULE_REQUESTED,
            f"Reprogramare propusa pentru {data['scheduled_start']:%d %b %H:%M}",
            actor=self.request.user,
            payload={
                "duration_minutes": data["duration_minutes"],
                "note": data.get("note", ""),
                "request_id": reschedule_request.id,
            },
        )
        messages.success(
            self.request,
            "Solicitarea de reprogramare a fost trimisa catre celalalt utilizator.",
        )
        return redirect("bookings:detail", pk=self.booking.pk)


class BookingRescheduleDecisionView(LoginRequiredMixin, generic.View):
    def post(self, request, pk, request_id, decision):
        booking = get_object_or_404(Booking, pk=pk)
        reschedule_request = get_object_or_404(
            RescheduleRequest, pk=request_id, booking=booking
        )
        if request.user not in [booking.client, booking.provider]:
            raise PermissionDenied("Nu ai acces la aceasta cerere.")
        if booking.status in [
            Booking.Status.CANCELED,
            Booking.Status.COMPLETED,
            Booking.Status.DECLINED,
        ]:
            messages.info(request, "Cererea nu mai poate fi modificata.")
            return redirect("bookings:detail", pk=pk)
        if reschedule_request.status != RescheduleRequest.Status.PENDING:
            messages.info(request, "Solicitarea a fost deja procesata.")
            return redirect("bookings:detail", pk=pk)
        if reschedule_request.requested_by == request.user:
            messages.error(request, "Nu poti aproba propria solicitare.")
            return redirect("bookings:detail", pk=pk)

        if decision == "accept":
            if booking.provider:
                try:
                    validate_provider_slot(
                        booking.provider,
                        reschedule_request.proposed_start,
                        reschedule_request.proposed_duration_minutes,
                        booking=booking,
                    )
                except ValidationError as exc:
                    messages.error(request, "; ".join(exc.messages))
                    return redirect("bookings:detail", pk=pk)
            booking.scheduled_start = reschedule_request.proposed_start
            booking.duration_minutes = (
                reschedule_request.proposed_duration_minutes
            )
            booking.status = reschedule_request.previous_status
            booking.save(
                update_fields=["scheduled_start", "duration_minutes", "status"]
            )
            reschedule_request.status = RescheduleRequest.Status.APPROVED
            reschedule_request.responded_by = request.user
            reschedule_request.responded_at = timezone.now()
            reschedule_request.save(
                update_fields=["status", "responded_by", "responded_at"]
            )
            booking.add_event(
                BookingEvent.EventType.RESCHEDULE_APPROVED,
                "Reprogramarea a fost aprobata.",
                actor=request.user,
                payload={
                    "request_id": reschedule_request.id,
                    "new_start": reschedule_request.proposed_start.isoformat(),
                    "duration_minutes": reschedule_request.proposed_duration_minutes,
                },
            )
            messages.success(request, "Reprogramarea a fost aprobata.")
        else:
            booking.status = reschedule_request.previous_status
            booking.save(update_fields=["status", "updated_at"])
            reschedule_request.status = RescheduleRequest.Status.DECLINED
            reschedule_request.responded_by = request.user
            reschedule_request.responded_at = timezone.now()
            reschedule_request.save(
                update_fields=["status", "responded_by", "responded_at"]
            )
            booking.add_event(
                BookingEvent.EventType.RESCHEDULE_DECLINED,
                "Reprogramarea a fost respinsa.",
                actor=request.user,
                payload={"request_id": reschedule_request.id},
            )
            messages.info(request, "Reprogramarea a fost respinsa.")
        return redirect("bookings:detail", pk=pk)


class BookingCancelView(LoginRequiredMixin, generic.FormView):
    form_class = CancelBookingForm
    template_name = "bookings/cancel.html"

    def dispatch(self, request, *args, **kwargs):
        self.booking = get_object_or_404(Booking, pk=kwargs["pk"])
        if request.user not in [self.booking.client, self.booking.provider]:
            raise PermissionDenied("Nu ai acces la aceasta cerere.")
        if self.booking.status in [
            Booking.Status.CANCELED,
            Booking.Status.COMPLETED,
            Booking.Status.IN_PROGRESS,
            Booking.Status.DECLINED,
        ]:
            messages.info(request, "Cererea nu mai poate fi anulata.")
            return redirect("bookings:detail", pk=self.booking.pk)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["booking"] = self.booking
        return ctx

    def form_valid(self, form):
        self.booking.status = Booking.Status.CANCELED
        self.booking.cancel_reason = form.cleaned_data.get("reason", "")
        self.booking.canceled_by = self.request.user
        self.booking.canceled_at = timezone.now()
        self.booking.save(
            update_fields=[
                "status",
                "cancel_reason",
                "canceled_by",
                "canceled_at",
                "updated_at",
            ]
        )
        self.booking.add_event(
            BookingEvent.EventType.CANCELED,
            "Cererea a fost anulata.",
            actor=self.request.user,
            payload={"reason": self.booking.cancel_reason},
        )
        messages.success(self.request, "Cererea a fost anulata.")
        return redirect("bookings:detail", pk=self.booking.pk)


class BookingDeclineView(LoginRequiredMixin, generic.FormView):
    form_class = CancelBookingForm
    template_name = "bookings/decline.html"

    def dispatch(self, request, *args, **kwargs):
        self.booking = get_object_or_404(Booking, pk=kwargs["pk"])
        if not getattr(request.user, "is_provider", False):
            raise PermissionDenied("Doar voluntarul poate refuza.")
        if self.booking.provider not in [None, request.user]:
            raise PermissionDenied("Nu esti asignat la aceasta cerere.")
        if self.booking.status not in [
            Booking.Status.PENDING,
            Booking.Status.RESCHEDULE_REQUESTED,
        ]:
            messages.info(request, "Cererea nu mai poate fi refuzata.")
            return redirect("bookings:detail", pk=self.booking.pk)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["booking"] = self.booking
        return ctx

    def form_valid(self, form):
        self.booking.status = Booking.Status.DECLINED
        self.booking.cancel_reason = form.cleaned_data.get("reason", "")
        self.booking.canceled_by = self.request.user
        self.booking.canceled_at = timezone.now()
        self.booking.save(
            update_fields=[
                "status",
                "cancel_reason",
                "canceled_by",
                "canceled_at",
                "updated_at",
            ]
        )
        self.booking.add_event(
            BookingEvent.EventType.DECLINED,
            "Cererea a fost refuzata de voluntar.",
            actor=self.request.user,
            payload={"reason": self.booking.cancel_reason},
        )
        messages.success(self.request, "Ai refuzat cererea.")
        return redirect("bookings:detail", pk=self.booking.pk)


class BookingAcceptView(LoginRequiredMixin, generic.View):
    def post(self, request, pk):
        from chat.models import ChatMessage

        booking = get_object_or_404(Booking, pk=pk)
        if not getattr(request.user, "is_provider", False):
            raise PermissionDenied("Doar voluntarul poate accepta.")
        if booking.provider not in [None, request.user]:
            raise PermissionDenied("Nu esti asignat la aceasta cerere.")
        if booking.status not in [
            Booking.Status.PENDING,
            Booking.Status.RESCHEDULE_REQUESTED,
            Booking.Status.DISPUTED,
        ]:
            messages.info(request, "Cererea nu mai poate fi acceptata.")
            return redirect("bookings:detail", pk=pk)
        booking.provider = booking.provider or request.user
        booking.status = Booking.Status.CONFIRMED
        booking.accepted_at = timezone.now()
        booking.accepted_by = request.user
        booking.save(
            update_fields=[
                "provider",
                "status",
                "accepted_at",
                "accepted_by",
                "updated_at",
            ]
        )
        booking.add_event(
            BookingEvent.EventType.ACCEPTED,
            "Cererea a fost acceptata de voluntar.",
            actor=request.user,
        )

        conversation = ensure_booking_conversation(booking)
        if conversation:
            chat_text = "Voluntarul a acceptat cererea de ajutor."
            ChatMessage.objects.create(
                conversation=conversation,
                booking=booking,
                sender=request.user,
                text=chat_text,
            )
            for user in conversation.participants.exclude(pk=request.user.pk):
                notify_user(
                    user=user,
                    notif_type=Notification.Type.NEW_MESSAGE,
                    title="Mesaj nou",
                    body=chat_text,
                    link=f"/chat/{conversation.pk}/",
                )

        messages.success(request, "Cererea a fost acceptata. Mesaj trimis in chat.")
        return redirect("bookings:detail", pk=pk)


class BookingStartView(LoginRequiredMixin, generic.View):
    def post(self, request, pk):
        booking = get_object_or_404(Booking, pk=pk)
        if not getattr(request.user, "is_provider", False):
            raise PermissionDenied("Doar voluntarul poate incepe.")
        if booking.provider != request.user:
            raise PermissionDenied("Nu esti asignat la aceasta cerere.")
        if booking.status != Booking.Status.CONFIRMED:
            messages.info(request, "Cererea nu poate fi pornita in acest status.")
            return redirect("bookings:detail", pk=pk)
        booking.status = Booking.Status.IN_PROGRESS
        booking.started_at = timezone.now()
        booking.save(update_fields=["status", "started_at", "updated_at"])
        booking.add_event(
            BookingEvent.EventType.STATUS_CHANGED,
            "Voluntarul a marcat cererea ca In curs.",
            actor=request.user,
        )
        messages.success(request, "Cererea este in curs.")
        return redirect("bookings:detail", pk=pk)


class BookingCompleteView(LoginRequiredMixin, generic.FormView):
    form_class = CompleteBookingForm
    template_name = "bookings/complete.html"

    def dispatch(self, request, *args, **kwargs):
        self.booking = get_object_or_404(Booking, pk=kwargs["pk"])
        if not getattr(request.user, "is_provider", False):
            raise PermissionDenied("Doar voluntarul poate finaliza.")
        if self.booking.provider != request.user:
            raise PermissionDenied("Nu esti asignat la aceasta cerere.")
        if self.booking.status != Booking.Status.IN_PROGRESS:
            messages.info(request, "Cererea nu poate fi finalizata in acest status.")
            return redirect("bookings:detail", pk=self.booking.pk)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["booking"] = self.booking
        return ctx

    def form_valid(self, form):
        self.booking.status = Booking.Status.AWAITING_CLIENT
        self.booking.completed_at = timezone.now()
        self.booking.save(
            update_fields=[
                "status",
                "completed_at",
                "updated_at",
            ]
        )
        note = form.cleaned_data.get("note", "")
        self.booking.add_event(
            BookingEvent.EventType.STATUS_CHANGED,
            "Cererea a fost marcata ca finalizata de voluntar (in asteptare confirmare solicitant).",
            actor=self.request.user,
            payload={
                "note": note,
            },
        )
        messages.success(
            self.request,
            "Cererea a fost marcata ca finalizata. Asteptam confirmarea solicitantului.",
        )
        return redirect("bookings:detail", pk=self.booking.pk)


class BookingClientConfirmView(LoginRequiredMixin, View):
    def post(self, request, pk):
        booking = get_object_or_404(Booking, pk=pk)
        user = request.user
        if booking.client != user:
            raise PermissionDenied("Doar solicitantul poate confirma.")
        if booking.status != Booking.Status.AWAITING_CLIENT:
            messages.info(request, "Nu se poate confirma in acest status.")
            return redirect("bookings:detail", pk=pk)

        note = (request.POST.get("note") or "").strip()
        booking.status = Booking.Status.COMPLETED
        booking.client_confirmed_at = timezone.now()
        booking.client_confirmation_note = note
        booking.save(
            update_fields=[
                "status",
                "client_confirmed_at",
                "client_confirmation_note",
                "updated_at",
            ]
        )
        booking.add_event(
            BookingEvent.EventType.STATUS_CHANGED,
            "Solicitantul a confirmat finalizarea.",
            actor=user,
            payload={"note": note},
        )
        messages.success(request, "Ai confirmat finalizarea cererii.")
        return redirect("bookings:detail", pk=pk)


class BookingClientDisputeView(LoginRequiredMixin, View):
    def post(self, request, pk):
        booking = get_object_or_404(Booking, pk=pk)
        user = request.user
        if booking.client != user:
            raise PermissionDenied("Doar solicitantul poate marca disputa.")
        if booking.status != Booking.Status.AWAITING_CLIENT:
            messages.info(request, "Nu se poate disputa in acest status.")
            return redirect("bookings:detail", pk=pk)

        note = (request.POST.get("note") or "").strip()
        booking.status = Booking.Status.DISPUTED
        booking.client_confirmed_at = timezone.now()
        booking.client_confirmation_note = note
        dispute, created = BookingDispute.objects.get_or_create(
            booking=booking,
            defaults={
                "opened_by": user,
                "reason": note,
                "escalated_at": timezone.now(),
            },
        )
        if not created and not dispute.escalated_at:
            dispute.escalated_at = timezone.now()
            dispute.save(update_fields=["escalated_at"])
        if not dispute.reason:
            dispute.reason = note
            dispute.save(update_fields=["reason"])

        booking.save(
            update_fields=[
                "status",
                "client_confirmed_at",
                "client_confirmation_note",
                "updated_at",
            ]
        )
        booking.add_event(
            BookingEvent.EventType.DISPUTE_OPENED,
            "Solicitantul a deschis o disputa.",
            actor=user,
            payload={
                "note": note,
                "dispute_id": dispute.id,
                "escalated_at": dispute.escalated_at.isoformat()
                if dispute.escalated_at
                else None,
            },
        )
        messages.info(request, "Disputa a fost deschisa.")
        return redirect("bookings:detail", pk=pk)


class BookingResolveDisputeView(LoginRequiredMixin, generic.FormView):
    form_class = ResolveDisputeForm
    template_name = "bookings/resolve_dispute.html"

    def dispatch(self, request, *args, **kwargs):
        self.booking = get_object_or_404(Booking, pk=kwargs["pk"])
        self.dispute = getattr(self.booking, "dispute", None)
        if not self.dispute or self.dispute.status != self.dispute.Status.OPEN:
            messages.info(request, "Nu exista disputa activa.")
            return redirect("bookings:detail", pk=self.booking.pk)
        if not (getattr(request.user, "is_provider", False) or request.user.is_staff):
            raise PermissionDenied("Nu poti marca rezolvarea.")
        if getattr(request.user, "is_provider", False) and self.booking.provider != request.user:
            raise PermissionDenied("Nu esti asignat la aceasta cerere.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["booking"] = self.booking
        ctx["dispute"] = self.dispute
        ctx["dispute_messages"] = self.dispute.messages.select_related("author")
        ctx["message_form"] = DisputeMessageForm()
        return ctx

    def form_valid(self, form):
        note = form.cleaned_data.get("resolution_note", "")
        self.dispute.status = self.dispute.Status.RESOLVED
        self.dispute.resolution_note = note
        self.dispute.resolved_by = self.request.user
        self.dispute.resolved_at = timezone.now()
        self.dispute.save(
            update_fields=["status", "resolution_note", "resolved_by", "resolved_at"]
        )
        self.booking.status = Booking.Status.COMPLETED
        self.booking.save(update_fields=["status", "updated_at"])
        self.booking.add_event(
            BookingEvent.EventType.DISPUTE_RESOLVED,
            "Voluntarul a rezolvat disputa.",
            actor=self.request.user,
            payload={"note": note},
        )
        messages.success(self.request, "Disputa a fost marcata rezolvata.")
        return redirect("bookings:detail", pk=self.booking.pk)


class BookingDisputeMessageView(LoginRequiredMixin, generic.FormView):
    form_class = DisputeMessageForm
    template_name = "bookings/resolve_dispute.html"

    def dispatch(self, request, *args, **kwargs):
        self.booking = get_object_or_404(Booking, pk=kwargs["pk"])
        self.dispute = getattr(self.booking, "dispute", None)
        if not self.dispute or self.dispute.status != self.dispute.Status.OPEN:
            messages.info(request, "Nu exista disputa activa.")
            return redirect("bookings:detail", pk=self.booking.pk)
        if request.user not in [self.booking.client, self.booking.provider]:
            raise PermissionDenied("Nu ai acces la aceasta disputa.")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        self.dispute.messages.create(
            author=self.request.user,
            text=form.cleaned_data["text"],
            attachment=self.request.FILES.get("attachment"),
        )
        self.booking.add_event(
            BookingEvent.EventType.NOTE,
            "Mesaj nou in disputa.",
            actor=self.request.user,
        )
        messages.success(self.request, "Mesaj trimis in disputa.")
        return redirect("bookings:detail", pk=self.booking.pk)


class BookingRepeatView(LoginRequiredMixin, generic.FormView):
    form_class = BookingRepeatForm
    template_name = "bookings/repeat.html"

    def dispatch(self, request, *args, **kwargs):
        self.booking = get_object_or_404(Booking, pk=kwargs["pk"])
        if self.booking.client != request.user:
            raise PermissionDenied("Doar solicitantul poate duplica cererea.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["booking"] = self.booking
        return ctx

    def form_valid(self, form):
        start = form.cleaned_data.get("scheduled_start") or timezone.now()
        duration = form.cleaned_data.get("duration_minutes") or self.booking.duration_minutes
        new_booking = Booking.objects.create(
            client=self.request.user,
            provider=self.booking.provider,
            service=self.booking.service,
            address=self.booking.address,
            description=self.booking.description,
            scheduled_start=start,
            duration_minutes=duration,
            status=Booking.Status.PENDING,
        )
        new_booking.add_event(
            BookingEvent.EventType.NOTE,
            "Cerere duplicata dintr-un ajutor anterior.",
            actor=self.request.user,
            payload={"source_booking": self.booking.id},
        )
        messages.success(self.request, "Cererea a fost duplicata.")
        return redirect("bookings:detail", pk=new_booking.pk)


class RecurringBookingCreateView(LoginRequiredMixin, generic.FormView):
    form_class = RecurringBookingForm
    template_name = "bookings/recurring.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        rule = RecurringBookingRule.objects.create(
            client=self.request.user,
            service=form.cleaned_data["service"],
            provider=form.cleaned_data.get("provider"),
            address=form.cleaned_data["address"],
            description=form.cleaned_data.get("description", ""),
            start_date=form.cleaned_data["start_date"],
            start_time=form.cleaned_data["start_time"],
            duration_minutes=form.cleaned_data["duration_minutes"],
            frequency=form.cleaned_data["frequency"],
            occurrences=form.cleaned_data["occurrences"],
        )
        current_date = rule.start_date
        for _ in range(rule.occurrences):
            start_dt = timezone.make_aware(
                timezone.datetime.combine(current_date, rule.start_time)
            )
            Booking.objects.create(
                client=self.request.user,
                provider=rule.provider,
                service=rule.service,
                address=rule.address,
                description=rule.description,
                scheduled_start=start_dt,
                duration_minutes=rule.duration_minutes,
                status=Booking.Status.PENDING,
                recurring_rule=rule,
            )
            if rule.frequency == RecurringBookingRule.Frequency.WEEKLY:
                current_date += timezone.timedelta(days=7)
            elif rule.frequency == RecurringBookingRule.Frequency.BIWEEKLY:
                current_date += timezone.timedelta(days=14)
            else:
                current_date += timezone.timedelta(days=30)
        messages.success(self.request, "Seria recurentДѓ a fost creatДѓ.")
        return redirect("bookings:list")


class RecurringRuleListView(LoginRequiredMixin, generic.TemplateView):
    template_name = "bookings/recurring_list.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["rules"] = RecurringBookingRule.objects.filter(
            client=self.request.user
        ).select_related("service", "provider", "address")
        return ctx


class RecurringRuleCancelView(LoginRequiredMixin, View):
    def post(self, request, pk):
        rule = get_object_or_404(RecurringBookingRule, pk=pk, client=request.user)
        rule.is_active = False
        rule.save(update_fields=["is_active"])
        # cancel pending future bookings
        future = Booking.objects.filter(
            recurring_rule=rule,
            status__in=[
                Booking.Status.PENDING,
                Booking.Status.CONFIRMED,
                Booking.Status.RESCHEDULE_REQUESTED,
                Booking.Status.AWAITING_CLIENT,
            ],
        )
        for b in future:
            b.status = Booking.Status.CANCELED
            b.cancel_reason = "Seria recurenta a fost anulata."
            b.save(update_fields=["status", "cancel_reason", "updated_at"])
            b.add_event(
                BookingEvent.EventType.CANCELED,
                "Cerere anulata deoarece seria a fost oprita.",
                actor=request.user,
            )
        messages.info(request, "Seria a fost oprita si cererile viitoare au fost anulate.")
        return redirect("bookings:recurring_list")


class RecurringRuleTriggerNextView(LoginRequiredMixin, View):
    def post(self, request, pk):
        rule = get_object_or_404(RecurringBookingRule, pk=pk, client=request.user)
        if not rule.is_active:
            messages.error(request, "Seria este dezactivata.")
            return redirect("bookings:recurring_list")
        # find last occurrence
        last_booking = (
            rule.bookings.order_by("-scheduled_start").first()
            or None
        )
        if last_booking:
            current_date = last_booking.scheduled_start.date()
        else:
            current_date = rule.start_date
        if rule.frequency == RecurringBookingRule.Frequency.WEEKLY:
            next_date = current_date + timezone.timedelta(days=7)
        elif rule.frequency == RecurringBookingRule.Frequency.BIWEEKLY:
            next_date = current_date + timezone.timedelta(days=14)
        else:
            next_date = current_date + timezone.timedelta(days=30)

        start_dt = timezone.make_aware(
            timezone.datetime.combine(next_date, rule.start_time)
        )
        booking = Booking.objects.create(
            client=request.user,
            provider=rule.provider,
            service=rule.service,
            address=rule.address,
            description=rule.description,
            scheduled_start=start_dt,
            duration_minutes=rule.duration_minutes,
            status=Booking.Status.PENDING,
            recurring_rule=rule,
        )
        booking.add_event(
            BookingEvent.EventType.NOTE,
            "Cerere generata manual din seria recurenta.",
            actor=request.user,
            payload={"rule_id": rule.id},
        )
        messages.success(request, "Am generat urmatoarea cerere din serie.")
        return redirect("bookings:detail", pk=booking.pk)


class RecurringRuleSkipNextView(LoginRequiredMixin, View):
    def post(self, request, pk):
        rule = get_object_or_404(RecurringBookingRule, pk=pk, client=request.user)
        upcoming = Booking.objects.filter(
            recurring_rule=rule,
            status__in=[
                Booking.Status.PENDING,
                Booking.Status.CONFIRMED,
                Booking.Status.RESCHEDULE_REQUESTED,
                Booking.Status.AWAITING_CLIENT,
            ],
            scheduled_start__gte=timezone.now(),
        ).order_by("scheduled_start").first()
        if not upcoming:
            messages.info(request, "Nu exista cereri viitoare de sarit.")
            return redirect("bookings:recurring_list")
        upcoming.status = Booking.Status.CANCELED
        upcoming.cancel_reason = "Sarit in seria recurenta."
        upcoming.save(update_fields=["status", "cancel_reason", "updated_at"])
        upcoming.add_event(
            BookingEvent.EventType.CANCELED,
            "Cerere anulata (skip urmatoarea din serie).",
            actor=request.user,
        )
        messages.info(request, "Urmatoarea cerere a fost sarita.")
        return redirect("bookings:recurring_list")


class ProviderDashboardView(LoginRequiredMixin, generic.TemplateView):
    template_name = "bookings/provider_dashboard.html"

    def dispatch(self, request, *args, **kwargs):
        if not getattr(request.user, "is_provider", False):
            raise PermissionDenied("Doar voluntarii au acces la acest dashboard.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        now = timezone.now()
        period_start = now - timezone.timedelta(days=30)
        upcoming = (
            Booking.objects.filter(
                provider=user,
                scheduled_start__gte=now,
                status__in=[
                    Booking.Status.PENDING,
                    Booking.Status.CONFIRMED,
                    Booking.Status.IN_PROGRESS,
                    Booking.Status.RESCHEDULE_REQUESTED,
                ],
            )
            .select_related("service", "client", "address")
            .order_by("scheduled_start")[:10]
        )
        disputes = (
            BookingDispute.objects.filter(
                models.Q(assigned_to=user)
                | models.Q(booking__provider=user),
                status=BookingDispute.Status.OPEN,
            )
            .select_related("booking", "booking__client", "assigned_to")
            .order_by("-created_at")[:5]
        )
        recurring = (
            RecurringBookingRule.objects.filter(provider=user, is_active=True)
            .select_related("service", "address")
            .order_by("-created_at")[:5]
        )
        recent = Booking.objects.filter(provider=user, created_at__gte=period_start)
        stats = {
            "total_30d": recent.count(),
            "completed_30d": recent.filter(status=Booking.Status.COMPLETED).count(),
            "canceled_30d": recent.filter(status=Booking.Status.CANCELED).count(),
            "accepted_rate": 0,
        }
        total_for_rate = recent.count() or 1
        accepted_count = recent.filter(accepted_by=user).count()
        stats["accepted_rate"] = round((accepted_count / total_for_rate) * 100)
        reviews = Review.objects.filter(booking__provider=user)
        stats["avg_rating"] = round(
            reviews.aggregate(avg=Avg("rating"))["avg"] or 0, 2
        )
        stats["reviews_count"] = reviews.count()
        minutes_donated = (
            recent.filter(status=Booking.Status.COMPLETED).aggregate(
                total=models.Sum("duration_minutes")
            )["total"]
            or 0
        )
        stats["hours_30d"] = round(minutes_donated / 60, 1) if minutes_donated else 0
        ctx.update(
            {
                "upcoming": upcoming,
                "open_disputes": disputes,
                "recurring_rules": recurring,
                "provider_stats": stats,
            }
        )
        return ctx


class ProviderEarningsCSVView(LoginRequiredMixin, View):
    def get(self, request):
        user = request.user
        if not getattr(user, "is_provider", False):
            raise PermissionDenied("Doar voluntarii pot exporta rapoartele.")
        start_param = request.GET.get("start")
        end_param = request.GET.get("end")
        try:
            start = (
                timezone.datetime.fromisoformat(start_param)
                if start_param
                else timezone.now() - timezone.timedelta(days=30)
            )
            end = (
                timezone.datetime.fromisoformat(end_param)
                if end_param
                else timezone.now()
            )
        except ValueError:
            start = timezone.now() - timezone.timedelta(days=30)
            end = timezone.now()

        qs = (
            Booking.objects.filter(
                provider=user,
                scheduled_start__range=(start, end),
            )
            .select_related("service", "client")
            .order_by("scheduled_start")
        )

        response = HttpResponse(content_type="text/csv")
        response[
            "Content-Disposition"
        ] = f'attachment; filename="earnings_{user.username}.csv"'
        writer = csv.writer(response)
        writer.writerow(
            [
                "Booking ID",
                "Status",
                "Start",
                "Service",
                "Client",
                "Estimated",
                "Final",
            ]
        )
        for b in qs:
            writer.writerow(
                [
                    b.pk,
                    b.status,
                    timezone.localtime(b.scheduled_start).strftime(
                        "%Y-%m-%d %H:%M"
                    ),
                    b.service.name,
                    b.client.display_name,
                ]
            )
        return response


class BookingAssignDisputeView(LoginRequiredMixin, generic.View):
    def post(self, request, pk):
        booking = get_object_or_404(Booking, pk=pk)
        dispute = getattr(booking, "dispute", None)
        if not dispute or dispute.status != dispute.Status.OPEN:
            messages.info(request, "Nu exista disputa activa.")
            return redirect("bookings:detail", pk=pk)
        if not request.user.is_staff:
            raise PermissionDenied("Doar staff-ul poate prelua dispute.")
        dispute.assigned_to = request.user
        dispute.save(update_fields=["assigned_to"])
        booking.add_event(
            BookingEvent.EventType.NOTE,
            "Disputa a fost asignata unui membru staff.",
            actor=request.user,
            payload={"staff": request.user.username},
        )
        messages.success(request, "Ai preluat disputa.")
        return redirect(request.META.get("HTTP_REFERER") or "bookings:detail", pk=pk)


class BookingAttachmentUploadView(LoginRequiredMixin, generic.FormView):
    form_class = BookingAttachmentForm
    template_name = "bookings/detail.html"

    def dispatch(self, request, *args, **kwargs):
        self.booking = get_object_or_404(Booking, pk=kwargs["pk"])
        if request.user not in [self.booking.client, self.booking.provider]:
            raise PermissionDenied("Nu ai acces la aceasta cerere.")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        attachment = form.save(commit=False)
        attachment.booking = self.booking
        attachment.uploaded_by = self.request.user
        attachment.save()
        self.booking.add_event(
            BookingEvent.EventType.NOTE,
            "A fost adДѓugat un fiИ™ier la comandДѓ.",
            actor=self.request.user,
            payload={"attachment_id": attachment.id, "note": attachment.note},
        )
        messages.success(self.request, "FiИ™ier Г®ncДѓrcat.")
        return redirect("bookings:detail", pk=self.booking.pk)


class BookingCalendarFeedView(LoginRequiredMixin, View):
    def get(self, request):
        user = request.user
        if getattr(user, "is_provider", False):
            qs = Booking.objects.filter(provider=user)
        else:
            qs = Booking.objects.filter(client=user)
        qs = qs.exclude(status=Booking.Status.CANCELED).select_related(
            "service", "address", "provider"
        )

        def fmt(dt):
            dt_utc = timezone.localtime(dt, timezone.utc)
            return dt_utc.strftime("%Y%m%dT%H%M%SZ")

        lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//sot-la-ora//bookings//EN",
            "CALSCALE:GREGORIAN",
            f"X-WR-CALNAME:Cereri {user.username}",
        ]
        for booking in qs:
            uid = f"booking-{booking.pk}@sotlaora"
            start = fmt(booking.scheduled_start)
            end = fmt(booking.scheduled_end)
            summary = f"{booking.service.name}"
            description = f"Status: {booking.get_status_display()}"
            location = f"{booking.address}"
            lines.extend(
                [
                    "BEGIN:VEVENT",
                    f"UID:{uid}",
                    f"DTSTAMP:{fmt(timezone.now())}",
                    f"DTSTART:{start}",
                    f"DTEND:{end}",
                    f"SUMMARY:{summary}",
                    f"DESCRIPTION:{description}",
                    f"LOCATION:{location}",
                    "END:VEVENT",
                ]
            )
        lines.append("END:VCALENDAR")
        content = "\r\n".join(lines)
        resp = HttpResponse(content, content_type="text/calendar")
        resp["Content-Disposition"] = 'attachment; filename="bookings.ics"'
        return resp

class BookingViewSet(viewsets.ModelViewSet):
    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticated]
    action_serializer_classes = {
        "cancel": BookingCancelSerializer,
        "request_reschedule": RescheduleRequestCreateSerializer,
        "respond_reschedule": RescheduleDecisionSerializer,
        "accept": BookingAcceptSerializer,
        "decline": BookingCancelSerializer,
        "start": BookingAcceptSerializer,
        "complete": BookingCompleteSerializer,
        "client_confirm": ClientConfirmationSerializer,
        "client_dispute": ClientConfirmationSerializer,
        "repeat": BookingRepeatSerializer,
        "create_recurring": RecurringRuleCreateSerializer,
    }

    def get_serializer_class(self):
        if hasattr(self, "action") and self.action in self.action_serializer_classes:
            return self.action_serializer_classes[self.action]
        return super().get_serializer_class()

    def get_queryset(self):
        user = self.request.user
        params = self.request.query_params
        if getattr(user, "is_provider", False):
            qs = Booking.objects.filter(provider=user).select_related(
                "service", "client", "address"
            )
        else:
            qs = Booking.objects.filter(client=user).select_related(
                "service", "provider", "address"
            )
        urgent_param = params.get("urgent") or params.get("is_urgent")
        if urgent_param is not None:
            urgent_flag = str(urgent_param).lower() in ["1", "true", "yes", "y"]
            qs = qs.filter(is_urgent=urgent_flag)
        urgency_level = params.get("urgency_level")
        if urgency_level:
            qs = qs.filter(urgency_level=urgency_level)
        city = params.get("city")
        if city:
            qs = qs.filter(address__city__iexact=city)
        return qs.order_by("-is_urgent", "-created_at")

    def perform_create(self, serializer):
        provider = None
        start = serializer.validated_data.get("scheduled_start")
        duration = serializer.validated_data.get("duration_minutes", 60)
        service = serializer.validated_data.get("service")
        address = serializer.validated_data.get("address")
        if start and service:
            provider = find_available_provider(
                service, address, start, duration
            )
        serializer.save(client=self.request.user, provider=provider)

    def _ensure_participant(self, booking):
        user = self.request.user
        if user not in [booking.client, booking.provider]:
            raise PermissionDenied("Nu ai acces la aceasta cerere.")

    @action(detail=True, methods=["post"], url_path="request-reschedule")
    def request_reschedule(self, request, pk=None):
        booking = self.get_object()
        self._ensure_participant(booking)
        if booking.status in [
            Booking.Status.CANCELED,
            Booking.Status.COMPLETED,
            Booking.Status.IN_PROGRESS,
            Booking.Status.DECLINED,
            Booking.Status.DISPUTED,
        ]:
            return Response(
                {"detail": "Cererea nu mai poate fi reprogramata."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if booking.reschedule_requests.filter(
            status=RescheduleRequest.Status.PENDING
        ).exists():
            return Response(
                {"detail": "Exista deja o solicitare in asteptare."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        start = serializer.validated_data["proposed_start"]
        duration = serializer.validated_data.get(
            "proposed_duration_minutes", booking.duration_minutes
        )
        note = serializer.validated_data.get("note", "")
        if booking.provider:
            try:
                validate_provider_slot(
                    booking.provider, start, duration, booking=booking
                )
            except ValidationError as exc:
                return Response(
                    {"detail": "; ".join(exc.messages)},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        reschedule_request = RescheduleRequest.objects.create(
            booking=booking,
            requested_by=request.user,
            proposed_start=start,
            proposed_duration_minutes=duration,
            note=note,
            previous_status=booking.status,
        )
        booking.status = Booking.Status.RESCHEDULE_REQUESTED
        booking.save(update_fields=["status", "updated_at"])
        booking.add_event(
            BookingEvent.EventType.RESCHEDULE_REQUESTED,
            f"Reprogramare propusa pentru {start:%d %b %H:%M}",
            actor=request.user,
            payload={
                "duration_minutes": duration,
                "note": note,
                "request_id": reschedule_request.id,
            },
        )
        output = RescheduleRequestSerializer(
            reschedule_request, context=self.get_serializer_context()
        )
        return Response(output.data, status=status.HTTP_201_CREATED)

    @action(
        detail=True,
        methods=["post"],
        url_path="reschedule/(?P<request_id>[^/.]+)/respond",
    )
    def respond_reschedule(self, request, pk=None, request_id=None):
        booking = self.get_object()
        self._ensure_participant(booking)
        if booking.status in [
            Booking.Status.CANCELED,
            Booking.Status.COMPLETED,
            Booking.Status.DECLINED,
        ]:
            return Response(
                {"detail": "Cererea nu mai poate fi modificata."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        reschedule_request = get_object_or_404(
            RescheduleRequest, pk=request_id, booking=booking
        )
        if reschedule_request.status != RescheduleRequest.Status.PENDING:
            return Response(
                {"detail": "Solicitarea a fost deja procesata."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if reschedule_request.requested_by == request.user:
            return Response(
                {"detail": "Nu poti aproba propria solicitare."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        decision = serializer.validated_data["decision"]

        if decision == "accept":
            if booking.provider:
                try:
                    validate_provider_slot(
                        booking.provider,
                        reschedule_request.proposed_start,
                        reschedule_request.proposed_duration_minutes,
                        booking=booking,
                    )
                except ValidationError as exc:
                    return Response(
                        {"detail": "; ".join(exc.messages)},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            booking.scheduled_start = reschedule_request.proposed_start
            booking.duration_minutes = (
                reschedule_request.proposed_duration_minutes
            )
            booking.status = reschedule_request.previous_status
            booking.save(
                update_fields=["scheduled_start", "duration_minutes", "status"]
            )
            reschedule_request.status = RescheduleRequest.Status.APPROVED
            reschedule_request.responded_by = request.user
            reschedule_request.responded_at = timezone.now()
            reschedule_request.save(
                update_fields=["status", "responded_by", "responded_at"]
            )
            booking.add_event(
                BookingEvent.EventType.RESCHEDULE_APPROVED,
                "Reprogramarea a fost aprobata.",
                actor=request.user,
                payload={
                    "request_id": reschedule_request.id,
                    "new_start": reschedule_request.proposed_start.isoformat(),
                    "duration_minutes": reschedule_request.proposed_duration_minutes,
                },
            )
        else:
            booking.status = reschedule_request.previous_status
            booking.save(update_fields=["status", "updated_at"])
            reschedule_request.status = RescheduleRequest.Status.DECLINED
            reschedule_request.responded_by = request.user
            reschedule_request.responded_at = timezone.now()
            reschedule_request.save(
                update_fields=["status", "responded_by", "responded_at"]
            )
            booking.add_event(
                BookingEvent.EventType.RESCHEDULE_DECLINED,
                "Reprogramarea a fost respinsa.",
                actor=request.user,
                payload={"request_id": reschedule_request.id},
            )

        output = RescheduleRequestSerializer(
            reschedule_request, context=self.get_serializer_context()
        )
        return Response(output.data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        booking = self.get_object()
        self._ensure_participant(booking)
        if booking.status in [
            Booking.Status.CANCELED,
            Booking.Status.COMPLETED,
            Booking.Status.IN_PROGRESS,
            Booking.Status.DECLINED,
            Booking.Status.DISPUTED,
        ]:
            return Response(
                {"detail": "Cererea nu mai poate fi anulata."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        booking.status = Booking.Status.CANCELED
        booking.cancel_reason = serializer.validated_data.get("reason", "")
        booking.canceled_by = request.user
        booking.canceled_at = timezone.now()
        booking.save(
            update_fields=[
                "status",
                "cancel_reason",
                "canceled_by",
                "canceled_at",
                "updated_at",
            ]
        )
        booking.add_event(
            BookingEvent.EventType.CANCELED,
            "Cererea a fost anulata.",
            actor=request.user,
            payload={"reason": booking.cancel_reason},
        )
        output = BookingSerializer(
            booking, context=self.get_serializer_context()
        )
        return Response(output.data)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def accept(self, request, pk=None):
        idem_key = request.headers.get("Idempotency-Key")
        cache_key = None
        if idem_key:
            cache_key = f"idem:application_accept:{pk}:{idem_key}"
            from django.core.cache import cache

            if cache.get(cache_key):
                return Response(self.get_serializer(self.get_object()).data)
        application = self.get_queryset().select_for_update().get(pk=pk)
        help_request = application.help_request
        if help_request.is_locked and not request.user.is_staff:
            raise PermissionDenied("Cererea este blocat? de admin.")
        if request.user not in [help_request.created_by] and not request.user.is_staff:
            raise PermissionDenied("Nu po?i accepta aceast? aplica?ie.")
        if application.status != VolunteerApplication.Status.PENDING:
            return Response(
                {"detail": "Aplica?ie nu mai poate fi acceptat?."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if help_request.status not in [
            HelpRequest.Status.OPEN,
            HelpRequest.Status.IN_REVIEW,
        ]:
            return Response(
                {"detail": "Cererea nu poate fi acceptat? din acest status."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        existing = VolunteerApplication.objects.filter(
            help_request=help_request, status=VolunteerApplication.Status.ACCEPTED
        ).exclude(pk=application.pk)
        if existing.exists():
            return Response(
                {"detail": "ExistДѓ deja o aplicaИ›ie acceptatДѓ."},
                status=status.HTTP_409_CONFLICT,
            )
        VolunteerApplication.objects.filter(
            help_request=help_request,
            status=VolunteerApplication.Status.PENDING,
        ).exclude(pk=application.pk).update(
            status=VolunteerApplication.Status.REJECTED
        )
        application.status = VolunteerApplication.Status.ACCEPTED
        application.save(update_fields=["status", "updated_at"])
        help_request.status = HelpRequest.Status.MATCHED
        help_request.matched_volunteer = application.volunteer
        help_request.accepted_at = timezone.now()
        append_help_request_history(help_request, help_request.status, request.user)
        help_request.save(
            update_fields=["status", "matched_volunteer", "accepted_at", "updated_at", "status_history"]
        )
        notify_user(
            user=application.volunteer,
            notif_type=None,
            title="Aplica?ie acceptat?",
            body=help_request.title,
            link=f"/help-requests/{help_request.pk}/",
        )
        log_audit(
            request.user,
            "application_accepted",
            application,
            {"help_request": help_request.pk},
            request=request,
        )
        if cache_key:
            from django.core.cache import cache

            cache.set(cache_key, True, timeout=self.idem_ttl)
        return Response(self.get_serializer(application).data)


    @action(detail=True, methods=["post"])
    def decline(self, request, pk=None):
        booking = self.get_object()
        user = request.user
        if not getattr(user, "is_provider", False):
            raise PermissionDenied("Doar voluntarul poate refuza.")
        if booking.provider not in [None, user]:
            raise PermissionDenied("Nu esti asignat la aceasta cerere.")
        if booking.status not in [
            Booking.Status.PENDING,
            Booking.Status.RESCHEDULE_REQUESTED,
        ]:
            return Response(
                {"detail": "Cererea nu mai poate fi refuzata."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reason = serializer.validated_data.get("reason", "")

        booking.status = Booking.Status.DECLINED
        booking.cancel_reason = reason
        booking.canceled_by = user
        booking.canceled_at = timezone.now()
        booking.save(
            update_fields=[
                "status",
                "cancel_reason",
                "canceled_by",
                "canceled_at",
                "updated_at",
            ]
        )
        booking.add_event(
            BookingEvent.EventType.DECLINED,
            "Cererea a fost refuzata de voluntar.",
            actor=user,
            payload={"reason": reason},
        )
        return Response(
            BookingSerializer(booking, context=self.get_serializer_context()).data
        )

    @action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        booking = self.get_object()
        user = request.user
        if not getattr(user, "is_provider", False):
            raise PermissionDenied("Doar voluntarul poate incepe.")
        if booking.provider != user:
            raise PermissionDenied("Nu esti asignat la aceasta cerere.")
        if booking.status != Booking.Status.CONFIRMED:
            return Response(
                {"detail": "Cererea nu poate fi pornita."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        booking.status = Booking.Status.IN_PROGRESS
        booking.started_at = timezone.now()
        booking.save(update_fields=["status", "started_at", "updated_at"])
        booking.add_event(
            BookingEvent.EventType.STATUS_CHANGED,
            "Voluntarul a marcat cererea ca In curs.",
            actor=user,
        )
        return Response(
            BookingSerializer(booking, context=self.get_serializer_context()).data
        )

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        booking = self.get_object()
        user = request.user
        if not getattr(user, "is_provider", False):
            raise PermissionDenied("Doar voluntarul poate finaliza.")
        if booking.provider != user:
            raise PermissionDenied("Nu esti asignat la aceasta cerere.")
        if booking.status != Booking.Status.IN_PROGRESS:
            return Response(
                {"detail": "Cererea nu poate fi finalizata in acest status."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        booking.status = Booking.Status.COMPLETED
        booking.completed_at = timezone.now()
        booking.save(
            update_fields=[
                "status",
                "completed_at",
                "updated_at",
            ]
        )
        note = serializer.validated_data.get("note", "")
        booking.add_event(
            BookingEvent.EventType.STATUS_CHANGED,
            "Cererea a fost finalizata.",
            actor=user,
            payload={
                "note": note,
            },
        )
        return Response(
            BookingSerializer(booking, context=self.get_serializer_context()).data
        )

    @action(detail=True, methods=["post"])
    def repeat(self, request, pk=None):
        booking = self.get_object()
        if booking.client != request.user:
            raise PermissionDenied("Doar solicitantul poate duplica cererea.")
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_start = serializer.validated_data.get("scheduled_start") or timezone.now()
        duration = serializer.validated_data.get(
            "duration_minutes", booking.duration_minutes
        )
        new_booking = Booking.objects.create(
            client=request.user,
            provider=booking.provider,
            service=booking.service,
            address=booking.address,
            description=booking.description,
            scheduled_start=new_start,
            duration_minutes=duration,
            status=Booking.Status.PENDING,
        )
        new_booking.add_event(
            BookingEvent.EventType.NOTE,
            "Cerere duplicata dintr-un ajutor anterior.",
            actor=request.user,
            payload={"source_booking": booking.id},
        )
        return Response(
            BookingSerializer(
                new_booking, context=self.get_serializer_context()
            ).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["post"], url_path="recurring")
    def create_recurring(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        rule = RecurringBookingRule.objects.create(
            client=request.user,
            **serializer.validated_data,
        )
        # generate occurrences
        created = []
        current_date = rule.start_date
        for i in range(rule.occurrences):
            start_dt = timezone.make_aware(
                timezone.datetime.combine(current_date, rule.start_time)
            )
            booking = Booking.objects.create(
                client=request.user,
                provider=rule.provider,
                service=rule.service,
                address=rule.address,
                description=rule.description,
                scheduled_start=start_dt,
                duration_minutes=rule.duration_minutes,
                status=Booking.Status.PENDING,
                recurring_rule=rule,
            )
            created.append(booking)
            if rule.frequency == RecurringBookingRule.Frequency.WEEKLY:
                current_date += timezone.timedelta(days=7)
            elif rule.frequency == RecurringBookingRule.Frequency.BIWEEKLY:
                current_date += timezone.timedelta(days=14)
            else:
                # monthly: naive add 30 days
                current_date += timezone.timedelta(days=30)
        return Response(
            {
                "rule": RecurringRuleSerializer(rule, context=self.get_serializer_context()).data,
                "bookings": BookingSerializer(created, many=True, context=self.get_serializer_context()).data,
            },
            status=status.HTTP_201_CREATED,
        )
    @action(detail=True, methods=["post"])
    def client_confirm(self, request, pk=None):
        booking = self.get_object()
        user = request.user
        if booking.client != user:
            raise PermissionDenied("Doar solicitantul poate confirma.")
        if booking.status != Booking.Status.AWAITING_CLIENT:
            return Response(
                {"detail": "Nu se poate confirma in acest status."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        booking.status = Booking.Status.COMPLETED
        booking.client_confirmed_at = timezone.now()
        booking.client_confirmation_note = serializer.validated_data.get(
            "note", ""
        )
        booking.save(
            update_fields=[
                "status",
                "client_confirmed_at",
                "client_confirmation_note",
                "updated_at",
            ]
        )
        booking.add_event(
            BookingEvent.EventType.STATUS_CHANGED,
            "Solicitantul a confirmat finalizarea.",
            actor=user,
            payload={"note": booking.client_confirmation_note},
        )
        return Response(
            BookingSerializer(booking, context=self.get_serializer_context()).data
        )

    @action(detail=True, methods=["post"])
    def client_dispute(self, request, pk=None):
        booking = self.get_object()
        user = request.user
        if booking.client != user:
            raise PermissionDenied("Doar solicitantul poate marca disputa.")
        if booking.status != Booking.Status.AWAITING_CLIENT:
            return Response(
                {"detail": "Nu se poate disputa in acest status."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        booking.status = Booking.Status.DISPUTED
        booking.client_confirmed_at = timezone.now()
        booking.client_confirmation_note = serializer.validated_data.get(
            "note", ""
        )
        from .models import BookingDispute
        dispute, created = BookingDispute.objects.get_or_create(
            booking=booking,
            defaults={
                "opened_by": user,
                "reason": booking.client_confirmation_note,
                "escalated_at": timezone.now(),
            },
        )
        if created is False and not dispute.escalated_at:
            dispute.escalated_at = timezone.now()
            dispute.save(update_fields=["escalated_at"])
        if not dispute.reason:
            dispute.reason = booking.client_confirmation_note
            dispute.save(update_fields=["reason"])
        booking.save(
            update_fields=[
                "status",
                "client_confirmed_at",
                "client_confirmation_note",
                "updated_at",
            ]
        )
        booking.add_event(
            BookingEvent.EventType.DISPUTE_OPENED,
            "Solicitantul a deschis o disputa.",
            actor=user,
            payload={
                "note": booking.client_confirmation_note,
                "dispute_id": dispute.id,
                "escalated_at": dispute.escalated_at.isoformat()
                if dispute.escalated_at
                else None,
            },
        )
        return Response(
            BookingSerializer(booking, context=self.get_serializer_context()).data
        )

    @action(detail=True, methods=["get"], url_path="invoice")
    def invoice(self, request, pk=None):
        booking = self.get_object()
        if request.user not in [booking.client, booking.provider]:
            raise PermissionDenied("Nu ai acces la aceasta factura.")
        html = render_to_string(
            "bookings/invoice.html",
            {"booking": booking},
            request=request,
        )
        try:
            pdf_bytes = generate_pdf_from_html(html)
            response = HttpResponse(pdf_bytes, content_type="application/pdf")
            response[
                "Content-Disposition"
            ] = f'attachment; filename="booking_{booking.pk}.pdf"'
            return response
        except Exception:
            return HttpResponse(html)


# --- HelpRequest & VolunteerApplication API (non-commercial core) ---


class HelpRequestViewSet(IdempotentMixin, viewsets.ModelViewSet):
    queryset = HelpRequest.objects.select_related(
        "created_by", "matched_volunteer", "category"
    ).prefetch_related("applications__volunteer", "attachments")
    serializer_class = HelpRequestSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsHelpRequestOwnerOrAdmin]
    throttle_classes = [AnonRateThrottle, UserRateThrottle, HelpRequestThrottle]
    throttle_scope = "help-requests"

    def _ensure_not_locked(self, help_request):
        if help_request.is_locked and not self.request.user.is_staff:
            raise PermissionDenied("Cererea este blocatДѓ de admin.")

    def _auto_award_badges(self, profile, actor, request):
        # simple thresholds to avoid monetization; extendable
        thresholds = [1, 5, 10]
        for n in thresholds:
            name = f"Helper - {n} requests"
            badge, _ = Badge.objects.get_or_create(name=name, defaults={"description": f"{n} cereri finalizate"})
            if profile.completed_requests >= n and badge not in profile.badges.all():
                profile.badges.add(badge)
                log_audit(actor, "badge_awarded", badge, {"to": profile.user_id, "threshold": n}, request=request)

    def create(self, request, *args, **kwargs):
        idem_key = request.headers.get("Idempotency-Key")
        if idem_key:
            instance = self._get_cached_instance(HelpRequest, "help_request_create", idem_key)
            if instance:
                serializer = self.get_serializer(instance)
                return Response(serializer.data, status=status.HTTP_200_OK)
        response = super().create(request, *args, **kwargs)
        if idem_key and getattr(response, "data", None):
            created_id = response.data.get("id")
            if created_id:
                instance = HelpRequest.objects.filter(pk=created_id).first()
                self._remember_instance(instance, "help_request_create", idem_key)
        return response

    def perform_create(self, serializer):
        user = self.request.user
        if not getattr(user, "is_client", False) and not user.is_staff:
            raise PermissionDenied("Doar solicitantii pot crea cereri.")
        urgency = serializer.validated_data.get("urgency")
        if urgency == getattr(HelpRequest.Urgency, "HIGH", None) and not user.is_verified:
            raise PermissionDenied("Pentru urgentДѓ este necesarДѓ verificare.")
        serializer.save(created_by=self.request.user, status_history=[])
        notify_user(
            user=self.request.user,
            notif_type=None,
            title="Cerere creatДѓ",
            body=serializer.instance.title,
            link=f"/help-requests/{serializer.instance.pk}/",
        )
        log_audit(user, "help_request_created", serializer.instance, request=self.request)

    def perform_update(self, serializer):
        instance = self.get_object()
        if instance.status not in [
            HelpRequest.Status.OPEN,
            HelpRequest.Status.IN_REVIEW,
        ]:
            raise PermissionDenied("Cererea nu mai poate fi editatДѓ Г®n acest status.")
        # prevent status tampering via update; status changes via dedicated actions
        serializer.save(status=instance.status, matched_volunteer=instance.matched_volunteer)

    def perform_destroy(self, instance):
        user = self.request.user
        if user not in [instance.created_by] and not user.is_staff:
            raise PermissionDenied("Nu poИ›i И™terge aceastДѓ cerere.")
        instance.is_deleted = True
        instance.status = HelpRequest.Status.CANCELLED
        instance.cancel_reason = "deleted"
        instance.canceled_at = timezone.now()
        append_help_request_history(instance, instance.status, user)
        instance.save(
            update_fields=[
                "is_deleted",
                "status",
                "cancel_reason",
                "canceled_at",
                "updated_at",
                "status_history",
            ]
        )
        log_audit(user, "help_request_soft_deleted", instance, request=self.request)

    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_staff:
            qs = qs.filter(is_deleted=False)
        status_param = self.request.query_params.get("status")
        if status_param:
            qs = qs.filter(status=status_param)
        urgency = self.request.query_params.get("urgency")
        if urgency:
            qs = qs.filter(urgency=urgency)
        return qs

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        help_request = self.get_object()
        if request.user not in [help_request.created_by, help_request.matched_volunteer] and not request.user.is_staff:
            raise PermissionDenied("Nu poИ›i anula aceastДѓ cerere.")
        self._ensure_not_locked(help_request)
        if help_request.status in [HelpRequest.Status.DONE, HelpRequest.Status.CANCELLED]:
            return Response(self.get_serializer(help_request).data)
        serializer = BookingCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        help_request.status = HelpRequest.Status.CANCELLED
        help_request.cancel_reason = serializer.validated_data.get("reason", "")
        help_request.canceled_at = timezone.now()
        append_help_request_history(help_request, help_request.status, request.user)
        help_request.save(
            update_fields=[
                "status",
                "cancel_reason",
                "canceled_at",
                "updated_at",
                "status_history",
            ]
        )
        log_audit(
            request.user,
            "help_request_cancelled",
            help_request,
            {"reason": help_request.cancel_reason},
            request=request,
        )
        recipients = [help_request.created_by]
        if help_request.matched_volunteer and help_request.matched_volunteer not in recipients:
            recipients.append(help_request.matched_volunteer)
        for user in recipients:
            notify_user(
                user=user,
                notif_type=None,
                title="Cerere anulatДѓ",
                body=help_request.title,
                link=f"/help-requests/{help_request.pk}/",
            )
        return Response(self.get_serializer(help_request).data)

    @action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        help_request = self.get_object()
        if request.user not in [help_request.matched_volunteer] and not request.user.is_staff:
            raise PermissionDenied("Nu poИ›i porni aceastДѓ cerere.")
        self._ensure_not_locked(help_request)
        if not help_request.matched_volunteer:
            return Response(
                {"detail": "Cererea nu are voluntar atribuit."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if help_request.status not in [
            HelpRequest.Status.MATCHED,
            HelpRequest.Status.IN_PROGRESS,
        ]:
            raise ConflictError("Nu se poate porni Г®n acest status.")
        if help_request.status == HelpRequest.Status.IN_PROGRESS:
            return Response(self.get_serializer(help_request).data)
        help_request.status = HelpRequest.Status.IN_PROGRESS
        help_request.started_at = help_request.started_at or timezone.now()
        append_help_request_history(help_request, help_request.status, request.user)
        help_request.save(update_fields=["status", "started_at", "updated_at", "status_history"])
        notify_user(
            user=help_request.created_by,
            notif_type=None,
            title="Cerere Г®n curs",
            body=help_request.title,
            link=f"/help-requests/{help_request.pk}/",
        )
        log_audit(request.user, "help_request_started", help_request, request=request)
        return Response(self.get_serializer(help_request).data)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        help_request = self.get_object()
        if request.user not in [help_request.matched_volunteer] and not request.user.is_staff:
            raise PermissionDenied("Nu poИ›i finaliza aceastДѓ cerere.")
        self._ensure_not_locked(help_request)
        if help_request.status == HelpRequest.Status.DONE:
            return Response(self.get_serializer(help_request).data)
        if help_request.status != HelpRequest.Status.IN_PROGRESS:
            raise ConflictError("Nu se poate finaliza Г®n acest status.")
        help_request.status = HelpRequest.Status.DONE
        help_request.completed_at = timezone.now()
        append_help_request_history(help_request, help_request.status, request.user)
        help_request.save(update_fields=["status", "completed_at", "updated_at", "status_history"])
        notify_user(
            user=help_request.created_by,
            notif_type=None,
            title="Cerere finalizatДѓ",
            body=help_request.title,
            link=f"/help-requests/{help_request.pk}/",
        )
        return self._after_completion(help_request, request)

    @action(detail=True, methods=["post"])
    def send_to_review(self, request, pk=None):
        help_request = self.get_object()
        if not request.user.is_staff:
            raise PermissionDenied("Doar adminul poate trimite Г®n review.")
        if help_request.status != HelpRequest.Status.OPEN:
            raise ConflictError("Se poate trimite Г®n review doar din open.")
        help_request.status = HelpRequest.Status.IN_REVIEW
        append_help_request_history(help_request, help_request.status, request.user)
        help_request.save(update_fields=["status", "updated_at", "status_history"])
        notify_user(
            user=help_request.created_by,
            notif_type=None,
            title="Cerere Г®n review",
            body=help_request.title,
            link=f"/help-requests/{help_request.pk}/",
        )
        log_audit(request.user, "help_request_sent_to_review", help_request, request=request)
        return Response(self.get_serializer(help_request).data)

    def _after_completion(self, help_request, request):
        volunteer = help_request.matched_volunteer
        if volunteer and hasattr(volunteer, "provider_profile"):
            profile = volunteer.provider_profile
            profile.completed_requests = profile.completed_requests + 1
            profile.total_hours_helped = profile.total_hours_helped + 1
            profile.save(update_fields=["completed_requests", "total_hours_helped"])
            self._auto_award_badges(profile, request.user, request)
            from accounts.models import ProviderMonthlyStat
            today = timezone.now().date()
            monthly, _ = ProviderMonthlyStat.objects.get_or_create(
                provider=volunteer,
                year=today.year,
                month=today.month,
                defaults={"completed_requests": 0, "total_hours": 0},
            )
            monthly.completed_requests += 1
            monthly.total_hours += 1
            monthly.save(update_fields=["completed_requests", "total_hours", "updated_at"])
            try:
                from .tasks import generate_certificate
                request_id = getattr(request, "request_id", "")
                if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False):
                    certificate_id = generate_certificate(help_request.pk, request_id=request_id)
                else:
                    generate_certificate.delay(help_request.pk, request_id)
                    certificate_id = None
                if certificate_id:
                    cert = CompletionCertificate.objects.filter(pk=certificate_id).first()
                    if cert:
                        log_audit(request.user, "certificate_issued", cert, request=request)
            except Exception as exc:
                log_audit(request.user, "certificate_issue_failed", help_request, {"error": str(exc)}, request=request)
        log_audit(request.user, "help_request_completed", help_request, request=request)
        return Response(self.get_serializer(help_request).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        help_request = self.get_object()
        if not request.user.is_staff:
            raise PermissionDenied("Doar adminul poate aproba.")
        if help_request.status != HelpRequest.Status.IN_REVIEW:
            raise ConflictError("Poate fi aprobat doar din review.")
        help_request.status = HelpRequest.Status.OPEN
        append_help_request_history(help_request, help_request.status, request.user)
        help_request.save(update_fields=["status", "updated_at", "status_history"])
        notify_user(
            user=help_request.created_by,
            notif_type=None,
            title="Cerere aprobat?",
            body=help_request.title,
            link=f"/help-requests/{help_request.pk}/",
        )
        log_audit(request.user, "help_request_approved", help_request, request=request)
        return Response(self.get_serializer(help_request).data)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def reject(self, request, pk=None):
        help_request = self.get_object()
        if not request.user.is_staff:
            raise PermissionDenied("Doar adminul poate respinge.")
        if help_request.status not in [HelpRequest.Status.IN_REVIEW, HelpRequest.Status.OPEN]:
            raise ConflictError("Nu se poate respinge din acest status.")
        serializer = BookingCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        help_request.status = HelpRequest.Status.CANCELLED
        help_request.cancel_reason = serializer.validated_data.get("reason", "")
        help_request.canceled_at = timezone.now()
        append_help_request_history(help_request, help_request.status, request.user)
        help_request.save(update_fields=["status", "cancel_reason", "canceled_at", "updated_at", "status_history"])
        notify_user(
            user=help_request.created_by,
            notif_type=None,
            title="Cerere respins?",
            body=help_request.title,
            link=f"/help-requests/{help_request.pk}/",
        )
        log_audit(
            request.user,
            "help_request_rejected",
            help_request,
            {"reason": help_request.cancel_reason},
            request=request,
        )
        return Response(self.get_serializer(help_request).data)

    @action(detail=True, methods=["get"], url_path="certificate")
    def certificate(self, request, pk=None):
        help_request = self.get_object()
        cert = getattr(help_request, "completion_certificate", None)
        if not cert:
            return Response({"detail": "Certificat indisponibil."}, status=status.HTTP_404_NOT_FOUND)
        user = request.user
        allowed = user.is_staff or user == help_request.created_by or user == help_request.matched_volunteer
        if not allowed:
            raise PermissionDenied("Nu ai acces la acest certificat.")
        pdf_url = None
        if cert.pdf:
            pdf_url = get_signed_url(cert.pdf)
        data = {
            "id": cert.pk,
            "issued_at": cert.issued_at,
            "pdf_url": pdf_url,
            "summary": cert.summary,
        }
        return Response(data)


    @action(detail=True, methods=["post"])
    def lock(self, request, pk=None):
        help_request = self.get_object()
        if not request.user.is_staff:
            raise PermissionDenied("Doar adminul poate bloca.")
        help_request.is_locked = True
        help_request.save(update_fields=["is_locked", "updated_at"])
        log_audit(request.user, "help_request_locked", help_request, request=request)
        return Response(self.get_serializer(help_request).data)

    @action(detail=True, methods=["post"])
    def unlock(self, request, pk=None):
        help_request = self.get_object()
        if not request.user.is_staff:
            raise PermissionDenied("Doar adminul poate debloca.")
        help_request.is_locked = False
        help_request.save(update_fields=["is_locked", "updated_at"])
        log_audit(request.user, "help_request_unlocked", help_request, request=request)
        return Response(self.get_serializer(help_request).data)


class VolunteerApplicationViewSet(viewsets.ModelViewSet):
    queryset = VolunteerApplication.objects.select_related(
        "help_request", "volunteer", "help_request__created_by"
    )
    serializer_class = VolunteerApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [AnonRateThrottle, UserRateThrottle, ScopedRateThrottle]
    throttle_scope = "volunteer-applications"

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()
        if not user.is_staff:
            qs = qs.filter(help_request__is_deleted=False)
        if user.is_staff:
            return qs
        if getattr(user, "is_provider", False):
            return qs.filter(volunteer=user)
        # requester/admin: show applications for own help requests
        return qs.filter(help_request__created_by=user)

    def perform_create(self, serializer):
        user = self.request.user
        if not getattr(user, "is_provider", False):
            raise PermissionDenied("Doar voluntarii pot aplica.")
        help_request = serializer.validated_data["help_request"]
        if help_request.status not in [
            HelpRequest.Status.OPEN,
            HelpRequest.Status.IN_REVIEW,
        ]:
            raise PermissionDenied("Cererea nu mai acceptДѓ aplicaИ›ii.")
        serializer.save(volunteer=user)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def withdraw(self, request, pk=None):
        application = self.get_object()
        if application.help_request.is_locked and not request.user.is_staff:
            raise PermissionDenied("Cererea este blocat? de admin.")
        if application.volunteer != request.user:
            raise PermissionDenied("Nu po?i retrage aceast? aplica?ie.")
        if application.status == VolunteerApplication.Status.WITHDRAWN:
            return Response(self.get_serializer(application).data)
        if application.status != VolunteerApplication.Status.PENDING:
            raise ConflictError("AplicaИ›ia nu mai poate fi retrasДѓ.")
        application.status = VolunteerApplication.Status.WITHDRAWN
        application.save(update_fields=["status", "updated_at"])
        log_audit(
            request.user,
            "application_withdrawn",
            application,
            {"help_request": application.help_request_id},
            request=request,
        )
        return Response(self.get_serializer(application).data)


    @action(detail=True, methods=["post"])
    @transaction.atomic
    def accept(self, request, pk=None):
        application = self.get_queryset().select_for_update().get(pk=pk)
        help_request = application.help_request
        if help_request.is_locked and not request.user.is_staff:
            raise PermissionDenied("Cererea este blocata de admin.")
        if request.user not in [help_request.created_by] and not request.user.is_staff:
            raise PermissionDenied("Nu poti accepta aceasta aplicatie.")
        if application.status == VolunteerApplication.Status.ACCEPTED:
            ensure_help_request_conversation(help_request)
            return Response(self.get_serializer(application).data, status=status.HTTP_200_OK)
        if application.status != VolunteerApplication.Status.PENDING:
            raise ConflictError("Aplicatia nu mai poate fi acceptata.")
        if help_request.status not in [
            HelpRequest.Status.OPEN,
            HelpRequest.Status.IN_REVIEW,
        ]:
            raise ConflictError("Cererea nu poate fi acceptata din acest status.")
        VolunteerApplication.objects.filter(
            help_request=help_request,
            status=VolunteerApplication.Status.PENDING,
        ).exclude(pk=application.pk).update(
            status=VolunteerApplication.Status.REJECTED
        )
        application.status = VolunteerApplication.Status.ACCEPTED
        application.save(update_fields=["status", "updated_at"])
        help_request.status = HelpRequest.Status.MATCHED
        help_request.matched_volunteer = application.volunteer
        help_request.accepted_at = timezone.now()
        append_help_request_history(help_request, help_request.status, request.user)
        help_request.save(
            update_fields=["status", "matched_volunteer", "accepted_at", "updated_at", "status_history"]
        )
        conversation = ensure_help_request_conversation(help_request)
        notify_user(
            user=application.volunteer,
            notif_type=None,
            title="Aplicatie acceptata",
            body=help_request.title,
            link=f"/chat/{conversation.pk}/",
        )
        return Response(self.get_serializer(application).data)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def reject(self, request, pk=None):
        application = self.get_object()
        help_request = application.help_request
        if request.user not in [help_request.created_by] and not request.user.is_staff:
            raise PermissionDenied("Nu poИ›i respinge aceastДѓ aplicaИ›ie.")
        if application.status == VolunteerApplication.Status.REJECTED:
            return Response(self.get_serializer(application).data, status=status.HTTP_200_OK)
        if application.status != VolunteerApplication.Status.PENDING:
            raise ConflictError("AplicaИ›ia nu mai poate fi respinsДѓ.")
        application.status = VolunteerApplication.Status.REJECTED
        application.save(update_fields=["status", "updated_at"])
        log_audit(
            request.user,
            "application_rejected",
            application,
            {"help_request": help_request.pk},
            request=request,
        )
        return Response(self.get_serializer(application).data)


