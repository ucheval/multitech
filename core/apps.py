from django.apps import AppConfig
import os

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        import core.signals
        
        if os.environ.get('RENDER'):
            from django.contrib.auth.models import User
            
            # These values come from your Render Environment tab
            username = os.environ.get('ADMIN_USER')
            email = os.environ.get('ADMIN_EMAIL')
            password = os.environ.get('ADMIN_PASS')
            
            if username and email and password:
                if not User.objects.filter(username=username).exists():
                    User.objects.create_superuser(username, email, password)
                    print(f"--- Superuser {username} created! ---")