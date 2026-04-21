from django.db import migrations
from django.utils.text import slugify


CATEGORIES = [
    (
        "Cumparaturi",
        "Ajutor cu cumparaturi, ridicare produse si livrare usoara.",
        "shopping-bag",
        [
            ("Cumparaturi alimentare", 60),
            ("Ridicare medicamente", 45),
            ("Livrare pachet mic", 45),
        ],
    ),
    (
        "Transport si insotire",
        "Insotire la programari, institutii sau drumuri scurte.",
        "route",
        [
            ("Insotire la medic", 90),
            ("Insotire la institutii", 120),
            ("Drum scurt in oras", 60),
        ],
    ),
    (
        "Ingrijire persoane",
        "Sprijin non-medical pentru persoane in varsta sau cu mobilitate redusa.",
        "heart-handshake",
        [
            ("Vizita de sprijin", 60),
            ("Ajutor cu rutina zilnica", 90),
            ("Companie si conversatie", 60),
        ],
    ),
    (
        "Reparatii usoare",
        "Interventii simple pentru casa, fara lucrari complexe.",
        "hammer",
        [
            ("Montat raft", 60),
            ("Reglat usa sau balama", 45),
            ("Asamblat mobila usoara", 120),
        ],
    ),
    (
        "Suport digital",
        "Ajutor cu telefonul, calculatorul si conturile online.",
        "monitor",
        [
            ("Configurare telefon", 45),
            ("Ajutor cu email si conturi", 60),
            ("Instalare aplicatii utile", 45),
        ],
    ),
    (
        "Acte si formulare",
        "Sprijin pentru completarea formularelor si pregatirea documentelor.",
        "file-text",
        [
            ("Completare formular", 60),
            ("Pregatire dosar", 90),
            ("Scanare si trimitere documente", 45),
        ],
    ),
    (
        "Gradina si curte",
        "Ajutor usor in jurul casei si al curtii.",
        "leaf",
        [
            ("Curatat curte", 120),
            ("Udat plante", 45),
            ("Strans frunze", 90),
        ],
    ),
    (
        "Mutare usoara",
        "Mutat sau organizat obiecte usoare in locuinta.",
        "box",
        [
            ("Mutat obiecte usoare", 90),
            ("Organizat debara", 90),
            ("Pregatit cutii", 60),
        ],
    ),
    (
        "Mese si bucatarie",
        "Sprijin pentru pregatiri simple in bucatarie.",
        "utensils",
        [
            ("Pregatit masa simpla", 60),
            ("Organizat frigider", 45),
            ("Spalat vase dupa eveniment", 60),
        ],
    ),
    (
        "Urgente casnice",
        "Ajutor rapid pentru situatii casnice care nu necesita servicii de urgenta.",
        "alert-circle",
        [
            ("Verificare scurgere minora", 45),
            ("Ajutor dupa pana de curent", 45),
            ("Deblocare acces in locuinta", 60),
        ],
    ),
]


def seed_more_categories(apps, schema_editor):
    ServiceCategory = apps.get_model("services", "ServiceCategory")
    Service = apps.get_model("services", "Service")

    for name, description, icon, services in CATEGORIES:
        category, created = ServiceCategory.objects.get_or_create(
            slug=slugify(name),
            defaults={
                "name": name,
                "description": description,
                "icon": icon,
                "is_active": True,
            },
        )
        if not created:
            changed = False
            if category.description != description:
                category.description = description
                changed = True
            if category.icon != icon:
                category.icon = icon
                changed = True
            if not category.is_active:
                category.is_active = True
                changed = True
            if changed:
                category.save(update_fields=["description", "icon", "is_active", "updated_at"])

        for service_name, duration in services:
            Service.objects.get_or_create(
                category=category,
                slug=slugify(service_name),
                defaults={
                    "name": service_name,
                    "description": "",
                    "duration_estimate_minutes": duration,
                    "is_active": True,
                },
            )


def unseed_more_categories(apps, schema_editor):
    ServiceCategory = apps.get_model("services", "ServiceCategory")
    slugs = [slugify(item[0]) for item in CATEGORIES]
    ServiceCategory.objects.filter(slug__in=slugs).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("services", "0002_remove_service_base_price_remove_service_price_type"),
    ]

    operations = [
        migrations.RunPython(seed_more_categories, unseed_more_categories),
    ]
