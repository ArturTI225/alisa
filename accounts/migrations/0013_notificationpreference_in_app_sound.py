from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0012_providermonthlystat"),
    ]

    operations = [
        migrations.AddField(
            model_name="notificationpreference",
            name="in_app_sound",
            field=models.BooleanField(default=False),
        ),
    ]
