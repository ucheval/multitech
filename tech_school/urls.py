from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Django admin (KEEP IT CLEAN - no custom OTP override here)
    path('admin/', admin.site.urls),

    # Your application (custom auth + 2FA + dashboard system)
    path('', include('core.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)