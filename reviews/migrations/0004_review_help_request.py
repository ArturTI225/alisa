from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("bookings", "0021_remove_completioncertificate_pdf_url_and_more"),
        ("reviews", "0003_rename_reviews_rev_to_use_82d7f9_idx_reviews_rev_to_user_a8fe0b_idx"),
    ]

    operations = [
        migrations.AddField(
            model_name="review",
            name="help_request",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="reviews",
                to="bookings.helprequest",
            ),
        ),
    ]
