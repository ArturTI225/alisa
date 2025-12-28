from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("bookings", "0012_booking_urgency_fields"),
    ]

    operations = [
        migrations.AlterField(
            model_name="booking",
            name="client_confirmation_note",
            field=models.CharField(
                blank=True, default="", max_length=255
            ),
        ),
    ]
