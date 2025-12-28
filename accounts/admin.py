from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import (
    Address,
    ClientProfile,
    FavoriteProvider,
    FavoriteService,
    ProviderProfile,
    User,
    Notification,
    NotificationPreference,
)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    fieldsets = BaseUserAdmin.fieldsets + (
        (
            _("Role & contact"),
            {"fields": ("role", "phone", "city", "is_verified")},
        ),
    )
    list_display = (
        "username",
        "email",
        "role",
        "is_verified",
        "is_staff",
    )
    list_filter = BaseUserAdmin.list_filter + ("role", "is_verified")


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ("label", "user", "city", "is_default", "created_at")
    list_filter = ("city", "is_default")
    search_fields = ("label", "city", "street", "user__username")


@admin.register(ClientProfile)
class ClientProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "created_at")


@admin.register(ProviderProfile)
class ProviderProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "city",
        "verification_status",
        "hourly_rate",
        "experience_years",
    )
    list_filter = ("verification_status", "city")
    search_fields = ("user__username", "user__email", "city")
    filter_horizontal = ("skills",)


@admin.register(FavoriteService)
class FavoriteServiceAdmin(admin.ModelAdmin):
    list_display = ("user", "service", "created_at")
    search_fields = ("user__username", "service__name")


@admin.register(FavoriteProvider)
class FavoriteProviderAdmin(admin.ModelAdmin):
    list_display = ("user", "provider", "created_at")
    search_fields = ("user__username", "provider__username")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "title", "is_read", "created_at")
    list_filter = ("is_read",)
    search_fields = ("user__username", "title")


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ("user", "booking_updates", "disputes", "marketing", "recurring")
