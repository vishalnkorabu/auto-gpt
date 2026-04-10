from __future__ import annotations

from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import UserProfile


@receiver(post_save, sender=User)
def ensure_user_profile(sender, instance: User, created: bool, **_kwargs) -> None:
    if created:
        UserProfile.objects.create(user=instance, display_name=instance.username)
        return
    UserProfile.objects.get_or_create(user=instance, defaults={"display_name": instance.username})
