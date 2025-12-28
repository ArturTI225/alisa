from django.conf import settings
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver


def review_upload_path(instance, filename: str) -> str:
    return f"reviews/{instance.id}/{filename}"


def update_user_rating(user):
    qs = Review.objects.filter(to_user=user)
    agg = qs.aggregate(avg=models.Avg("rating"), cnt=models.Count("id"))
    user.rating_avg = agg["avg"] or 0
    user.rating_count = agg["cnt"] or 0
    user.save(update_fields=["rating_avg", "rating_count"])


class Review(models.Model):
    booking = models.ForeignKey(
        "bookings.Booking",
        related_name="reviews",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    ad = models.ForeignKey(
        "ads.Ad",
        related_name="reviews",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    from_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reviews_authored",
    )
    to_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reviews_received",
    )
    rating = models.PositiveSmallIntegerField(default=5)
    comment = models.TextField(blank=True)
    photo = models.ImageField(
        upload_to=review_upload_path, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["to_user", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"Review #{self.pk} {self.rating}/5"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        update_user_rating(self.to_user)


@receiver(post_delete, sender=Review)
def update_rating_on_delete(sender, instance, **kwargs):
    update_user_rating(instance.to_user)
