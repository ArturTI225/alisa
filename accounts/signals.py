from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import ClientProfile, ProviderProfile, User


@receiver(post_save, sender=User)
def create_profiles_on_signup(sender, instance: User, created: bool, **kwargs):
    if not created:
        if instance.role == User.Roles.PROVIDER and not hasattr(
            instance, "provider_profile"
        ):
            ProviderProfile.objects.create(user=instance)
        return

    ClientProfile.objects.create(user=instance)
    if instance.role == User.Roles.PROVIDER:
        ProviderProfile.objects.create(user=instance)
