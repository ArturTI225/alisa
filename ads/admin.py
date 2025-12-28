from django.contrib import admin

from .models import Ad, Offer


@admin.register(Ad)
class AdAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "client",
        "category",
        "city",
        "is_urgent",
        "status",
        "assigned_craftsman",
        "created_at",
    )
    list_filter = ("status", "is_urgent", "category", "city")
    search_fields = ("title", "description", "city", "client__username")


@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "ad",
        "craftsman",
        "status",
        "proposed_price",
        "created_at",
    )
    list_filter = ("status",)
    search_fields = ("ad__title", "craftsman__username")
