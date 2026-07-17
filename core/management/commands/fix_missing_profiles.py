from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import Profile


class Command(BaseCommand):
    help = (
        "Finds any User account with no matching Profile row and creates one "
        "with safe defaults. Safe to run repeatedly (idempotent) — accounts "
        "that already have a Profile are left untouched."
    )

    def handle(self, *args, **options):
        fixed = []
        for user in User.objects.all():
            try:
                user.profile
            except Profile.DoesNotExist:
                Profile.objects.create(
                    user=user,
                    user_type='student',
                    onboarding_quiz_completed=True,
                    facilitator_profile_completed=True,
                )
                fixed.append(user.username)

        if fixed:
            self.stdout.write(self.style.SUCCESS(
                f"Created missing Profile for {len(fixed)} account(s): {', '.join(fixed)}"
            ))
        else:
            self.stdout.write(self.style.SUCCESS("No missing profiles found — nothing to do."))