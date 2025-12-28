from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ("ads", "0001_initial"),
        ("bookings", "0013_booking_confirmation_defaults"),
        ("reviews", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name="review",
            name="booking",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="reviews",
                to="bookings.booking",
            ),
        ),
        migrations.RenameField(
            model_name="review",
            old_name="author",
            new_name="from_user",
        ),
        migrations.AddField(
            model_name="review",
            name="ad",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="reviews",
                to="ads.ad",
            ),
        ),
        migrations.AddField(
            model_name="review",
            name="to_user",
            field=models.ForeignKey(
                default=1,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="reviews_received",
                to=settings.AUTH_USER_MODEL,
            ),
            preserve_default=False,
        ),
        migrations.AddIndex(
            model_name="review",
            index=models.Index(fields=["to_user", "created_at"], name="reviews_rev_to_use_82d7f9_idx"),
        ),
        migrations.AlterField(
            model_name="review",
            name="from_user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="reviews_authored",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
