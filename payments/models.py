from django.conf import settings
from django.db import models


class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "În așteptare"
        SUCCEEDED = "succeeded", "Plată reușită"
        FAILED = "failed", "Eșuat"
        REFUNDED = "refunded", "Rambursat"

    booking = models.OneToOneField(
        "bookings.Booking",
        related_name="payment",
        on_delete=models.CASCADE,
    )
    provider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={"role": "provider"},
    )
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    currency = models.CharField(max_length=8, default="RON")
    platform_fee = models.DecimalField(
        max_digits=8, decimal_places=2, default=0
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    stripe_payment_intent = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Payment #{self.pk} - {self.amount} {self.currency}"
