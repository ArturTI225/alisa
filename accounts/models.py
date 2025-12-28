from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    class Roles(models.TextChoices):
        CLIENT = "client", _("Client")
        PROVIDER = "provider", _("Provider")
        ADMIN = "admin", _("Admin")

    role = models.CharField(
        max_length=20, choices=Roles.choices, default=Roles.CLIENT
    )
    phone = models.CharField(max_length=32, blank=True)
    city = models.CharField(max_length=128, blank=True)
    is_verified = models.BooleanField(default=False)
    rating_avg = models.DecimalField(
        max_digits=4, decimal_places=2, default=0, blank=True
    )
    rating_count = models.PositiveIntegerField(default=0, blank=True)

    @property
    def is_client(self) -> bool:
        return self.role == self.Roles.CLIENT

    @property
    def is_provider(self) -> bool:
        return self.role == self.Roles.PROVIDER

    @property
    def display_name(self) -> str:
        return self.get_full_name() or self.username


class Address(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="addresses"
    )
    label = models.CharField(max_length=64, default="Acasa")
    city = models.CharField(max_length=128)
    street = models.CharField(max_length=255)
    details = models.CharField(max_length=255, blank=True)
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Addresses"

    def __str__(self) -> str:
        return f"{self.label} - {self.city}"


class ClientProfile(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="client_profile"
    )
    preferences = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Client {self.user.display_name}"


class ProviderProfile(models.Model):
    class VerificationStatus(models.TextChoices):
        PENDING = "pending", _("Pending")
        VERIFIED = "verified", _("Verified")
        REJECTED = "rejected", _("Rejected")

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="provider_profile"
    )
    bio = models.TextField(blank=True)
    skills = models.ManyToManyField(
        "services.Service", related_name="providers", blank=True
    )
    hourly_rate = models.DecimalField(
        max_digits=7, decimal_places=2, null=True, blank=True
    )
    city = models.CharField(max_length=128, blank=True)
    experience_years = models.PositiveIntegerField(default=0)
    verification_status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING,
    )
    verification_note = models.TextField(blank=True)
    availability_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Provider {self.user.display_name}"


class FavoriteService(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="favorite_services"
    )
    service = models.ForeignKey(
        "services.Service", on_delete=models.CASCADE, related_name="favorited_by"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "service")
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.user} -> {self.service}"


class FavoriteProvider(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="favorite_providers"
    )
    provider = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="favorited_as_provider",
        limit_choices_to={"role": User.Roles.PROVIDER},
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "provider")
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.user} -> {self.provider}"


class Notification(models.Model):
    class Type(models.TextChoices):
        GENERAL = "general", "General"
        NEW_MESSAGE = "new_message", "New message"
        NEW_BID = "new_bid", "New bid"
        BID_ACCEPTED = "bid_accepted", "Bid accepted"
        URGENT_AD_NEARBY = "urgent_ad_nearby", "Urgent ad nearby"
        REVIEW = "review", "Review"

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="notifications"
    )
    type = models.CharField(
        max_length=50, choices=Type.choices, default=Type.GENERAL
    )
    title = models.CharField(max_length=200)
    body = models.TextField(blank=True)
    link = models.CharField(max_length=255, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Notif {self.user}: {self.title}"


class NotificationPreference(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="notification_pref"
    )
    booking_updates = models.BooleanField(default=True)
    disputes = models.BooleanField(default=True)
    marketing = models.BooleanField(default=False)
    recurring = models.BooleanField(default=True)
    chat_messages = models.BooleanField(default=True)
    bids = models.BooleanField(default=True)
    urgent_ads = models.BooleanField(default=True)
    reviews = models.BooleanField(default=True)

    def __str__(self) -> str:
        return f"Prefs for {self.user}"
