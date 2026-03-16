from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import models, transaction
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views import View, generic

from accounts.models import Notification
from accounts.utils import log_audit, notify_user, scan_uploaded_file
from ads.models import Ad
from bookings.models import (
    Booking,
    HelpRequest,
    HelpRequestAttachment,
    VolunteerApplication,
)
from bookings.utils import ensure_help_request_conversation
from chat.models import Conversation
from reviews.models import Review
from services.models import Service, ServiceCategory

from .forms import ClientHelpRequestForm, WorkerRequestSearchForm


def _append_help_request_history(help_request: HelpRequest, new_status: str, actor):
    history = help_request.status_history or []
    history.append(
        {
            "status": new_status,
            "timestamp": timezone.now().isoformat(),
            "actor": getattr(actor, "id", None),
        }
    )
    help_request.status_history = history


def _validate_uploaded_media(uploaded_file):
    max_size = getattr(settings, "MAX_UPLOAD_SIZE", 0)
    if max_size and uploaded_file.size > max_size:
        raise ValidationError("Fisierul este prea mare.")
    allowed = getattr(settings, "ALLOWED_UPLOAD_MIME_TYPES", [])
    content_type = getattr(uploaded_file, "content_type", "")
    if allowed and content_type and content_type not in allowed:
        raise ValidationError("Tipul de fisier nu este permis.")
    if scan_uploaded_file(uploaded_file) is False:
        raise ValidationError("Fisier respins la scanarea antivirus.")


class HomePageView(generic.TemplateView):
    template_name = "pages/home.html"

    def get_template_names(self):
        user = self.request.user
        if user.is_authenticated and getattr(user, "is_client", False):
            return ["pages/home_client.html"]
        if user.is_authenticated and getattr(user, "is_provider", False):
            return ["pages/home_worker.html"]
        return [self.template_name]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        if user.is_authenticated and getattr(user, "is_client", False):
            return self._client_context(ctx)
        if user.is_authenticated and getattr(user, "is_provider", False):
            return self._worker_context(ctx)
        return self._public_context(ctx)

    def _public_context(self, ctx):
        from accounts.models import User

        ctx["categories"] = ServiceCategory.objects.filter(is_active=True)[:6]
        ctx["featured_services"] = Service.objects.filter(is_active=True)[:6]
        ctx["top_providers"] = (
            User.objects.filter(role="provider", is_verified=True)
            .select_related("provider_profile")
            .prefetch_related("provider_profile__skills")
            .order_by("-rating_avg", "-rating_count")[:4]
        )
        ctx["urgent_ads"] = (
            Ad.objects.filter(is_urgent=True)
            .select_related("category", "client")
            .order_by("-created_at")[:6]
        )
        ctx["recent_reviews"] = (
            Review.objects.select_related("from_user", "to_user")
            .order_by("-created_at")[:3]
        )
        return ctx

    def _client_context(self, ctx):
        user = self.request.user
        ctx["request_form"] = ClientHelpRequestForm(user=user)
        ctx["categories"] = ServiceCategory.objects.filter(is_active=True)
        app_qs = VolunteerApplication.objects.select_related("volunteer").order_by(
            "-created_at"
        )
        requests_qs = (
            HelpRequest.objects.filter(created_by=user, is_deleted=False)
            .select_related("category", "matched_volunteer")
            .prefetch_related(models.Prefetch("applications", queryset=app_qs))
            .order_by("-created_at")
        )
        requests_list = list(requests_qs)
        conversation_map = dict(
            Conversation.objects.filter(help_request__in=requests_list)
            .values_list("help_request_id", "id")
        )
        for help_request in requests_list:
            help_request.chat_conversation_id = conversation_map.get(help_request.id)
        ctx["client_requests"] = requests_list
        return ctx

    def _worker_context(self, ctx):
        user = self.request.user
        search_form = WorkerRequestSearchForm(self.request.GET or None)

        my_client_requests = (
            HelpRequest.objects.filter(
                created_by=user,
                is_deleted=False,
            )
            .select_related("category", "matched_volunteer")
            .order_by("-updated_at")
        )

        open_requests = (
            HelpRequest.objects.filter(
                is_deleted=False,
                status__in=[HelpRequest.Status.OPEN, HelpRequest.Status.IN_REVIEW],
            )
            .exclude(created_by=user)
            .select_related("category", "created_by")
            .order_by("-created_at")
        )
        open_bookings = (
            Booking.objects.filter(
                status__in=[
                    Booking.Status.PENDING,
                    Booking.Status.RESCHEDULE_REQUESTED,
                ]
            )
            .filter(models.Q(provider__isnull=True) | models.Q(provider=user))
            .exclude(client=user)
            .select_related("service", "service__category", "client", "address")
            .order_by("-created_at")
        )
        if search_form.is_valid():
            category = search_form.cleaned_data.get("category")
            urgency = search_form.cleaned_data.get("urgency")
            city = (search_form.cleaned_data.get("city") or "").strip()
            q = (search_form.cleaned_data.get("q") or "").strip()
            if category:
                open_requests = open_requests.filter(category=category)
                open_bookings = open_bookings.filter(service__category=category)
            if urgency:
                open_requests = open_requests.filter(urgency=urgency)
            if city:
                open_requests = open_requests.filter(city__icontains=city)
                open_bookings = open_bookings.filter(address__city__icontains=city)
            if q:
                open_requests = open_requests.filter(
                    models.Q(title__icontains=q)
                    | models.Q(description__icontains=q)
                )
                open_bookings = open_bookings.filter(
                    models.Q(description__icontains=q)
                    | models.Q(service__name__icontains=q)
                    | models.Q(client__username__icontains=q)
                )

        applied_ids = set(
            VolunteerApplication.objects.filter(
                volunteer=user, help_request__in=open_requests
            ).values_list("help_request_id", flat=True)
        )

        assigned_requests = (
            HelpRequest.objects.filter(
                is_deleted=False,
                matched_volunteer=user,
            )
            .select_related("category", "created_by")
            .order_by("-updated_at")
        )
        applied_requests = (
            HelpRequest.objects.filter(
                is_deleted=False,
                applications__volunteer=user,
            )
            .exclude(matched_volunteer=user)
            .select_related("category", "created_by")
            .distinct()
            .order_by("-updated_at")
        )

        assigned_list = list(assigned_requests)
        my_client_list = list(my_client_requests[:20])
        conversation_map = dict(
            Conversation.objects.filter(
                help_request__in=assigned_list + my_client_list
            )
            .values_list("help_request_id", "id")
        )
        for help_request in assigned_list:
            help_request.chat_conversation_id = conversation_map.get(help_request.id)
        for help_request in my_client_list:
            help_request.chat_conversation_id = conversation_map.get(help_request.id)

        worker_skill_category_ids = []
        profile = getattr(user, "provider_profile", None)
        if profile:
            worker_skill_category_ids = list(
                profile.skills.values_list("category_id", flat=True).distinct()
            )

        ctx["search_form"] = search_form
        ctx["open_bookings"] = open_bookings[:40]
        ctx["open_requests"] = open_requests[:40]
        ctx["applied_request_ids"] = applied_ids
        ctx["assigned_requests"] = assigned_list
        ctx["applied_requests"] = applied_requests
        ctx["my_client_requests"] = my_client_list
        ctx["worker_skill_category_ids"] = worker_skill_category_ids
        return ctx


class ClientHelpRequestCreateView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        if not getattr(request.user, "is_client", False):
            raise PermissionDenied("Doar clientii pot crea cereri.")

        form = ClientHelpRequestForm(request.POST, request.FILES, user=request.user)
        if not form.is_valid():
            messages.error(request, "Date invalide in formular.")
            return redirect("pages:home")

        urgency = form.cleaned_data["urgency"]
        if urgency == HelpRequest.Urgency.HIGH and not request.user.is_verified:
            messages.error(
                request,
                "Pentru urgenta ridicata este necesar cont verificat.",
            )
            return redirect("pages:home")

        description = form.cleaned_data["description"].strip()
        title = description[:80]
        if len(description) > 80:
            title = f"{title}..."

        history = [
            {
                "status": HelpRequest.Status.OPEN,
                "timestamp": timezone.now().isoformat(),
                "actor": request.user.id,
            }
        ]

        help_request = HelpRequest.objects.create(
            created_by=request.user,
            title=title,
            description=description,
            category=form.cleaned_data["category"],
            city=form.cleaned_data.get("city", "").strip(),
            region=form.cleaned_data.get("region", "").strip(),
            urgency=urgency,
            status=HelpRequest.Status.OPEN,
            status_history=history,
        )

        try:
            for uploaded_file in request.FILES.getlist("media"):
                _validate_uploaded_media(uploaded_file)
                HelpRequestAttachment.objects.create(
                    help_request=help_request,
                    uploaded_by=request.user,
                    file=uploaded_file,
                )
        except ValidationError as exc:
            help_request.delete()
            messages.error(request, "; ".join(exc.messages))
            return redirect("pages:home")

        notify_user(
            user=request.user,
            notif_type=Notification.Type.GENERAL,
            title="Cerere creata",
            body=help_request.title,
            link="/",
        )
        log_audit(request.user, "help_request_created_ui", help_request, request=request)
        messages.success(request, "Cererea a fost publicata.")
        return redirect("pages:home")


class WorkerApplyHelpRequestView(LoginRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        if not getattr(request.user, "is_provider", False):
            raise PermissionDenied("Doar workerii pot aplica.")

        help_request = get_object_or_404(
            HelpRequest.objects.select_related("created_by"),
            pk=pk,
            is_deleted=False,
        )
        if help_request.created_by_id == request.user.id:
            messages.error(request, "Nu poti aplica la propria cerere.")
            return redirect(request.META.get("HTTP_REFERER") or "pages:home")
        if help_request.status not in [
            HelpRequest.Status.OPEN,
            HelpRequest.Status.IN_REVIEW,
        ]:
            messages.error(request, "Cererea nu mai accepta aplicatii.")
            return redirect(request.META.get("HTTP_REFERER") or "pages:home")

        message_text = (request.POST.get("message") or "").strip()
        application, created = VolunteerApplication.objects.get_or_create(
            help_request=help_request,
            volunteer=request.user,
            defaults={"message": message_text},
        )
        if created:
            notify_user(
                user=help_request.created_by,
                notif_type=Notification.Type.NEW_BID,
                title="Aplicatie noua",
                body=f"{request.user.display_name} a aplicat la cererea ta.",
                link="/",
            )
            log_audit(
                request.user,
                "application_created_ui",
                application,
                {"help_request": help_request.id},
                request=request,
            )
            messages.success(request, "Ai aplicat la lucrare.")
        else:
            messages.info(request, "Ai aplicat deja la aceasta cerere.")
        return redirect(request.META.get("HTTP_REFERER") or "pages:home")


class ClientAcceptApplicationView(LoginRequiredMixin, View):
    @transaction.atomic
    def post(self, request, pk, *args, **kwargs):
        application = get_object_or_404(
            VolunteerApplication.objects.select_related(
                "help_request", "help_request__created_by", "volunteer"
            ).select_for_update(),
            pk=pk,
        )
        help_request = application.help_request
        if request.user not in [help_request.created_by] and not request.user.is_staff:
            raise PermissionDenied("Nu poti accepta aceasta aplicatie.")
        if help_request.is_locked and not request.user.is_staff:
            messages.error(request, "Cererea este blocata de admin.")
            return redirect("pages:home")
        if application.status == VolunteerApplication.Status.ACCEPTED:
            conversation = ensure_help_request_conversation(help_request)
            messages.info(request, "Aplicatia era deja acceptata.")
            return redirect("chat:conversation_detail", pk=conversation.pk)
        if application.status != VolunteerApplication.Status.PENDING:
            messages.error(request, "Aplicatia nu mai poate fi acceptata.")
            return redirect("pages:home")
        if help_request.status not in [
            HelpRequest.Status.OPEN,
            HelpRequest.Status.IN_REVIEW,
        ]:
            messages.error(request, "Cererea nu poate fi acceptata din acest status.")
            return redirect("pages:home")

        VolunteerApplication.objects.filter(
            help_request=help_request,
            status=VolunteerApplication.Status.PENDING,
        ).exclude(pk=application.pk).update(status=VolunteerApplication.Status.REJECTED)

        application.status = VolunteerApplication.Status.ACCEPTED
        application.save(update_fields=["status", "updated_at"])
        help_request.status = HelpRequest.Status.MATCHED
        help_request.matched_volunteer = application.volunteer
        help_request.accepted_at = timezone.now()
        _append_help_request_history(help_request, help_request.status, request.user)
        help_request.save(
            update_fields=[
                "status",
                "matched_volunteer",
                "accepted_at",
                "updated_at",
                "status_history",
            ]
        )

        conversation = ensure_help_request_conversation(help_request)
        notify_user(
            user=application.volunteer,
            notif_type=Notification.Type.BID_ACCEPTED,
            title="Aplicatie acceptata",
            body=help_request.title,
            link=f"/chat/{conversation.pk}/",
        )
        log_audit(
            request.user,
            "application_accepted_ui",
            application,
            {"help_request": help_request.id, "conversation": conversation.id},
            request=request,
        )
        messages.success(request, "Worker-ul a fost acceptat. Discutati in chat.")
        return redirect("chat:conversation_detail", pk=conversation.pk)


class WorkerStartHelpRequestView(LoginRequiredMixin, View):
    @transaction.atomic
    def post(self, request, pk, *args, **kwargs):
        if not getattr(request.user, "is_provider", False):
            raise PermissionDenied("Doar workerii pot porni lucrarea.")

        help_request = get_object_or_404(
            HelpRequest.objects.select_related("created_by"),
            pk=pk,
            matched_volunteer=request.user,
            is_deleted=False,
        )
        if help_request.is_locked and not request.user.is_staff:
            messages.error(request, "Cererea este blocata de admin.")
            return redirect("pages:home")
        if help_request.status == HelpRequest.Status.IN_PROGRESS:
            conversation = ensure_help_request_conversation(help_request)
            messages.info(request, "Lucrarea este deja in desfasurare.")
            return redirect("chat:conversation_detail", pk=conversation.pk)
        if help_request.status != HelpRequest.Status.MATCHED:
            messages.error(request, "Lucrarea nu poate fi pornita in acest status.")
            return redirect("pages:home")

        help_request.status = HelpRequest.Status.IN_PROGRESS
        help_request.started_at = help_request.started_at or timezone.now()
        _append_help_request_history(help_request, help_request.status, request.user)
        help_request.save(
            update_fields=["status", "started_at", "updated_at", "status_history"]
        )

        conversation = ensure_help_request_conversation(help_request)
        notify_user(
            user=help_request.created_by,
            notif_type=Notification.Type.GENERAL,
            title="Lucrarea a inceput",
            body=help_request.title,
            link=f"/chat/{conversation.pk}/",
        )
        log_audit(
            request.user,
            "help_request_started_ui",
            help_request,
            {"conversation": conversation.id},
            request=request,
        )
        messages.success(request, "Status actualizat: In work.")
        return redirect("chat:conversation_detail", pk=conversation.pk)


class HowItWorksView(generic.TemplateView):
    template_name = "pages/how_it_works.html"


class FAQView(generic.TemplateView):
    template_name = "pages/faq.html"


class ProviderApplyView(generic.TemplateView):
    template_name = "pages/provider_apply.html"
