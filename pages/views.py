from django.views import generic

from ads.models import Ad
from bookings.models import Booking
from reviews.models import Review
from services.models import Service, ServiceCategory


class HomePageView(generic.TemplateView):
    template_name = "pages/home.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["categories"] = ServiceCategory.objects.filter(is_active=True)[:6]
        ctx["featured_services"] = Service.objects.filter(is_active=True)[:6]
        from accounts.models import User

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
        ctx["recent_bookings"] = (
            Booking.objects.select_related("service", "client", "provider")
            .order_by("-created_at")[:4]
        )
        ctx["recent_reviews"] = (
            Review.objects.select_related("from_user", "to_user")
            .order_by("-created_at")[:3]
        )
        return ctx


class HowItWorksView(generic.TemplateView):
    template_name = "pages/how_it_works.html"


class FAQView(generic.TemplateView):
    template_name = "pages/faq.html"


class ProviderApplyView(generic.TemplateView):
    template_name = "pages/provider_apply.html"
