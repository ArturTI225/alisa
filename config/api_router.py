from rest_framework import routers

from accounts.views import (
    AddressViewSet,
    FavoriteProviderViewSet,
    FavoriteServiceViewSet,
    NotificationViewSet,
    NotificationPreferenceViewSet,
    ReportViewSet,
    ProviderViewSet,
    VerificationViewSet,
)
from bookings.views import BookingViewSet
from chat.views import ChatMessageViewSet, ConversationViewSet
from reviews.views import ReviewViewSet
from services.views import ServiceCategoryViewSet, ServiceViewSet
from ads.views import AdViewSet, OfferViewSet
from bookings.views import HelpRequestViewSet, VolunteerApplicationViewSet

app_name = "api"
router = routers.DefaultRouter()
router.register("service-categories", ServiceCategoryViewSet)
router.register("services", ServiceViewSet)
router.register("bookings", BookingViewSet, basename="booking")
router.register("help-requests", HelpRequestViewSet, basename="help-request")
router.register(
    "volunteer-applications",
    VolunteerApplicationViewSet,
    basename="volunteer-application",
)
router.register("addresses", AddressViewSet, basename="address")
router.register("favorite-services", FavoriteServiceViewSet, basename="favorite-service")
router.register("favorite-providers", FavoriteProviderViewSet, basename="favorite-provider")
router.register("notifications", NotificationViewSet, basename="notification")
router.register(
    "notification-preferences",
    NotificationPreferenceViewSet,
    basename="notification-preference",
)
router.register("verifications", VerificationViewSet, basename="verification")
router.register("reports", ReportViewSet, basename="report")
router.register("chat-messages", ChatMessageViewSet, basename="chatmessage")
router.register("conversations", ConversationViewSet, basename="conversation")
router.register("reviews", ReviewViewSet, basename="review")
router.register("ads", AdViewSet, basename="ad")
router.register("offers", OfferViewSet, basename="offer")
router.register("providers", ProviderViewSet, basename="provider")

urlpatterns = router.urls
