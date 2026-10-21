from pathlib import Path
import os
from dotenv import load_dotenv
from datetime import timedelta

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / '.env')

SECRET_KEY = os.getenv('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'False') == 'True'

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = [
    # Apps de Django
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Apps externas
    'rest_framework',
    'corsheaders',

    # Apps del sistema
    'apps.usuarios.apps.UsuariosConfig',
    'apps.estrategia',
    'apps.indicadores',
    'apps.integraciones',
    'apps.auditoria',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
        # Etapa 4 (auditoría M7): cada petición es una sola transacción. Si
        # algo falla después de guardar (p. ej. la bitácora), se revierte
        # todo: no quedan operaciones a medias ni sin registro de auditoría.
        'ATOMIC_REQUESTS': True,
    }
}


# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGE_CODE = 'es'

TIME_ZONE = 'America/Guatemala'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/

STATIC_URL = 'static/'

# Archivos subidos por usuarios (Bloque 4: evidencia de mediciones).
# Almacenamiento local (FileSystemStorage, el default de Django): el
# proyecto corre localmente y luego en un servidor institucional propio, sin
# integración con S3/Drive/nube en esta etapa. MEDIA_URL no se expone como
# ruta pública en config/urls.py a propósito: los archivos se sirven
# únicamente mediante el endpoint autenticado GET /api/mediciones/{id}/evidencia/,
# que respeta los mismos permisos de lectura que el resto de Medicion.
MEDIA_ROOT = BASE_DIR / 'media'
MEDIA_URL = '/media/'

AUTH_USER_MODEL = 'usuarios.Usuario'


REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'apps.usuarios.authentication.JWTAuthenticationConControlPasswordTemporal',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'EXCEPTION_HANDLER': 'config.exception_handler.manejador_excepciones',
    # Etapa 2 (B2): cantidad de proxies inversos de confianza delante de
    # Django. 0 = se usa REMOTE_ADDR y se ignora X-Forwarded-For (que el
    # cliente puede falsificar). Detrás de Nginx/IIS en producción: 1.
    'NUM_PROXIES': int(os.getenv('DRF_NUM_PROXIES', '0')),
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'AUTH_HEADER_TYPES': ('Bearer',),
    # Etapa 2 (A3): login y renovación exigen is_active Y estado vigente.
    'USER_AUTHENTICATION_RULE': 'apps.usuarios.authentication.usuario_puede_autenticarse',
}

# Etapa 2 (B2): los contadores de límites de intentos usan esta caché. La
# caché en memoria es por proceso: sirve para el servidor de desarrollo y
# para un despliegue de un solo proceso. Con varios workers, cada uno
# contaría por separado; para producción configurar una caché compartida
# (ver documentación de despliegue).
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'sniff-default',
    }
}

# Etapa 2 (B2): límites de intentos (formato DRF: "<n>/<second|minute|hour|day>").
# Valores técnicos provisionales, pendientes de confirmación institucional;
# una variable vacía desactiva ese límite.
SNIFF_LIMITES_SOLICITUDES = {
    'login_ip': os.getenv('LIMITE_LOGIN_IP', '20/minute'),
    'login_usuario': os.getenv('LIMITE_LOGIN_USUARIO', '5/minute'),
    'restablecimiento_ip': os.getenv('LIMITE_RESTABLECIMIENTO_IP', '10/hour'),
    'restablecimiento_identificador': os.getenv('LIMITE_RESTABLECIMIENTO_IDENTIFICADOR', '3/hour'),
}

CORS_ALLOWED_ORIGINS = [
    'http://localhost:5173',
    'http://127.0.0.1:5173',
]