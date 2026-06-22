from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django_otp.admin import OTPAdminSite

# Force the standard admin site to use OTP
admin.site.__class__ = OTPAdminSite

urlpatterns = [
    # 1. The official Django backend management (requires OTP)
    path('ogatechinovadmin/', admin.site.urls),
    
    # 2. Your core application, including your custom /admin_dashboard/ view
    path('', include('core.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)