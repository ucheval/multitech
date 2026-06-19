from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django_otp.admin import OTPAdminSite

# Force the admin site to use OTP
admin.site.__class__ = OTPAdminSite

urlpatterns = [
    # Your custom secured admin URL
    path('ogatechinovadmin/', admin.site.urls),
    path('', include('core.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)