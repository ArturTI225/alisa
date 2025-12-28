from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("services", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Ad",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=150)),
                ("description", models.TextField()),
                ("city", models.CharField(max_length=120)),
                ("district", models.CharField(blank=True, max_length=120)),
                ("budget_min", models.DecimalField(blank=True, decimal_places=2, max_digits=9, null=True)),
                ("budget_max", models.DecimalField(blank=True, decimal_places=2, max_digits=9, null=True)),
                ("status", models.CharField(choices=[("draft", "Draft"), ("open", "Deschis"), ("in_progress", "In curs"), ("completed", "Finalizat"), ("cancelled", "Anulat")], db_index=True, default="open", max_length=20)),
                ("is_urgent", models.BooleanField(db_index=True, default=False)),
                ("deadline", models.DateTimeField(blank=True, null=True)),
                ("preferred_date", models.DateField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("assigned_craftsman", models.ForeignKey(blank=True, limit_choices_to={"role": "provider"}, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="assigned_ads", to=settings.AUTH_USER_MODEL)),
                ("category", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="ads", to="services.servicecategory")),
                ("client", models.ForeignKey(limit_choices_to={"role": "client"}, on_delete=django.db.models.deletion.CASCADE, related_name="ads", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="Offer",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("message", models.TextField(blank=True)),
                ("proposed_price", models.DecimalField(blank=True, decimal_places=2, max_digits=9, null=True)),
                ("status", models.CharField(choices=[("pending", "In asteptare"), ("accepted", "Acceptat"), ("rejected", "Respins")], default="pending", max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("ad", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="offers", to="ads.ad")),
                ("craftsman", models.ForeignKey(limit_choices_to={"role": "provider"}, on_delete=django.db.models.deletion.CASCADE, related_name="offers", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-created_at"],
                "unique_together": {("ad", "craftsman")},
            },
        ),
        migrations.AddIndex(
            model_name="ad",
            index=models.Index(fields=["category", "city"], name="ads_ad_catego_07ddae_idx"),
        ),
        migrations.AddIndex(
            model_name="ad",
            index=models.Index(fields=["is_urgent", "created_at"], name="ads_ad_is_urge_2b89a5_idx"),
        ),
        migrations.AddIndex(
            model_name="offer",
            index=models.Index(fields=["ad", "craftsman"], name="ads_offer_ad__3c3ef1_idx"),
        ),
    ]
