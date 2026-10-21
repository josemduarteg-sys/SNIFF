from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Rol, SolicitudRestablecimientoPassword, Usuario

PASSWORD_INICIAL = 'Inicial-Sniff-2026'
PASSWORD_NUEVO = 'Nueva-Clave-Segura-2026'
URL_LOGIN = '/api/auth/login/'
URL_ME = '/api/usuarios/me/'
URL_CAMBIAR = '/api/usuarios/cambiar-password/'
URL_PROTEGIDA = '/api/notificaciones/'


def obtener_rol(nombre):
    rol, _ = Rol.objects.get_or_create(
        nombre=nombre,
        defaults={'descripcion': 'Rol de prueba', 'estado': True},
    )
    return rol


def crear_usuario_admin(username):
    usuario = Usuario.objects.create_user(username=username, password='clave-prueba-123')
    usuario.rol = obtener_rol('Administrador del sistema')
    usuario.correo = f'{username}@sniff.test'
    usuario.save()
    return usuario


class CambioObligatorioPasswordTests(APITestCase):
    """Usuarios creados desde el módulo de Usuarios: cambio obligatorio de la
    contraseña inicial en el primer inicio de sesión (casos 1 a 10)."""

    def setUp(self):
        # Etapa 2 (B2): contadores de límites de intentos aislados por prueba.
        cache.clear()
        self.admin = crear_usuario_admin('admin_usuarios')

    # ------------------------------------------------------------ helpers
    def crear_usuario_desde_modulo(self, username, rol_nombre='Supervisor'):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            '/api/usuarios/',
            {
                'username': username,
                'first_name': 'Nuevo',
                'last_name': 'Usuario',
                'correo': f'{username}@sniff.test',
                'rol': obtener_rol(rol_nombre).id,
                'estado': True,
                'password': PASSWORD_INICIAL,
            },
            format='json',
        )
        self.client.force_authenticate(user=None)
        return response

    def iniciar_sesion(self, username, password):
        """Login real con JWT: así se ejercita la clase de autenticación que
        bloquea la API mientras debe_cambiar_password=True."""
        self.client.credentials()
        response = self.client.post(URL_LOGIN, {'username': username, 'password': password}, format='json')
        if response.status_code == status.HTTP_200_OK:
            self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
        return response

    # ------------------------------------------------------------ casos
    def test_caso_1_crear_usuario_queda_con_cambio_obligatorio(self):
        response = self.crear_usuario_desde_modulo('nuevo_caso1')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        usuario = Usuario.objects.get(username='nuevo_caso1')
        self.assertTrue(usuario.debe_cambiar_password)
        self.assertTrue(usuario.check_password(PASSWORD_INICIAL))

    def test_caso_1_aplica_a_todos_los_roles(self):
        roles = [
            'Administrador del sistema',
            'Administrador de planificación',
            'Ejecutor operativo',
            'Usuario de consulta',
        ]
        for i, rol in enumerate(roles):
            with self.subTest(rol=rol):
                response = self.crear_usuario_desde_modulo(f'nuevo_rol_{i}', rol)
                self.assertEqual(response.status_code, status.HTTP_201_CREATED)
                self.assertTrue(Usuario.objects.get(username=f'nuevo_rol_{i}').debe_cambiar_password)

    def test_caso_1_el_frontend_no_puede_desactivar_la_bandera(self):
        self.client.force_authenticate(user=self.admin)
        self.client.post(
            '/api/usuarios/',
            {
                'username': 'nuevo_sin_bandera',
                'correo': 'nuevo_sin_bandera@sniff.test',
                'rol': obtener_rol('Supervisor').id,
                'password': PASSWORD_INICIAL,
                'debe_cambiar_password': False,
            },
            format='json',
        )
        self.assertTrue(Usuario.objects.get(username='nuevo_sin_bandera').debe_cambiar_password)

    def test_caso_2_login_exitoso_e_informa_cambio_obligatorio(self):
        self.crear_usuario_desde_modulo('nuevo_caso2')

        response = self.iniciar_sesion('nuevo_caso2', PASSWORD_INICIAL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        me = self.client.get(URL_ME)
        self.assertEqual(me.status_code, status.HTTP_200_OK)
        self.assertTrue(me.data['debe_cambiar_password'])

    def test_caso_4_api_protegida_rechazada_antes_del_cambio(self):
        self.crear_usuario_desde_modulo('nuevo_caso4')
        self.iniciar_sesion('nuevo_caso4', PASSWORD_INICIAL)

        response = self.client.get(URL_PROTEGIDA)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('Debés cambiar tu contraseña', str(response.data['detail']))

    def test_casos_5_6_7_cambio_correcto_libera_el_sistema(self):
        self.crear_usuario_desde_modulo('nuevo_caso5')
        self.iniciar_sesion('nuevo_caso5', PASSWORD_INICIAL)

        # Caso 5: cambio correcto -> bandera en False
        response = self.client.post(
            URL_CAMBIAR,
            {
                'password_actual': PASSWORD_INICIAL,
                'password_nuevo': PASSWORD_NUEVO,
                'password_confirmacion': PASSWORD_NUEVO,
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(Usuario.objects.get(username='nuevo_caso5').debe_cambiar_password)

        # Caso 6: con la misma sesión ya puede usar la API protegida
        self.assertEqual(self.client.get(URL_PROTEGIDA).status_code, status.HTTP_200_OK)

        # Caso 7: nuevo login con la nueva contraseña, sin cambio obligatorio
        self.assertEqual(
            self.iniciar_sesion('nuevo_caso5', PASSWORD_INICIAL).status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
        self.assertEqual(self.iniciar_sesion('nuevo_caso5', PASSWORD_NUEVO).status_code, status.HTTP_200_OK)
        self.assertFalse(self.client.get(URL_ME).data['debe_cambiar_password'])
        self.assertEqual(self.client.get(URL_PROTEGIDA).status_code, status.HTTP_200_OK)

    def test_caso_8_editar_usuario_no_reactiva_la_bandera(self):
        existente = Usuario.objects.create_user(username='existente', password='clave-prueba-123')
        existente.correo = 'existente@sniff.test'
        existente.rol = obtener_rol('Supervisor')
        existente.save()
        self.assertFalse(existente.debe_cambiar_password)

        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(
            f'/api/usuarios/{existente.id}/',
            {
                'first_name': 'Editado',
                'correo': 'editado@sniff.test',
                'rol': obtener_rol('Usuario de consulta').id,
                'estado': True,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        existente.refresh_from_db()
        self.assertEqual(existente.first_name, 'Editado')
        self.assertFalse(existente.debe_cambiar_password)

    def test_caso_8_edicion_sigue_sin_permitir_cambiar_password(self):
        existente = Usuario.objects.create_user(username='existente_pwd', password='clave-prueba-123')
        existente.correo = 'existente_pwd@sniff.test'
        existente.save()

        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(
            f'/api/usuarios/{existente.id}/', {'password': 'Otra-Clave-2026'}, format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        existente.refresh_from_db()
        self.assertTrue(existente.check_password('clave-prueba-123'))

    def test_caso_9_restablecimiento_sigue_exigiendo_el_cambio(self):
        usuario = Usuario.objects.create_user(username='olvido', password='clave-original-123')
        usuario.correo = 'olvido@sniff.test'
        usuario.save()
        solicitud = SolicitudRestablecimientoPassword.objects.create(
            usuario=usuario, identificador_ingresado='olvido', estado='aprobada',
        )

        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            f'/api/solicitudes-restablecimiento/{solicitud.id}/asignar-password-temporal/',
            {'password_temporal': 'Temporal-Sniff-2026'},
            format='json',
        )
        self.client.force_authenticate(user=None)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        usuario.refresh_from_db()
        self.assertTrue(usuario.debe_cambiar_password)

        self.iniciar_sesion('olvido', 'Temporal-Sniff-2026')
        self.assertEqual(self.client.get(URL_PROTEGIDA).status_code, status.HTTP_403_FORBIDDEN)

        self.client.post(
            URL_CAMBIAR,
            {
                'password_actual': 'Temporal-Sniff-2026',
                'password_nuevo': PASSWORD_NUEVO,
                'password_confirmacion': PASSWORD_NUEVO,
            },
            format='json',
        )
        usuario.refresh_from_db()
        self.assertFalse(usuario.debe_cambiar_password)

    def test_caso_10_usuarios_existentes_no_cambian(self):
        existente = Usuario.objects.create_user(username='previo', password='clave-prueba-123')
        self.assertFalse(existente.debe_cambiar_password)

        self.crear_usuario_desde_modulo('nuevo_caso10')

        existente.refresh_from_db()
        self.admin.refresh_from_db()
        self.assertFalse(existente.debe_cambiar_password)
        self.assertFalse(self.admin.debe_cambiar_password)
