from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("bookings", "0011_bookingattachment"),
    ]

    operations = [
        migrations.AddField(
            model_name="booking",
            name="is_urgent",
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AddField(
            model_name="booking",
            name="urgency_level",
            field=models.CharField(
                choices=[
                    ("normal", "Normal"),
                    ("high", "Ridicat"),
                    ("critical", "Critic"),
                ],
                default="normal",
                max_length=20,
            ),
        ),
        migrations.AddIndex(
            model_name="booking",
            index=models.Index(
                fields=["is_urgent", "created_at"], name="bookings_b_is_urge_f5ba80_idx"
            ),
        ),
    ]
