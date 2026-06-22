from django.apps import AppConfig
import os

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        # Import your signals to keep application features working
        import core.signals

        # Auto-create superuser only on the live Render server
        if os.environ.get('RENDER'):
            from django.contrib.auth.models import User
            
            # --- UPDATE THESE VALUES ---
            username = 'myadmin'
            email = 'admin@techinovaedu.com'
            password = 'YourSecurePassword123'
            # ---------------------------
            
            try:
                if not User.objects.filter(username=username).exists():
                    User.objects.create_superuser(username, email, password)
                    print(f"--- Superuser {username} created successfully! ---")
            except Exception as e:
                print(f"--- Could not create superuser: {e} ---")