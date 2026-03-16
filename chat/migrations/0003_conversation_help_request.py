from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("bookings", "0021_remove_completioncertificate_pdf_url_and_more"),
        ("chat", "0002_conversation_chatmessage_conversation"),
    ]

    operations = [
        migrations.AddField(
            model_name="conversation",
            name="help_request",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="conversations",
                to="bookings.helprequest",
            ),
        ),
    ]
