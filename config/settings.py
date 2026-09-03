from pathlib import Path

from decouple import config
import dj_database_url
from datetime import timedelta


# ============================================================
# BASE
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent


# ============================================================
# SEGURIDAD
# ============================================================

SECRET_KEY = config(
    'SECRET_KEY',
    default='django-build-only-insecure-key'
)

DEBUG = config(
    'DEBUG',
    default=False,
    cast=bool
)

ALLOWED_HOSTS = ['*']


# ============================================================
# MODELO DE USUARIO PERSONALIZADO
# ============================================================

AUTH_USER_MODEL = 'usuarios.Usuario'


# ============================================================
# BACKENDS DE AUTENTICACIÓN
# ============================================================

AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesStandaloneBackend',
    'django.contrib.auth.backends.ModelBackend',
]


# ============================================================
# APLICACIONES
# ============================================================

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'axes',

    'core',
    'apps.usuarios',
    'apps.areas',
    'apps.clientes',
    'apps.reclamaciones',
    'apps.reclamaciones_internas',
    'apps.liberaciones',
]


# ============================================================
# MIDDLEWARE
# ============================================================

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',

    'django.contrib.sessions.middleware.SessionMiddleware',

    'django.middleware.common.CommonMiddleware',

    'django.middleware.csrf.CsrfViewMiddleware',

    'django.contrib.auth.middleware.AuthenticationMiddleware',

    'django.contrib.messages.middleware.MessageMiddleware',

    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    
    
    'axes.middleware.AxesMiddleware',
]


# ============================================================
# URLS
# ============================================================

ROOT_URLCONF = 'config.urls'


# ============================================================
# TEMPLATES
# ============================================================

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',

        'DIRS': [
            BASE_DIR / 'templates'
        ],

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


# ============================================================
# WSGI
# ============================================================

WSGI_APPLICATION = 'config.wsgi.application'


# ============================================================
# BASE DE DATOS
# ============================================================

DATABASES = {
    'default': dj_database_url.parse(
        config('DATABASE_URL')
    )
}


# ============================================================
# VALIDACIÓN DE CONTRASEÑAS
# ============================================================

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME':
        'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'
    },
    {
        'NAME':
        'django.contrib.auth.password_validation.MinimumLengthValidator'
    },
    {
        'NAME':
        'django.contrib.auth.password_validation.CommonPasswordValidator'
    },
    {
        'NAME':
        'django.contrib.auth.password_validation.NumericPasswordValidator'
    },
]


# ============================================================
# IDIOMA Y ZONA HORARIA
# ============================================================

LANGUAGE_CODE = 'es-mx'

TIME_ZONE = 'America/Mexico_City'

USE_I18N = True

USE_TZ = True


# ============================================================
# ARCHIVOS ESTÁTICOS
# ============================================================

STATIC_URL = '/static/'

STATIC_ROOT = BASE_DIR / 'staticfiles'

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

STATICFILES_DIRS = [
    BASE_DIR / 'static'
]


# ============================================================
# ARCHIVOS MEDIA
# ============================================================
#
# Aquí se guardarán:
#
# media/
# ├── reclamaciones/
# │   ├── defectos/
# │   └── cierres/
# │
# └── otros archivos...
#
# ============================================================

MEDIA_URL = '/media/'

MEDIA_ROOT = BASE_DIR / 'media'


# ============================================================
# CONFIGURACIÓN DE LOGIN / LOGOUT
# ============================================================

LOGIN_URL = '/login/'

LOGIN_REDIRECT_URL = '/home/'

LOGOUT_REDIRECT_URL = '/login/'


# ============================================================
# SESIONES
# ============================================================
#
# 600 segundos = 10 minutos
#
# SESSION_SAVE_EVERY_REQUEST hace que cada petición válida
# reinicie el contador de inactividad.
#
# ============================================================

SESSION_COOKIE_AGE = 600

SESSION_SAVE_EVERY_REQUEST = True


# ============================================================
# SEGURIDAD DE SESIÓN
# ============================================================

SESSION_COOKIE_HTTPONLY = True

SESSION_COOKIE_SAMESITE = 'Lax'


# ============================================================
# CSRF
# ============================================================

CSRF_COOKIE_SAMESITE = 'Lax'


# ============================================================
# CORREO
# ============================================================

EMAIL_BACKEND = (
    'django.core.mail.backends.smtp.EmailBackend'
)

EMAIL_HOST = config(
    'MAIL_SERVER',
    default='localhost'
)

EMAIL_PORT = config(
    'MAIL_PORT',
    cast=int
)

EMAIL_HOST_USER = config(
    'MAIL_USERNAME',
    default=''
)

EMAIL_HOST_PASSWORD = config(
    'MAIL_PASSWORD',
    default=''
)

EMAIL_USE_TLS = config(
    'MAIL_USE_TLS',
    default=False,
    cast=bool
)

EMAIL_USE_SSL = config(
    'MAIL_USE_SSL',
    default=False,
    cast=bool
)

DEFAULT_FROM_EMAIL = config(
    'MAIL_DEFAULT_SENDER',
    default='webmaster@localhost'
)


# ============================================================
# PRIMARY KEY POR DEFECTO
# ============================================================

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'



# ============================================================
# DJANGO AXES
# ============================================================



AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = timedelta(minutes=10)
AXES_RESET_ON_SUCCESS = True
AXES_LOCKOUT_PARAMETERS = ["username"]
AXES_LOCKOUT_CALLABLE = 'apps.usuarios.views.axes_lockout'