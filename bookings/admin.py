from django.contrib import admin

from .models import (
    Availability,
    AvailabilityException,
    Booking,
    BookingAttachment,
    BookingDispute,
    BookingEvent,
    CompletionCertificate,
    HelpRequest,
    HelpRequestAttachment,
    DisputeMessage,
    VolunteerApplication,
    RescheduleRequest,
)


@admin.register(Availability)
class AvailabilityAdmin(admin.ModelAdmin):
    list_display = ("provider", "weekday", "start_time", "end_time", "is_active")
    list_filter = ("weekday", "is_active")


@admin.register(AvailabilityException)
class AvailabilityExceptionAdmin(admin.ModelAdmin):
    list_display = ("provider", "date", "is_available")
    list_filter = ("is_available",)


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "client",
        "provider",
        "service",
        "scheduled_start",
        "is_urgent",
        "urgency_level",
        "status",
        "accepted_by",
        "accepted_at",
    )
    list_filter = ("status", "service", "is_urgent", "urgency_level")
    search_fields = ("client__username", "provider__username", "service__name")


@admin.register(RescheduleRequest)
class RescheduleRequestAdmin(admin.ModelAdmin):
    list_display = (
        "booking",
        "status",
        "proposed_start",
        "proposed_duration_minutes",
        "requested_by",
        "created_at",
    )
    list_filter = ("status",)
    search_fields = ("booking__id", "requested_by__username")


@admin.register(BookingEvent)
class BookingEventAdmin(admin.ModelAdmin):
    list_display = ("booking", "event_type", "actor", "created_at")
    list_filter = ("event_type",)
    search_fields = ("booking__id", "actor__username", "message")


@admin.register(BookingDispute)
class BookingDisputeAdmin(admin.ModelAdmin):
    list_display = ("booking", "status", "opened_by", "resolved_by", "created_at")
    list_filter = ("status",)
    search_fields = ("booking__id", "opened_by__username")


@admin.register(DisputeMessage)
class DisputeMessageAdmin(admin.ModelAdmin):
    list_display = ("dispute", "author", "created_at")
    search_fields = ("dispute__booking__id", "author__username", "text")


@admin.register(BookingAttachment)
class BookingAttachmentAdmin(admin.ModelAdmin):
    list_display = ("booking", "uploaded_by", "created_at")
    search_fields = ("booking__id", "uploaded_by__username", "note")


@admin.register(HelpRequest)
class HelpRequestAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "created_by",
        "category",
        "city",
        "urgency",
        "status",
        "matched_volunteer",
        "created_at",
    )
    list_filter = ("status", "urgency", "category", "city")
    search_fields = ("title", "description", "created_by__username")


@admin.register(HelpRequestAttachment)
class HelpRequestAttachmentAdmin(admin.ModelAdmin):
    list_display = ("help_request", "uploaded_by", "created_at")
    search_fields = ("help_request__id", "uploaded_by__username", "note")


@admin.register(VolunteerApplication)
class VolunteerApplicationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "help_request",
        "volunteer",
        "status",
        "created_at",
    )
    list_filter = ("status",)
    search_fields = ("help_request__id", "volunteer__username", "message")


@admin.register(CompletionCertificate)
class CompletionCertificateAdmin(admin.ModelAdmin):
    list_display = ("help_request", "volunteer", "issued_at")
    search_fields = ("help_request__id", "volunteer__username", "summary")
