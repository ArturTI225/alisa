from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .utils import log_audit
from .models import (
    Address,
    Badge,
    ClientProfile,
    FavoriteProvider,
    FavoriteService,
    ProviderProfile,
    ProviderMonthlyStat,
    User,
    Notification,
    NotificationPreference,
    Report,
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

    def save_model(self, request, obj, form, change):
        prev_blocked = None
        if change and obj.pk:
            prev_blocked = User.objects.filter(pk=obj.pk).values_list("is_blocked", flat=True).first()
        super().save_model(request, obj, form, change)
        if prev_blocked is not None and prev_blocked != obj.is_blocked:
            action = "user_blocked" if obj.is_blocked else "user_unblocked"
            log_audit(request.user, action, obj, request=request)


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

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("id", "reporter", "reported_user", "help_request", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("reporter__username", "reported_user__username", "reason")


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "booking_updates",
        "disputes",
        "recurring",
        "chat_messages",
        "in_app_sound",
    )


@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display = ("name", "criteria", "created_at")
    search_fields = ("name", "criteria")


@admin.register(ProviderMonthlyStat)
class ProviderMonthlyStatAdmin(admin.ModelAdmin):
    list_display = ("provider", "year", "month", "completed_requests", "total_hours")
    list_filter = ("year", "month")
    search_fields = ("provider__username",)
