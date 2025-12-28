from django.contrib.auth import views as auth_views
from django.urls import path

from .views import (
    FavoriteToggleView,
    FavoritesView,
    ProfileView,
    ProviderDetailView,
    SignupView,
    NotificationListView,
    NotificationMarkAllView,
    NotificationPreferenceView,
)

app_name = "accounts"

urlpatterns = [
    path("signup/", SignupView.as_view(), name="signup"),
    path("login/", auth_views.LoginView.as_view(template_name="accounts/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("profile/", ProfileView.as_view(), name="profile"),
    path("favorites/", FavoritesView.as_view(), name="favorites"),
    path("notifications/", NotificationListView.as_view(), name="notifications"),
    path(
        "notifications/mark-all/",
        NotificationMarkAllView.as_view(),
        name="notifications_mark_all",
    ),
    path(
        "notifications/preferences/",
        NotificationPreferenceView.as_view(),
        name="notification_preferences",
    ),
    path(
        "favorites/<str:kind>/<int:pk>/toggle/",
        FavoriteToggleView.as_view(),
        name="favorite_toggle",
    ),
    path("providers/<int:pk>/", ProviderDetailView.as_view(), name="provider_detail"),
]
