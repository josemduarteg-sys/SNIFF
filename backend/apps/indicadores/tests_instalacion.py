"""Inicialización aislada. SQLite no certifica migraciones de PostgreSQL."""
from io import StringIO
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
from unittest import mock

from django.core.management import call_command
from django.test import TestCase, SimpleTestCase

from apps.usuarios.models import Rol, Usuario
from apps.usuarios.permissions import es_administrador_sistema, es_administrador_planificacion
from apps.estrategia.models import Area
from .models import Frecuencia, TipoCalculo, FuenteDato, EstadoCumplimiento, ConfiguracionMediciones


class InicializacionTests(TestCase):
    def cargar(self):
        call_command('cargar_catalogos', stdout=StringIO())

    def test_migrar_y_cargar_dos_veces_sin_duplicar(self):
        # Test runner ejecuta las migraciones antes de preparar este escenario.
        self.assertEqual(Usuario.objects.count(), 0)
        self.assertEqual(ConfiguracionMediciones.objects.get(pk=1).dias_plazo_registro, 5)
        self.assertTrue(EstadoCumplimiento.objects.filter(nombre='Sin registro').exists())
        self.cargar()
        modelos = [Rol, Area, Frecuencia, TipoCalculo, FuenteDato, EstadoCumplimiento]
        antes = [list(m.objects.order_by('pk').values()) for m in modelos]
        self.cargar()
        self.assertEqual(antes, [list(m.objects.order_by('pk').values()) for m in modelos])
        self.assertSetEqual(set(Rol.objects.values_list('nombre', flat=True)), {
            'Administrador del sistema', 'Administrador de planificación',
            'Ejecutor operativo', 'Usuario de consulta',
        })
        self.assertEqual(Rol.objects.filter(estado=True).count(), 4)
        self.assertEqual(Frecuencia.objects.count(), 5)
        self.assertEqual(TipoCalculo.objects.count(), 6)
        self.assertEqual(FuenteDato.objects.count(), 3)
        self.assertEqual(EstadoCumplimiento.objects.count(), 5)
        self.assertEqual(Usuario.objects.count(), 0)

    def test_roles_existentes_y_supervisor_no_se_sobrescriben(self):
        supervisor = Rol.objects.create(nombre='Supervisor', estado=False, descripcion='Histórico')
        rol = Rol.objects.create(nombre='Administrador del sistema', estado=False, descripcion='Personalizado')
        self.cargar()
        self.cargar()
        supervisor.refresh_from_db()
        rol.refresh_from_db()
        self.assertFalse(supervisor.estado)
        self.assertEqual(supervisor.descripcion, 'Histórico')
        self.assertFalse(rol.estado)
        self.assertEqual(rol.descripcion, 'Personalizado')
        self.assertEqual(Rol.objects.filter(nombre='Supervisor').count(), 1)

    def test_rol_equivalente_no_se_duplica_por_mayusculas(self):
        rol = Rol.objects.create(nombre='ejecutor operativo', estado=True, descripcion='Existente')
        self.cargar()
        self.assertEqual(Rol.objects.filter(nombre__iexact='Ejecutor operativo').count(), 1)
        rol.refresh_from_db()
        self.assertEqual(rol.nombre, 'ejecutor operativo')
        self.assertEqual(rol.descripcion, 'Existente')

    def test_administrador_con_credencial_elegida_y_rol_explicito(self):
        self.cargar()
        password = secrets.token_urlsafe(32)
        with mock.patch.dict(os.environ, {'DJANGO_SUPERUSER_PASSWORD': password}):
            call_command('createsuperuser', username='admin_instalacion',
                         email='admin@example.invalid', interactive=False, stdout=StringIO())
        usuario = Usuario.objects.get(username='admin_instalacion')
        # Representa el paso explícito documentado en /admin/.
        usuario.correo = 'admin@example.invalid'
        usuario.rol = Rol.objects.get(nombre='Administrador del sistema')
        usuario.save(update_fields=['correo', 'rol'])
        usuario.refresh_from_db()
        self.assertTrue(usuario.check_password(password))
        self.assertTrue(usuario.is_superuser and usuario.is_staff and usuario.is_active and usuario.estado)
        self.assertTrue(es_administrador_sistema(usuario))
        self.assertFalse(es_administrador_planificacion(usuario))


class ConfiguracionInstalacionTests(SimpleTestCase):
    def entorno(self):
        entorno = os.environ.copy()
        entorno.update({
            'SNIFF_LOAD_DOTENV': 'False', 'SECRET_KEY': secrets.token_urlsafe(64),
            'DEBUG': 'False', 'ALLOWED_HOSTS': 'sniff.example.invalid, api.example.invalid',
            'CORS_ALLOWED_ORIGINS': 'https://sniff.example.invalid',
            'CSRF_TRUSTED_ORIGINS': 'https://sniff.example.invalid',
            'SECURE_SSL_REDIRECT': 'True', 'SESSION_COOKIE_SECURE': 'True',
            'CSRF_COOKIE_SECURE': 'True', 'SECURE_HSTS_SECONDS': '3600',
            'SECURE_HSTS_INCLUDE_SUBDOMAINS': 'False', 'SECURE_HSTS_PRELOAD': 'False',
            'TRUST_X_FORWARDED_PROTO': 'True', 'USE_X_FORWARDED_HOST': 'False',
            'STATIC_ROOT': 'staticfiles_prueba', 'MEDIA_ROOT': 'media_prueba',
            # No conexión real: estos checks no solicitan consultas de datos.
            'DB_NAME': 'solo_revision_sin_conexion', 'DB_USER': 'sin_conexion',
            'DB_PASSWORD': '', 'DB_HOST': '127.0.0.1', 'DB_PORT': '1',
            'DJANGO_SETTINGS_MODULE': 'config.settings',
        })
        return entorno

    def ejecutar(self, args):
        return subprocess.run([sys.executable, '-B', *args], env=self.entorno(),
                              cwd=Path(__file__).resolve().parents[2],
                              capture_output=True, text=True, check=False)

    def test_parametros_institucionales_sin_dotenv_local(self):
        result = self.ejecutar(['-c', """
import json
from config import settings as s
print(json.dumps({'hosts':s.ALLOWED_HOSTS,'cors':s.CORS_ALLOWED_ORIGINS,
'csrf':s.CSRF_TRUSTED_ORIGINS,'debug':s.DEBUG,'https':s.SECURE_SSL_REDIRECT,
'proxy':s.SECURE_PROXY_SSL_HEADER,'static':s.STATIC_ROOT.name,'media':s.MEDIA_ROOT.name}))
"""])
        self.assertEqual(result.returncode, 0, result.stderr)
        datos = json.loads(result.stdout)
        self.assertEqual(datos['hosts'], ['sniff.example.invalid', 'api.example.invalid'])
        self.assertEqual(datos['cors'], ['https://sniff.example.invalid'])
        self.assertEqual(datos['csrf'], ['https://sniff.example.invalid'])
        self.assertFalse(datos['debug'])
        self.assertTrue(datos['https'])
        self.assertEqual(datos['proxy'], ['HTTP_X_FORWARDED_PROTO', 'https'])
        self.assertEqual(datos['static'], 'staticfiles_prueba')
        self.assertEqual(datos['media'], 'media_prueba')

    def test_check_deploy_con_https_y_hsts_gradual(self):
        result = self.ejecutar(['manage.py', 'check', '--deploy'])
        self.assertEqual(result.returncode, 0, result.stderr)
        # Subdominios y preload son decisiones institucionales, no defaults.
        for aviso in ('security.W004', 'security.W008', 'security.W009',
                      'security.W012', 'security.W016', 'security.W018', 'security.W020'):
            self.assertNotIn(aviso, result.stderr)
        self.assertIn('security.W005', result.stderr)
        self.assertIn('security.W021', result.stderr)
