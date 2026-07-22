import os

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Creates the default admin account"

    def handle(self, *args, **kwargs):
        username = os.getenv("ADMIN_USER")
        email = os.getenv("ADMIN_EMAIL")
        password = os.getenv("ADMIN_PASS")

        if not (username and email and password):
            self.stdout.write(
                self.style.WARNING(
                    "ADMIN_USER, ADMIN_EMAIL or ADMIN_PASS not set."
                )
            )
            return

        if User.objects.filter(username=username).exists():
            self.stdout.write(
                self.style.SUCCESS("Admin user already exists.")
            )
            return

        User.objects.create_superuser(
            username=username,
            email=email,
            password=password,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Superuser '{username}' created successfully."
            )
        )