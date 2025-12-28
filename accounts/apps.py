from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"

    def ready(self) -> None:
        # Import signals to auto-create profiles.
        from . import signals  # noqa: WPS433, F401
        return super().ready()
