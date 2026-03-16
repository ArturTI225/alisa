from django.conf import settings
from django.db import models


class Ad(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        OPEN = "open", "Deschis"
        IN_PROGRESS = "in_progress", "In curs"
        COMPLETED = "completed", "Finalizat"
        CANCELLED = "cancelled", "Anulat"

    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ads",
        limit_choices_to={"role": "client"},
    )
    title = models.CharField(max_length=150)
    description = models.TextField()
    category = models.ForeignKey(
        "services.ServiceCategory",
        on_delete=models.PROTECT,
        related_name="ads",
    )
    city = models.CharField(max_length=120)
    district = models.CharField(max_length=120, blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.OPEN, db_index=True
    )
    is_urgent = models.BooleanField(default=False, db_index=True)
    deadline = models.DateTimeField(null=True, blank=True)
    preferred_date = models.DateField(null=True, blank=True)
    assigned_craftsman = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_ads",
        limit_choices_to={"role": "provider"},
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["category", "city"]),
            models.Index(fields=["is_urgent", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.get_status_display()})"


class Offer(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "In asteptare"
        ACCEPTED = "accepted", "Acceptat"
        REJECTED = "rejected", "Respins"

    ad = models.ForeignKey(
        Ad, on_delete=models.CASCADE, related_name="offers"
    )
    craftsman = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="offers",
        limit_choices_to={"role": "provider"},
    )
    message = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = [("ad", "craftsman")]
        indexes = [
            models.Index(fields=["ad", "craftsman"]),
        ]

    def __str__(self) -> str:
        return f"Offer {self.pk} on {self.ad_id}"
