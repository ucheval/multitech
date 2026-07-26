from django.apps import AppConfig
import os
import sys


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self):
        import core.signals

        # Don't run during migrations or collectstatic
        if any(cmd in sys.argv for cmd in [
            "makemigrations",
            "migrate",
            "collectstatic",
        ]):
            return

        if not os.environ.get("RENDER"):
            return

        from django.contrib.auth.models import User
        from django.db import OperationalError, ProgrammingError

        username = os.environ.get("ADMIN_USER")
        email = os.environ.get("ADMIN_EMAIL")
        password = os.environ.get("ADMIN_PASS")

        if not (username and email and password):
            return

        try:
            if not User.objects.filter(username=username).exists():
                User.objects.create_superuser(username, email, password)
                print(f"--- Superuser {username} created! ---")
        except (OperationalError, ProgrammingError):
            # Database isn't ready yet (e.g. migrations haven't run).
            pass