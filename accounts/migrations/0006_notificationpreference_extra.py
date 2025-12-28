from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0005_user_rating_and_notification_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="notificationpreference",
            name="bids",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="notificationpreference",
            name="chat_messages",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="notificationpreference",
            name="reviews",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="notificationpreference",
            name="urgent_ads",
            field=models.BooleanField(default=True),
        ),
    ]
