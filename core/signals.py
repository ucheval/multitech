from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from core.models import Profile, Portfolio


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Creates a Profile for every new User.
    Passcode is generated inside Profile.save() — no need to do it here.
    Portfolio is created AFTER the profile so user_type is available.
    """
    if created:
        Profile.objects.create(user=instance)
        # Note: Portfolio is created in create_user_portfolio below,
        # which fires after Profile.save() sets user_type.


@receiver(post_save, sender=Profile)
def create_user_portfolio(sender, instance, created, **kwargs):
    """
    Creates a Portfolio whenever a new Profile is saved with user_type='student'.
    Fires after Profile is created so user_type is reliably set.
    """
    if created and instance.user_type == 'student':
        Portfolio.objects.get_or_create(
            user=instance.user,
            defaults={
                'name': instance.user.username,
                'bio': '',
                'github_url': '',
                'skills': '',
                'projects': '',
                'certificates': '',
                'is_public': False,
            }
        )


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()