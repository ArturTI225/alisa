from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import generic, View
from django.utils import timezone
from rest_framework import permissions, viewsets, filters

from bookings.models import Booking
from services.models import Service
from reviews.models import Review
from .forms import SignupForm, NotificationPreferenceForm
from .models import (
    Address,
    AuditLog,
    FavoriteProvider,
    FavoriteService,
    Notification,
    NotificationPreference,
    Report,
    User,
    Verification,
)
from .utils import notify_user, log_audit
from .serializers import (
    AddressSerializer,
    FavoriteProviderSerializer,
    FavoriteServiceSerializer,
    NotificationSerializer,
    NotificationPreferenceSerializer,
    VerificationSerializer,
    ReportSerializer,
    ProviderProfileSerializer,
)


class SignupView(generic.FormView):
    template_name = "accounts/signup.html"
    form_class = SignupForm
    success_url = reverse_lazy("pages:home")

    def form_valid(self, form):
        user = form.save()
        login(
            self.request,
            user,
            backend="django.contrib.auth.backends.ModelBackend",
        )
        return super().form_valid(form)


class ProfileView(LoginRequiredMixin, generic.TemplateView):
    template_name = "accounts/profile.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        addresses = user.addresses.order_by("-is_default", "label")
        favorite_services = FavoriteService.objects.filter(user=user).select_related(
            "service", "service__category"
        )
        favorite_providers = FavoriteProvider.objects.filter(
            user=user
        ).select_related("provider")
        all_bookings = Booking.objects.filter(Q(client=user) | Q(provider=user))
        active_statuses = [
            Booking.Status.PENDING,
            Booking.Status.CONFIRMED,
            Booking.Status.IN_PROGRESS,
            Booking.Status.AWAITING_CLIENT,
            Booking.Status.RESCHEDULE_REQUESTED,
            Booking.Status.DISPUTED,
        ]
        provider_profile = getattr(user, "provider_profile", None)
        if provider_profile is not None:
            provider_profile = (
                provider_profile.__class__.objects.filter(pk=provider_profile.pk)
                .prefetch_related("skills", "badges")
                .first()
            )

        ctx["addresses"] = addresses
        ctx["favorite_services"] = favorite_services
        ctx["favorite_providers"] = favorite_providers
        ctx["total_favorites_count"] = favorite_services.count() + favorite_providers.count()
        ctx["client_bookings_count"] = Booking.objects.filter(client=user).count()
        ctx["provider_bookings_count"] = (
            Booking.objects.filter(provider=user).count() if user.is_provider else 0
        )
        ctx["active_bookings_count"] = all_bookings.filter(
            status__in=active_statuses
        ).count()
        ctx["completed_bookings_count"] = all_bookings.filter(
            status=Booking.Status.COMPLETED
        ).count()
        ctx["unread_notifications_count"] = Notification.objects.filter(
            user=user, is_read=False
        ).count()
        ctx["profile"] = provider_profile
        return ctx


class ProviderDetailView(generic.DetailView):
    model = User
    template_name = "accounts/provider_detail.html"
    context_object_name = "provider"

    def get_queryset(self):
        return (
            User.objects.filter(role=User.Roles.PROVIDER, is_verified=True)
            .select_related("provider_profile")
            .prefetch_related("provider_profile__skills")
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        ctx["is_favorite"] = False
        if user.is_authenticated:
            ctx["is_favorite"] = FavoriteProvider.objects.filter(
                user=user, provider=self.object
            ).exists()
        reviews = Review.objects.filter(to_user=self.object).select_related(
            "from_user", "booking", "ad"
        )
        ctx["reviews"] = reviews[:6]
        ctx["avg_rating"] = float(self.object.rating_avg or 0)
        ctx["reviews_count"] = self.object.rating_count
        ctx["completed_jobs"] = Booking.objects.filter(
            provider=self.object, status=Booking.Status.COMPLETED
        ).count()
        return ctx


class ProviderViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ProviderProfileSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [filters.OrderingFilter, filters.SearchFilter]
    search_fields = ["user__username", "bio", "skills__name", "city"]
    ordering_fields = ["user__rating_avg", "experience_years"]

    def get_queryset(self):
        qs = (
            User.objects.filter(role=User.Roles.PROVIDER, is_verified=True)
            .select_related("provider_profile")
            .prefetch_related("provider_profile__skills")
        )
        city = self.request.query_params.get("city")
        if city:
            qs = qs.filter(city__iexact=city)
        min_rating = self.request.query_params.get("min_rating")
        if min_rating:
            qs = qs.filter(rating_avg__gte=min_rating)
        skill = self.request.query_params.get("service")
        if skill:
            qs = qs.filter(provider_profile__skills=skill)
        return qs


class AddressViewSet(viewsets.ModelViewSet):
    serializer_class = AddressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)


class FavoriteServiceViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = FavoriteServiceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return FavoriteService.objects.filter(user=self.request.user).select_related(
            "service"
        )


class FavoriteProviderViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = FavoriteProviderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return FavoriteProvider.objects.filter(
            user=self.request.user
        ).select_related("provider")


class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    def perform_update(self, serializer):
        if serializer.instance.user != self.request.user:
            raise PermissionDenied("Nu ai acces.")
        serializer.save()


class NotificationPreferenceViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationPreferenceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return NotificationPreference.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def perform_update(self, serializer):
        if serializer.instance.user != self.request.user:
            raise PermissionDenied("Nu ai acces.")
        serializer.save()


class ReportViewSet(viewsets.ModelViewSet):
    serializer_class = ReportSerializer
    permission_classes = [permissions.IsAuthenticated]
    throttle_scope = "reports"

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Report.objects.select_related("reporter", "reported_user", "help_request")
        return Report.objects.filter(reporter=user).select_related("reported_user", "help_request")

    def perform_create(self, serializer):
        serializer.save(reporter=self.request.user)
        reported_user = serializer.instance.reported_user
        if reported_user:
            recent_count = Report.objects.filter(
                reported_user=reported_user, created_at__gte=timezone.now() - timezone.timedelta(days=30)
            ).count()
            if recent_count >= 3:
                admin = User.objects.filter(is_staff=True).order_by("id").first()
                if admin:
                    notify_user(
                        admin,
                        notif_type=None,
                        title="Alertă abuz",
                        body=f"Utilizator raportat frecvent: {reported_user.username}",
                    )

    def perform_update(self, serializer):
        if not self.request.user.is_staff:
            raise permissions.PermissionDenied("Doar adminul poate edita raportul.")
        serializer.save()


class FavoriteToggleView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        kind = kwargs.get("kind")
        pk = kwargs.get("pk")
        if kind == "service":
            service = get_object_or_404(Service, pk=pk)
            fav, created = FavoriteService.objects.get_or_create(
                user=request.user, service=service
            )
            if not created:
                fav.delete()
                messages.info(request, "Serviciu scos din favorite.")
            else:
                messages.success(request, "Serviciu adăugat la favorite.")
            return redirect(request.META.get("HTTP_REFERER") or "services:list")
        if kind == "provider":
            provider = get_object_or_404(User, pk=pk, role=User.Roles.PROVIDER)
            fav, created = FavoriteProvider.objects.get_or_create(
                user=request.user, provider=provider
            )
            if not created:
                fav.delete()
                messages.info(request, "Prestator scos din favorite.")
            else:
                messages.success(request, "Prestator adăugat la favorite.")
            return redirect(request.META.get("HTTP_REFERER") or "accounts:provider_detail", pk=pk)
        messages.error(request, "Tip necunoscut.")
        return redirect("accounts:profile")


class FavoritesView(LoginRequiredMixin, generic.TemplateView):
    template_name = "accounts/favorites.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["favorite_services"] = FavoriteService.objects.filter(
            user=self.request.user
        ).select_related("service")
        ctx["favorite_providers"] = FavoriteProvider.objects.filter(
            user=self.request.user
        ).select_related("provider")
        return ctx


class NotificationListView(LoginRequiredMixin, generic.TemplateView):
    template_name = "accounts/notifications.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["notifications"] = Notification.objects.filter(
            user=self.request.user
        ).order_by("-created_at")[:100]
        return ctx


class NotificationMarkAllView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        Notification.objects.filter(user=request.user, is_read=False).update(
            is_read=True
        )
        messages.success(request, "Notificările au fost marcate ca citite.")
        return redirect(request.META.get("HTTP_REFERER") or "accounts:notifications")


class NotificationPreferenceView(LoginRequiredMixin, generic.FormView):
    template_name = "accounts/notification_preferences.html"
    form_class = NotificationPreferenceForm
    success_url = reverse_lazy("accounts:notifications")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        pref, _ = NotificationPreference.objects.get_or_create(user=self.request.user)
        kwargs["instance"] = pref
        return kwargs

    def form_valid(self, form):
        form.save()
        messages.success(self.request, "Preferințe salvate.")
        return super().form_valid(form)


# --- API: Verification ---


class VerificationViewSet(viewsets.ModelViewSet):
    serializer_class = VerificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Verification.objects.select_related("user", "checked_by")
        return Verification.objects.filter(user=user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user, status=Verification.Status.PENDING)

    def perform_update(self, serializer):
        if not self.request.user.is_staff:
            raise permissions.PermissionDenied("Doar adminul poate aproba/verifica.")
        instance = serializer.save(checked_by=self.request.user)
        log_audit(
            self.request.user,
            "verification_decision",
            instance,
            {"status": instance.status},
            request=self.request,
        )
