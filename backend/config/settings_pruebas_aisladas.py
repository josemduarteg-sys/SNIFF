"""Solo pruebas: SQLite en memoria, sin cargar credenciales ni PostgreSQL."""
from pathlib import Path
import tempfile
BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = 'solo-pruebas-aisladas'
DEBUG = False
ALLOWED_HOSTS = ['testserver', 'localhost']
INSTALLED_APPS = [
    'django.contrib.admin', 'django.contrib.auth', 'django.contrib.contenttypes',
    'django.contrib.sessions', 'django.contrib.messages', 'django.contrib.staticfiles',
    'rest_framework', 'corsheaders', 'apps.usuarios.apps.UsuariosConfig',
    'apps.estrategia', 'apps.indicadores', 'apps.integraciones', 'apps.auditoria',
]
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:', 'ATOMIC_REQUESTS': True}}
ROOT_URLCONF = 'config.urls'
MIDDLEWARE = [
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
]
TEMPLATES = [{'BACKEND': 'django.template.backends.django.DjangoTemplates', 'APP_DIRS': True,
    'OPTIONS': {'context_processors': ['django.template.context_processors.request',
    'django.contrib.auth.context_processors.auth', 'django.contrib.messages.context_processors.messages']}}]
AUTH_USER_MODEL = 'usuarios.Usuario'
TIME_ZONE = 'America/Guatemala'
USE_TZ = True
LANGUAGE_CODE = 'es-gt'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
STATIC_URL = '/static/'
MEDIA_URL = '/media/'
# El runner usa TemporaryDirectory para aislar y retirar evidencias de pruebas.
MEDIA_ROOT = tempfile.gettempdir()
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': ['rest_framework_simplejwt.authentication.JWTAuthentication'],
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticated'],
}
