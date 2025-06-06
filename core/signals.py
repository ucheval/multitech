from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from core.models import Profile, Portfolio
import random
import string

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        profile = Profile.objects.create(user=instance)
        # Generate unique 4-digit passcode
        while True:
            passcode = ''.join(random.choices(string.digits, k=4))
            if not Profile.objects.filter(student_passcode=passcode).exists():
                profile.student_passcode = passcode
                profile.save()
                break
        # Create portfolio for students
        if profile.user_type == 'student':
            Portfolio.objects.create(
                user=instance,
                name=instance.username,
                bio='',
                github_url='',
                skills='',
                projects='',
                certificates='',
                is_public=False
            )

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()