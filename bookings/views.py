from datetime import timedelta
import csv

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import models
from django.db.models import Sum, Avg
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import generic, View
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.template.loader import render_to_string
from django.conf import settings
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.models import User
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
from .models import BookingDispute, RecurringBookingRule, BookingAttachment
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
)
from .utils import validate_provider_slot


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


class BookingCreateView(LoginRequiredMixin, generic.CreateView):
    form_class = BookingForm
    template_name = "bookings/create.html"
    success_url = reverse_lazy("bookings:list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.client = self.request.user
        if form.instance.service and not form.instance.price_estimated:
            form.instance.price_estimated = form.instance.service.base_price
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
            raise PermissionDenied("Nu ai acces la aceasta comanda.")
        if self.booking.status in [
            Booking.Status.CANCELED,
            Booking.Status.COMPLETED,
            Booking.Status.IN_PROGRESS,
            Booking.Status.DECLINED,
        ]:
            messages.error(request, "Comanda nu mai poate fi reprogramata.")
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
            raise PermissionDenied("Nu ai acces la aceasta comanda.")
        if booking.status in [
            Booking.Status.CANCELED,
            Booking.Status.COMPLETED,
            Booking.Status.DECLINED,
        ]:
            messages.info(request, "Comanda nu mai poate fi modificata.")
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
            raise PermissionDenied("Nu ai acces la aceasta comanda.")
        if self.booking.status in [
            Booking.Status.CANCELED,
            Booking.Status.COMPLETED,
            Booking.Status.IN_PROGRESS,
            Booking.Status.DECLINED,
        ]:
            messages.info(request, "Comanda nu mai poate fi anulata.")
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
            "Comanda a fost anulata.",
            actor=self.request.user,
            payload={"reason": self.booking.cancel_reason},
        )
        messages.success(self.request, "Comanda a fost anulata.")
        return redirect("bookings:detail", pk=self.booking.pk)


class BookingDeclineView(LoginRequiredMixin, generic.FormView):
    form_class = CancelBookingForm
    template_name = "bookings/decline.html"

    def dispatch(self, request, *args, **kwargs):
        self.booking = get_object_or_404(Booking, pk=kwargs["pk"])
        if not getattr(request.user, "is_provider", False):
            raise PermissionDenied("Doar prestatorul poate refuza.")
        if self.booking.provider not in [None, request.user]:
            raise PermissionDenied("Nu esti asignat la aceasta comanda.")
        if self.booking.status not in [
            Booking.Status.PENDING,
            Booking.Status.RESCHEDULE_REQUESTED,
        ]:
            messages.info(request, "Comanda nu mai poate fi refuzata.")
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
            "Comanda a fost refuzata de prestator.",
            actor=self.request.user,
            payload={"reason": self.booking.cancel_reason},
        )
        messages.success(self.request, "Ai refuzat comanda.")
        return redirect("bookings:detail", pk=self.booking.pk)


class BookingAcceptView(LoginRequiredMixin, generic.View):
    def post(self, request, pk):
        booking = get_object_or_404(Booking, pk=pk)
        if not getattr(request.user, "is_provider", False):
            raise PermissionDenied("Doar prestatorul poate accepta.")
        if booking.provider not in [None, request.user]:
            raise PermissionDenied("Nu esti asignat la aceasta comanda.")
        if booking.status not in [
            Booking.Status.PENDING,
            Booking.Status.RESCHEDULE_REQUESTED,
            Booking.Status.DISPUTED,
        ]:
            messages.info(request, "Comanda nu mai poate fi acceptata.")
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
            "Comanda a fost acceptata de prestator.",
            actor=request.user,
        )
        messages.success(request, "Comanda a fost acceptata.")
        return redirect("bookings:detail", pk=pk)


class BookingStartView(LoginRequiredMixin, generic.View):
    def post(self, request, pk):
        booking = get_object_or_404(Booking, pk=pk)
        if not getattr(request.user, "is_provider", False):
            raise PermissionDenied("Doar prestatorul poate incepe.")
        if booking.provider != request.user:
            raise PermissionDenied("Nu esti asignat la aceasta comanda.")
        if booking.status != Booking.Status.CONFIRMED:
            messages.info(request, "Comanda nu poate fi pornita in acest status.")
            return redirect("bookings:detail", pk=pk)
        booking.status = Booking.Status.IN_PROGRESS
        booking.started_at = timezone.now()
        booking.save(update_fields=["status", "started_at", "updated_at"])
        booking.add_event(
            BookingEvent.EventType.STATUS_CHANGED,
            "Prestatorul a marcat comanda ca In curs.",
            actor=request.user,
        )
        messages.success(request, "Comanda este in curs.")
        return redirect("bookings:detail", pk=pk)


class BookingCompleteView(LoginRequiredMixin, generic.FormView):
    form_class = CompleteBookingForm
    template_name = "bookings/complete.html"

    def dispatch(self, request, *args, **kwargs):
        self.booking = get_object_or_404(Booking, pk=kwargs["pk"])
        if not getattr(request.user, "is_provider", False):
            raise PermissionDenied("Doar prestatorul poate finaliza.")
        if self.booking.provider != request.user:
            raise PermissionDenied("Nu esti asignat la aceasta comanda.")
        if self.booking.status != Booking.Status.IN_PROGRESS:
            messages.info(request, "Comanda nu poate fi finalizata in acest status.")
            return redirect("bookings:detail", pk=self.booking.pk)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["booking"] = self.booking
        return ctx

    def form_valid(self, form):
        self.booking.status = Booking.Status.AWAITING_CLIENT
        self.booking.price_final = form.cleaned_data["price_final"]
        self.booking.extra_costs = form.cleaned_data.get("extra_costs") or {}
        self.booking.completed_at = timezone.now()
        self.booking.save(
            update_fields=[
                "status",
                "price_final",
                "extra_costs",
                "completed_at",
                "updated_at",
            ]
        )
        note = form.cleaned_data.get("note", "")
        self.booking.add_event(
            BookingEvent.EventType.STATUS_CHANGED,
            "Comanda a fost marcata ca finalizata de prestator (in asteptare confirmare client).",
            actor=self.request.user,
            payload={
                "price_final": str(self.booking.price_final),
                "extra_costs": self.booking.extra_costs,
                "note": note,
            },
        )
        messages.success(
            self.request,
            "Comanda a fost marcata ca finalizata. Asteptam confirmarea clientului.",
        )
        return redirect("bookings:detail", pk=self.booking.pk)


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
            raise PermissionDenied("Nu esti asignat la aceasta comanda.")
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
            "Prestatorul a rezolvat disputa.",
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
            raise PermissionDenied("Doar clientul poate replica comanda.")
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
            price_estimated=self.booking.price_estimated,
            status=Booking.Status.PENDING,
        )
        new_booking.add_event(
            BookingEvent.EventType.NOTE,
            "Comanda replicata dintr-o rezervare anterioara.",
            actor=self.request.user,
            payload={"source_booking": self.booking.id},
        )
        messages.success(self.request, "Comanda a fost replicata.")
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
                price_estimated=rule.service.base_price,
                status=Booking.Status.PENDING,
                recurring_rule=rule,
            )
            if rule.frequency == RecurringBookingRule.Frequency.WEEKLY:
                current_date += timezone.timedelta(days=7)
            elif rule.frequency == RecurringBookingRule.Frequency.BIWEEKLY:
                current_date += timezone.timedelta(days=14)
            else:
                current_date += timezone.timedelta(days=30)
        messages.success(self.request, "Seria recurentă a fost creată.")
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
            b.cancel_reason = "Seria recurentă a fost anulată."
            b.save(update_fields=["status", "cancel_reason", "updated_at"])
            b.add_event(
                BookingEvent.EventType.CANCELED,
                "Rezervare anulată deoarece seria a fost oprită.",
                actor=request.user,
            )
        messages.info(request, "Seria a fost oprită și rezervările viitoare anulate.")
        return redirect("bookings:recurring_list")


class RecurringRuleTriggerNextView(LoginRequiredMixin, View):
    def post(self, request, pk):
        rule = get_object_or_404(RecurringBookingRule, pk=pk, client=request.user)
        if not rule.is_active:
            messages.error(request, "Seria este dezactivată.")
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
            price_estimated=rule.service.base_price,
            status=Booking.Status.PENDING,
            recurring_rule=rule,
        )
        booking.add_event(
            BookingEvent.EventType.NOTE,
            "Rezervare generată manual din seria recurentă.",
            actor=request.user,
            payload={"rule_id": rule.id},
        )
        messages.success(request, "Am generat următoarea rezervare din serie.")
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
            messages.info(request, "Nu există rezervări viitoare de sărit.")
            return redirect("bookings:recurring_list")
        upcoming.status = Booking.Status.CANCELED
        upcoming.cancel_reason = "Sărit în seria recurentă."
        upcoming.save(update_fields=["status", "cancel_reason", "updated_at"])
        upcoming.add_event(
            BookingEvent.EventType.CANCELED,
            "Rezervare anulată (skip următoarea din serie).",
            actor=request.user,
        )
        messages.info(request, "Următoarea rezervare a fost sărită.")
        return redirect("bookings:recurring_list")


class ProviderDashboardView(LoginRequiredMixin, generic.TemplateView):
    template_name = "bookings/provider_dashboard.html"

    def dispatch(self, request, *args, **kwargs):
        if not getattr(request.user, "is_provider", False):
            raise PermissionDenied("Doar prestatorii au acces la acest dashboard.")
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
            "revenue_30d": recent.aggregate(total=Sum("price_final"))[
                "total"
            ]
            or 0,
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
            raise PermissionDenied("Doar prestatorii pot exporta veniturile.")
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
                    b.price_estimated,
                    b.price_final or "",
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
            raise PermissionDenied("Nu ai acces la aceasta comanda.")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        attachment = form.save(commit=False)
        attachment.booking = self.booking
        attachment.uploaded_by = self.request.user
        attachment.save()
        self.booking.add_event(
            BookingEvent.EventType.NOTE,
            "A fost adăugat un fișier la comandă.",
            actor=self.request.user,
            payload={"attachment_id": attachment.id, "note": attachment.note},
        )
        messages.success(self.request, "Fișier încărcat.")
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
            f"X-WR-CALNAME:Rezervari {user.username}",
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
            raise PermissionDenied("Nu ai acces la aceasta comanda.")

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
                {"detail": "Comanda nu mai poate fi reprogramata."},
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
                {"detail": "Comanda nu mai poate fi modificata."},
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
                {"detail": "Comanda nu mai poate fi anulata."},
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
            "Comanda a fost anulata.",
            actor=request.user,
            payload={"reason": booking.cancel_reason},
        )
        output = BookingSerializer(
            booking, context=self.get_serializer_context()
        )
        return Response(output.data)

    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        booking = self.get_object()
        user = request.user
        if not getattr(user, "is_provider", False):
            raise PermissionDenied("Doar prestatorul poate accepta.")
        if booking.provider not in [None, user]:
            raise PermissionDenied("Nu esti asignat la aceasta comanda.")
        if booking.status not in [
            Booking.Status.PENDING,
            Booking.Status.RESCHEDULE_REQUESTED,
        ]:
            return Response(
                {"detail": "Comanda nu mai poate fi acceptata."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        note = serializer.validated_data.get("note", "")

        booking.provider = booking.provider or user
        booking.status = Booking.Status.CONFIRMED
        booking.accepted_at = timezone.now()
        booking.accepted_by = user
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
            "Comanda a fost acceptata de prestator.",
            actor=user,
            payload={"note": note} if note else {},
        )
        return Response(
            BookingSerializer(booking, context=self.get_serializer_context()).data
        )

    @action(detail=True, methods=["post"])
    def decline(self, request, pk=None):
        booking = self.get_object()
        user = request.user
        if not getattr(user, "is_provider", False):
            raise PermissionDenied("Doar prestatorul poate refuza.")
        if booking.provider not in [None, user]:
            raise PermissionDenied("Nu esti asignat la aceasta comanda.")
        if booking.status not in [
            Booking.Status.PENDING,
            Booking.Status.RESCHEDULE_REQUESTED,
        ]:
            return Response(
                {"detail": "Comanda nu mai poate fi refuzata."},
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
            "Comanda a fost refuzata de prestator.",
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
            raise PermissionDenied("Doar prestatorul poate incepe.")
        if booking.provider != user:
            raise PermissionDenied("Nu esti asignat la aceasta comanda.")
        if booking.status != Booking.Status.CONFIRMED:
            return Response(
                {"detail": "Comanda nu poate fi pornita."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        booking.status = Booking.Status.IN_PROGRESS
        booking.started_at = timezone.now()
        booking.save(update_fields=["status", "started_at", "updated_at"])
        booking.add_event(
            BookingEvent.EventType.STATUS_CHANGED,
            "Prestatorul a marcat comanda ca In curs.",
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
            raise PermissionDenied("Doar prestatorul poate finaliza.")
        if booking.provider != user:
            raise PermissionDenied("Nu esti asignat la aceasta comanda.")
        if booking.status != Booking.Status.IN_PROGRESS:
            return Response(
                {"detail": "Comanda nu poate fi finalizata in acest status."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        booking.status = Booking.Status.COMPLETED
        booking.price_final = serializer.validated_data["price_final"]
        booking.extra_costs = serializer.validated_data.get("extra_costs") or {}
        booking.completed_at = timezone.now()
        booking.save(
            update_fields=[
                "status",
                "price_final",
                "extra_costs",
                "completed_at",
                "updated_at",
            ]
        )
        note = serializer.validated_data.get("note", "")
        booking.add_event(
            BookingEvent.EventType.STATUS_CHANGED,
            "Comanda a fost finalizata.",
            actor=user,
            payload={
                "price_final": str(booking.price_final),
                "extra_costs": booking.extra_costs,
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
            raise PermissionDenied("Doar clientul poate replica rezervarea.")
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
            price_estimated=booking.price_estimated,
            status=Booking.Status.PENDING,
        )
        new_booking.add_event(
            BookingEvent.EventType.NOTE,
            "Comanda replicata dintr-o rezervare anterioara.",
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
                price_estimated=rule.service.base_price,
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
            raise PermissionDenied("Doar clientul poate confirma.")
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
            "Clientul a confirmat finalizarea.",
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
            raise PermissionDenied("Doar clientul poate marca disputa.")
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
            "Clientul a deschis o disputa.",
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
