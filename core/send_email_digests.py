from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.contrib.auth.models import User
from core.models import Notification
from django.utils import timezone
from datetime import timedelta

class Command(BaseCommand):
    help = 'Sends daily email digests to users'

    def handle(self, *args, **options):
        users = User.objects.all()
        for user in users:
            notifications = Notification.objects.filter(
                user=user,
                created_at__gte=timezone.now() - timedelta(days=1)
            )
            if notifications:
                subject = 'MultiTechSpace Daily Digest'
                message = 'Your recent notifications:\n\n'
                for n in notifications:
                    message += f"- {n.type.title()}: {n.message}\n"
                send_mail(
                    subject,
                    message,
                    'from@multitechspace.com',
                    [user.email],
                    fail_silently=True
                )
                notifications.update(read=True)
        self.stdout.write(self.style.SUCCESS('Email digests sent successfully'))