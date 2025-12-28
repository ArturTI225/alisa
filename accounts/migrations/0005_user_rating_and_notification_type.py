from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0004_notificationpreference"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="rating_avg",
            field=models.DecimalField(blank=True, decimal_places=2, default=0, max_digits=4),
        ),
        migrations.AddField(
            model_name="user",
            name="rating_count",
            field=models.PositiveIntegerField(blank=True, default=0),
        ),
        migrations.AddField(
            model_name="notification",
            name="type",
            field=models.CharField(
                choices=[
                    ("general", "General"),
                    ("new_message", "New message"),
                    ("new_bid", "New bid"),
                    ("bid_accepted", "Bid accepted"),
                    ("urgent_ad_nearby", "Urgent ad nearby"),
                    ("review", "Review"),
                ],
                default="general",
                max_length=50,
            ),
        ),
    ]
