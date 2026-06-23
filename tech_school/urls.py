from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django_otp.admin import OTPAdminSite

# Force the standard admin site to require OTP for all logins
admin.site.__class__ = OTPAdminSite

urlpatterns = [
    # Django admin — protected by OTP via OTPAdminSite above
    path('admin/', admin.site.urls),

    # Core app — includes all your custom views and /admin_dashboard/
    path('', include('core.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)