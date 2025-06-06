"""
Django settings for tech_school project.
"""
from pathlib import Path
import base64
import os

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent

# Security settings
SECRET_KEY = 'django-insecure-0#b5q2k7z!x2j#v^9#v@5k!q#h!v#z#v#z#v#z#v#z#v#z#v'  # Change in production
DEBUG = True  # Set to False in production
ALLOWED_HOSTS = ['127.0.0.1', 'localhost']  # Add domain in production
CSRF_TRUSTED_ORIGINS = ['http://127.0.0.1:8000', 'https://yourdomain.com']  # Update in production

# Session security
SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_AGE = 1800  # 30 minutes
CSRF_COOKIE_SECURE = False  # Set to True in production
SECURE_SSL_REDIRECT = False  # Set to True in production
SECURE_HSTS_SECONDS = 0  # Set to 31536000 in production
SECURE_HSTS_INCLUDE_SUBDOMAINS = False  # Set to True in production
SECURE_HSTS_PRELOAD = False  # Set to True in production

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_otp',
    'django_otp.plugins.otp_totp',
    'phonenumber_field',
    'core',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django_otp.middleware.OTPMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'tech_school.middleware.LogLongURIMiddleware',
]

ROOT_URLCONF = 'tech_school.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'tech_school.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static and media files
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Email settings
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'updatevlogandpress@gmail.com'
EMAIL_HOST_PASSWORD = 'uefz bqof ekna xtsf'  # Consider environment variables in production
DEFAULT_FROM_EMAIL = 'MultiTechSpace <updatevlogandpress@gmail.com>'

# Authentication settings
LOGIN_URL = '/user_login/'

# Logo setup
logo_path = os.path.join(BASE_DIR, 'static', 'images', 'logo.png')
if os.path.exists(logo_path):
    with open(logo_path, 'rb') as f:
        LOGO_BASE64 = base64.b64encode(f.read()).decode('utf-8')
else:
    LOGO_BASE64 = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/wcAAgAB/1z9rAAAAABJRU5ErkJggg=='
    print(f"Warning: logo.png not found at {logo_path}. Using placeholder.")

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'debug.log',
        },
    },
    'loggers': {
        '': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}