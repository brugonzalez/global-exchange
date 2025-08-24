"""
Configuración de Django para el proyecto global_exchange.

Generado por 'django-admin startproject' usando Django 5.2.4.

Para más información sobre este archivo, ver
https://docs.djangoproject.com/en/5.2/topics/settings/

Para la lista completa de configuraciones y sus valores, ver
https://docs.djangoproject.com/en/5.2/ref/settings/
"""

import os
from pathlib import Path
from decouple import config

# Construye las rutas dentro del proyecto así: DIRECTORIO_BASE / 'subdir'.
DIRECTORIO_BASE = Path(__file__).resolve().parent.parent


# Configuraciones de desarrollo de inicio rápido - no aptas para producción
# Ver https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# ADVERTENCIA DE SEGURIDAD: ¡mantén la clave secreta utilizada en producción en secreto!
SECRET_KEY = config('SECRET_KEY', default='django-insecure-(zfqwn(b_@^e17z=uohdbyxka#79mf^b)rdgn9n@$athop!a15')

# ADVERTENCIA DE SEGURIDAD: ¡no ejecutes con debug activado en producción!
DEBUG = config('DEBUG', default=True, cast=bool)

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0']


# Definición de la aplicación

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    
    # Aplicaciones de terceros
    'django_extensions',
    'crispy_forms',
    'crispy_bootstrap4',
    'django_otp',
    'django_otp.plugins.otp_totp',
    'django_otp.plugins.otp_static',
    
    # Aplicaciones locales
    'cuentas.apps.ConfiguracionCuentas',
    'clientes.apps.ConfiguracionClientes',
    'divisas.apps.ConfiguracionDivisas',
    'transacciones.apps.ConfiguracionTransacciones',
    'reportes.apps.ConfiguracionReportes',
    'notificaciones.apps.ConfiguracionNotificaciones',
    'tauser.apps.TauserConfig',
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
]

ROOT_URLCONF = 'global_exchange.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [DIRECTORIO_BASE / 'plantillas'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.media',
            ],
        },
    },
]

WSGI_APPLICATION = 'global_exchange.wsgi.application'


# Base de datos
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

# Usar SQLite para desarrollo
# En producción, reemplazar con la configuración de PostgreSQL
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': DIRECTORIO_BASE / 'db.sqlite3',
    }
}

# Descomentar y configurar para PostgreSQL en producción:
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql',
#         'NAME': config('DB_NAME', default='global_exchange'),
#         'USER': config('DB_USER', default='postgres'),
#         'PASSWORD': config('DB_PASSWORD', default='postgres'),
#         'HOST': config('DB_HOST', default='localhost'),
#         'PORT': config('DB_PORT', default='5432', cast=int),
#     }
# }


# Validación de contraseñas
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = []

# AUTH_PASSWORD_VALIDATORS = [
#     {
#         'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
#     },
#     {
#         'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
#     },
#     {
#         'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
#     },
#     {
#         'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
#     },
# ]


# Internacionalización
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'es-py'  # Español de Paraguay

TIME_ZONE = 'America/Asuncion'  # Zona horaria apropiada para Global Exchange en Paraguay

USE_I18N = True

USE_TZ = True


# Archivos estáticos (CSS, JavaScript, Imágenes)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = '/static/'
STATICFILES_DIRS = [DIRECTORIO_BASE / 'static']
STATIC_ROOT = DIRECTORIO_BASE / 'staticfiles'

# Archivos de medios
MEDIA_URL = '/media/'
MEDIA_ROOT = DIRECTORIO_BASE / 'media'

# Tipo de campo de clave primaria por defecto
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Modelo de Usuario Personalizado
AUTH_USER_MODEL = 'cuentas.Usuario'

# URLs de Inicio/Cierre de Sesión
LOGIN_URL = '/cuentas/iniciar-sesion/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

# Configuración de Email
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

# Para desarrollo, usar el backend de consola si no hay configuración de email
if not EMAIL_HOST_USER:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Formularios Crispy
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap4"
CRISPY_TEMPLATE_PACK = "bootstrap4"

# Configuración de Seguridad
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Configuración CSRF
CSRF_FAILURE_VIEW = 'clientes.views.fallo_csrf'
CSRF_COOKIE_AGE = 31449600  # 1 año, igual que el por defecto de Django

# Configuración de Sesión
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_AGE = 3600  # 1 hora
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# Configuración de Bloqueo de Cuenta
BLOQUEO_CUENTA_ACTIVADO = True
INTENTOS_MAX_BLOQUEO_CUENTA = 5
DURACION_BLOQUEO_CUENTA = 1800  # 30 minutos

# Configuración de API Externa
API_KEY_TASA_CAMBIO = config('API_KEY_TASA_CAMBIO', default='')
API_URL_TASA_CAMBIO = 'https://api.exchangerate-api.com/v4/latest/'

# Configuración de Stripe
STRIPE_CLAVE_PUBLICABLE = config('STRIPE_CLAVE_PUBLICABLE', default='pk_test_51234567890abcdef')
STRIPE_CLAVE_SECRETA = config('STRIPE_CLAVE_SECRETA', default='sk_test_51234567890abcdef')
STRIPE_SECRETO_ENDPOINT = config('STRIPE_SECRETO_ENDPOINT', default='whsec_12345')

# Configuración de Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': DIRECTORIO_BASE / 'logs' / 'global_exchange.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'global_exchange': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}