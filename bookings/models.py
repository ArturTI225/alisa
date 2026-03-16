from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone
from accounts.models import Notification, NotificationPreference
from services.models import ServiceCategory


class Availability(models.Model):
    class Weekday(models.IntegerChoices):
        MONDAY = 1, "Luni"
        TUESDAY = 2, "Marti"
        WEDNESDAY = 3, "Miercuri"
        THURSDAY = 4, "Joi"
        FRIDAY = 5, "Vineri"
        SATURDAY = 6, "Sambata"
        SUNDAY = 7, "Duminica"

    provider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="availabilities",
        limit_choices_to={"role": "provider"},
    )
    weekday = models.PositiveSmallIntegerField(choices=Weekday.choices)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("provider", "weekday", "start_time", "end_time")
        ordering = ["provider", "weekday", "start_time"]

    def __str__(self) -> str:
        return f"{self.provider} - {self.get_weekday_display()}"


class AvailabilityException(models.Model):
    provider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="availability_exceptions",
        limit_choices_to={"role": "provider"},
    )
    date = models.DateField()
    is_available = models.BooleanField(default=True)
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        unique_together = ("provider", "date")
        ordering = ["date"]

    def __str__(self) -> str:
        return f"{self.provider} - {self.date}"


class Booking(models.Model):
    class UrgencyLevel(models.TextChoices):
        NORMAL = "normal", "Normal"
        HIGH = "high", "Ridicat"
        CRITICAL = "critical", "Critic"

    class Status(models.TextChoices):
        PENDING = "pending", "In asteptare"
        CONFIRMED = "confirmed", "Confirmata"
        IN_PROGRESS = "in_progress", "In curs"
        AWAITING_CLIENT = "awaiting_client", "In asteptare confirmare client"
        COMPLETED = "completed", "Finalizata"
        CANCELED = "canceled", "Anulata"
        DECLINED = "declined", "Respinsa"
        DISPUTED = "disputed", "In disputa"
        RESCHEDULE_REQUESTED = (
            "reschedule_requested",
            "Reprogramare solicitata",
        )

    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="client_bookings",
        on_delete=models.CASCADE,
    )
    provider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="provider_bookings",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={"role": "provider"},
    )
    service = models.ForeignKey(
        "services.Service",
        related_name="bookings",
        on_delete=models.CASCADE,
    )
    address = models.ForeignKey(
        "accounts.Address",
        related_name="bookings",
        on_delete=models.PROTECT,
    )
    description = models.TextField()
    scheduled_start = models.DateTimeField(default=timezone.now)
    duration_minutes = models.PositiveIntegerField(default=60)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    client_confirmed_at = models.DateTimeField(null=True, blank=True)
    client_confirmation_note = models.CharField(
        max_length=255, blank=True, default=""
    )
    is_urgent = models.BooleanField(default=False, db_index=True)
    urgency_level = models.CharField(
        max_length=20,
        choices=UrgencyLevel.choices,
        default=UrgencyLevel.NORMAL,
    )
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    accepted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="accepted_bookings",
    )
    cancel_reason = models.CharField(max_length=255, blank=True)
    canceled_at = models.DateTimeField(null=True, blank=True)
    canceled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="canceled_bookings",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    recurring_rule = models.ForeignKey(
        "bookings.RecurringBookingRule",
        null=True,
        blank=True,
        related_name="bookings",
        on_delete=models.SET_NULL,
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["is_urgent", "created_at"]),
        ]

    @property
    def scheduled_end(self):
        return self.scheduled_start + timedelta(minutes=self.duration_minutes)

    def add_event(self, event_type: str, message: str, actor=None, payload=None):
        event = self.events.create(
            event_type=event_type,
            message=message,
            actor=actor,
            payload=payload or {},
        )
        # basic notifications for participants (except actor)
        recipients = [self.client]
        if self.provider and self.provider not in recipients:
            recipients.append(self.provider)
        for user in recipients:
            if actor and user == actor:
                continue
            pref = getattr(user, "notification_pref", None)
            if pref:
                if event_type in [
                    BookingEvent.EventType.RESCHEDULE_REQUESTED,
                    BookingEvent.EventType.RESCHEDULE_APPROVED,
                    BookingEvent.EventType.RESCHEDULE_DECLINED,
                    BookingEvent.EventType.STATUS_CHANGED,
                    BookingEvent.EventType.ACCEPTED,
                    BookingEvent.EventType.CANCELED,
                    BookingEvent.EventType.DECLINED,
                ] and not pref.booking_updates:
                    continue
                if event_type in [
                    BookingEvent.EventType.DISPUTE_OPENED,
                    BookingEvent.EventType.DISPUTE_RESOLVED,
                ] and not pref.disputes:
                    continue
            Notification.objects.create(
                user=user,
                title=f"Booking #{self.pk}: {event.get_event_type_display()}",
                body=message,
                link=f"/bookings/{self.pk}/",
        )
        return event

    def __str__(self) -> str:
        return f"Booking #{self.pk} - {self.service}"


class RescheduleRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "In asteptare"
        APPROVED = "approved", "Aprobata"
        DECLINED = "declined", "Respinsa"

    booking = models.ForeignKey(
        Booking,
        related_name="reschedule_requests",
        on_delete=models.CASCADE,
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reschedule_requests",
    )
    proposed_start = models.DateTimeField()
    proposed_duration_minutes = models.PositiveIntegerField(default=60)
    previous_status = models.CharField(max_length=20, choices=Booking.Status.choices)
    note = models.CharField(max_length=255, blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    responded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reschedule_responses",
    )
    responded_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Reschedule #{self.pk} for booking {self.booking_id}"


class BookingEvent(models.Model):
    class EventType(models.TextChoices):
        STATUS_CHANGED = "status_changed", "Schimbare status"
        RESCHEDULE_REQUESTED = "reschedule_requested", "Reprogramare propusa"
        RESCHEDULE_APPROVED = "reschedule_approved", "Reprogramare aprobata"
        RESCHEDULE_DECLINED = "reschedule_declined", "Reprogramare respinsa"
        ACCEPTED = "accepted", "Acceptata"
        DECLINED = "declined", "Respinsa"
        CANCELED = "canceled", "Anulare"
        DISPUTE_OPENED = "dispute_opened", "Disputa deschisa"
        DISPUTE_RESOLVED = "dispute_resolved", "Disputa rezolvata"
        NOTE = "note", "Nota"

    booking = models.ForeignKey(
        Booking, related_name="events", on_delete=models.CASCADE
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="booking_events",
    )
    event_type = models.CharField(max_length=50, choices=EventType.choices)
    message = models.TextField()
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"{self.get_event_type_display()} ({self.booking_id})"


class BookingDispute(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Deschisa"
        RESOLVED = "resolved", "Rezolvata"

    booking = models.OneToOneField(
        Booking, related_name="dispute", on_delete=models.CASCADE
    )
    opened_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="opened_disputes",
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_disputes",
    )
    reason = models.CharField(max_length=255, blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.OPEN
    )
    resolution_note = models.CharField(max_length=255, blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resolved_disputes",
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    escalated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Disputa booking {self.booking_id} ({self.status})"


class RecurringBookingRule(models.Model):
    class Frequency(models.TextChoices):
        WEEKLY = "weekly", "Saptamanal"
        BIWEEKLY = "biweekly", "Bilunar"
        MONTHLY = "monthly", "Lunar"

    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="recurring_rules",
        on_delete=models.CASCADE,
    )
    provider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="recurring_rules_as_provider",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={"role": "provider"},
    )
    service = models.ForeignKey(
        "services.Service",
        related_name="recurring_rules",
        on_delete=models.CASCADE,
    )
    address = models.ForeignKey(
        "accounts.Address",
        related_name="recurring_rules",
        on_delete=models.CASCADE,
    )
    description = models.TextField(blank=True)
    start_date = models.DateField()
    start_time = models.TimeField()
    duration_minutes = models.PositiveIntegerField(default=60)
    frequency = models.CharField(
        max_length=20, choices=Frequency.choices, default=Frequency.WEEKLY
    )
    occurrences = models.PositiveIntegerField(default=4)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Recurring {self.service} ({self.frequency})"


def booking_attachment_path(instance, filename: str) -> str:
    return f"bookings/{instance.booking_id}/attachments/{filename}"


class BookingAttachment(models.Model):
    booking = models.ForeignKey(
        Booking, related_name="attachments", on_delete=models.CASCADE
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="booking_attachments",
    )
    file = models.FileField(upload_to=booking_attachment_path)
    note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Attachment {self.pk} for booking {self.booking_id}"


class HelpRequest(models.Model):
    class Urgency(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        IN_REVIEW = "in_review", "In review"
        MATCHED = "matched", "Matched"
        IN_PROGRESS = "in_progress", "In progress"
        DONE = "done", "Done"
        CANCELLED = "cancelled", "Cancelled"

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="help_requests",
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.ForeignKey(
        ServiceCategory,
        on_delete=models.PROTECT,
        related_name="help_requests",
    )
    city = models.CharField(max_length=120, blank=True)
    region = models.CharField(max_length=120, blank=True)
    urgency = models.CharField(
        max_length=10, choices=Urgency.choices, default=Urgency.MEDIUM
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.OPEN, db_index=True
    )
    matched_volunteer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="matched_requests",
        limit_choices_to={"role": "provider"},
    )
    accepted_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    canceled_at = models.DateTimeField(null=True, blank=True)
    cancel_reason = models.CharField(max_length=255, blank=True)
    status_history = models.JSONField(default=list, blank=True)
    is_locked = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "urgency", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"HelpRequest #{self.pk} - {self.title}"


def help_attachment_path(instance, filename: str) -> str:
    return f"help_requests/{instance.help_request_id}/{filename}"


class HelpRequestAttachment(models.Model):
    help_request = models.ForeignKey(
        HelpRequest, related_name="attachments", on_delete=models.CASCADE
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="help_request_attachments",
    )
    file = models.FileField(upload_to=help_attachment_path)
    note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Attachment {self.pk} for help_request {self.help_request_id}"


class CompletionCertificate(models.Model):
    help_request = models.OneToOneField(
        HelpRequest, on_delete=models.CASCADE, related_name="completion_certificate"
    )
    volunteer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="completion_certificates",
    )
    issued_at = models.DateTimeField(auto_now_add=True)
    pdf = models.FileField(upload_to="certificates/", blank=True, null=True)
    summary = models.TextField(blank=True)

    class Meta:
        ordering = ["-issued_at"]


class VolunteerApplication(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"
        WITHDRAWN = "withdrawn", "Withdrawn"

    help_request = models.ForeignKey(
        HelpRequest, related_name="applications", on_delete=models.CASCADE
    )
    volunteer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="volunteer_applications",
        limit_choices_to={"role": "provider"},
    )
    message = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["help_request"],
                condition=models.Q(status="accepted"),
                name="unique_accepted_application_per_help_request",
            )
        ]
        unique_together = ("help_request", "volunteer")

    def __str__(self) -> str:
        return f"Application {self.pk} for help_request {self.help_request_id}"


def dispute_upload_path(instance, filename: str) -> str:
    return f"disputes/{instance.dispute_id}/{filename}"


class DisputeMessage(models.Model):
    dispute = models.ForeignKey(
        BookingDispute, related_name="messages", on_delete=models.CASCADE
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="dispute_messages",
    )
    text = models.TextField()
    attachment = models.FileField(
        upload_to=dispute_upload_path, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"Dispute msg {self.pk} for {self.dispute_id}"
