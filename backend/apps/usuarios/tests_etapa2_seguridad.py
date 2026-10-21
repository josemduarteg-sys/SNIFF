"""Etapa 2 de correcciones post-auditoría (20/10/2026): sesiones JWT (A3),
integraciones (A4), último Administrador del sistema (M10), validación de
contraseñas (B5) y límites de intentos (B2)."""

from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.auditoria.models import Bitacora
from apps.integraciones.models import ArchivoImportado, ConexionDW
from apps.indicadores.serializers import MedicionSerializer

from .models import Rol, SolicitudRestablecimientoPassword, Usuario

ROL_ADMIN_SISTEMA = 'Administrador del sistema'
ROL_ADMIN_PLANIFICACION = 'Administrador de planificación'
ROL_EJECUTOR_OPERATIVO = 'Ejecutor operativo'
ROL_USUARIO_CONSULTA = 'Usuario de consulta'
CUATRO_ROLES = (ROL_ADMIN_SISTEMA, ROL_ADMIN_PLANIFICACION, ROL_EJECUTOR_OPERATIVO, ROL_USUARIO_CONSULTA)

PASSWORD_PRUEBA = 'clave-prueba-123'
PASSWORD_FUERTE = 'Cooperativa-Segura-2026'

URL_LOGIN = '/api/auth/login/'
URL_REFRESH = '/api/auth/refresh/'
URL_ME = '/api/usuarios/me/'
URL_RECUPERAR = '/api/usuarios/solicitar-restablecimiento/'


def obtener_rol(nombre):
    rol, _ = Rol.objects.get_or_create(nombre=nombre, defaults={'descripcion': 'Rol de prueba', 'estado': True})
    return rol


def crear_usuario(username, rol_nombre=ROL_USUARIO_CONSULTA, **extra):
    usuario = Usuario.objects.create_user(username=username, password=PASSWORD_PRUEBA, **extra)
    usuario.rol = obtener_rol(rol_nombre) if rol_nombre else None
    usuario.correo = f'{username}@sniff.test'
    usuario.save()
    return usuario


class SeguridadBase(APITestCase):
    def setUp(self):
        cache.clear()

    def tearDown(self):
        cache.clear()

    def usar_access(self, access):
        self.client.force_authenticate(user=None)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')

    def refrescar(self, refresh):
        self.client.credentials()
        return self.client.post(URL_REFRESH, {'refresh': refresh}, format='json')


# ---------------------------------------------------------------- A3

class RenovacionSesionTests(SeguridadBase):
    def test_configuracion_jwt_sin_cambios_de_duracion(self):
        self.assertEqual(settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'], timedelta(minutes=60))
        self.assertEqual(settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'], timedelta(days=1))

    def test_renovacion_correcta_del_access_token(self):
        usuario = crear_usuario('renueva_ok', ROL_EJECUTOR_OPERATIVO)
        refresh = RefreshToken.for_user(usuario)

        response = self.refrescar(str(refresh))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.usar_access(response.data['access'])
        self.assertEqual(self.client.get(URL_ME).data['username'], 'renueva_ok')

    def test_refresh_vencido_es_rechazado(self):
        usuario = crear_usuario('refresh_vencido')
        refresh = RefreshToken.for_user(usuario)
        refresh.set_exp(lifetime=-timedelta(seconds=1))

        response = self.refrescar(str(refresh))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_invalido_es_rechazado(self):
        self.assertEqual(self.refrescar('no-es-un-token').status_code, status.HTTP_401_UNAUTHORIZED)

    def test_access_vencido_responde_401(self):
        usuario = crear_usuario('access_vencido')
        access = RefreshToken.for_user(usuario).access_token
        access.set_exp(lifetime=-timedelta(seconds=1))

        self.usar_access(str(access))

        self.assertEqual(self.client.get(URL_ME).status_code, status.HTTP_401_UNAUTHORIZED)

    def test_usuario_inactivo_no_renueva(self):
        usuario = crear_usuario('inactivo_renueva')
        refresh = str(RefreshToken.for_user(usuario))
        Usuario.objects.filter(pk=usuario.pk).update(is_active=False, estado=False)

        self.assertEqual(self.refrescar(refresh).status_code, status.HTTP_401_UNAUTHORIZED)

    def test_estado_inactivo_no_renueva_aunque_is_active_siga_true(self):
        usuario = crear_usuario('estado_inactivo_renueva')
        refresh = str(RefreshToken.for_user(usuario))
        Usuario.objects.filter(pk=usuario.pk).update(estado=False)

        self.assertEqual(self.refrescar(refresh).status_code, status.HTTP_401_UNAUTHORIZED)

    def test_access_emitido_antes_de_inactivar_deja_de_servir(self):
        usuario = crear_usuario('inactivado_en_sesion')
        access = str(RefreshToken.for_user(usuario).access_token)
        Usuario.objects.filter(pk=usuario.pk).update(estado=False)

        self.usar_access(access)

        self.assertEqual(self.client.get(URL_ME).status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_rechaza_cuenta_con_estado_inactivo(self):
        usuario = crear_usuario('estado_inactivo_login')
        Usuario.objects.filter(pk=usuario.pk).update(estado=False)

        response = self.client.post(URL_LOGIN, {'username': 'estado_inactivo_login', 'password': PASSWORD_PRUEBA})

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_renovar_no_amplia_permisos(self):
        ejecutor = crear_usuario('ejecutor_renueva', ROL_EJECUTOR_OPERATIVO)
        response = self.refrescar(str(RefreshToken.for_user(ejecutor)))
        self.usar_access(response.data['access'])

        self.assertEqual(
            self.client.post('/api/planes-estrategicos/', {'titulo': 'Intento'}).status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(self.client.get('/api/usuarios/').status_code, status.HTTP_403_FORBIDDEN)

    def test_cambio_de_rol_aplica_despues_de_renovar(self):
        crear_usuario('admin_respaldo', ROL_ADMIN_SISTEMA)
        admin = crear_usuario('admin_degradado', ROL_ADMIN_SISTEMA)
        refresh = str(RefreshToken.for_user(admin))

        admin.rol = obtener_rol(ROL_USUARIO_CONSULTA)
        admin.save()

        response = self.refrescar(refresh)
        self.usar_access(response.data['access'])

        self.assertEqual(self.client.get('/api/usuarios/').status_code, status.HTTP_403_FORBIDDEN)

    def test_cambio_obligatorio_de_password_sigue_vigente_tras_renovar(self):
        usuario = crear_usuario('renueva_temporal', debe_cambiar_password=True)
        response = self.refrescar(str(RefreshToken.for_user(usuario)))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.usar_access(response.data['access'])
        self.assertEqual(self.client.get(URL_ME).status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.get('/api/notificaciones/').status_code, status.HTTP_403_FORBIDDEN)

    def test_los_cuatro_roles_inician_sesion_y_renuevan(self):
        for indice, rol in enumerate(CUATRO_ROLES):
            with self.subTest(rol=rol):
                username = f'rol_sesion_{indice}'
                crear_usuario(username, rol)

                login = self.client.post(URL_LOGIN, {'username': username, 'password': PASSWORD_PRUEBA})
                self.assertEqual(login.status_code, status.HTTP_200_OK)

                renovado = self.refrescar(login.data['refresh'])
                self.assertEqual(renovado.status_code, status.HTTP_200_OK)

                self.usar_access(renovado.data['access'])
                self.assertEqual(self.client.get(URL_ME).data['rol_nombre'], rol)

    def test_api_auth_de_sesion_ya_no_esta_expuesta(self):
        self.assertEqual(self.client.get('/api-auth/login/').status_code, status.HTTP_404_NOT_FOUND)


# ---------------------------------------------------------------- A4

class IntegracionesRestringidasTests(SeguridadBase):
    def setUp(self):
        super().setUp()
        self.usuarios = {rol: crear_usuario(f'integ_{i}', rol) for i, rol in enumerate(CUATRO_ROLES)}
        self.archivo = ArchivoImportado.objects.create(
            nombre_archivo='carga.csv', importado_por=self.usuarios[ROL_ADMIN_SISTEMA],
        )
        self.conexion = ConexionDW.objects.create(nombre='DW', servidor='srv', base_datos='bd')

    def test_lectura_solo_para_administrador_del_sistema(self):
        for rol, usuario in self.usuarios.items():
            self.client.force_authenticate(user=usuario)

            for ruta in ('archivos-importados', 'conexiones-dw', 'consultas-dw'):
                esperado = status.HTTP_200_OK if rol == ROL_ADMIN_SISTEMA else status.HTTP_403_FORBIDDEN
                self.assertEqual(self.client.get(f'/api/{ruta}/').status_code, esperado, f'{rol} {ruta}')

    def test_ningun_rol_puede_escribir(self):
        for rol, usuario in self.usuarios.items():
            self.client.force_authenticate(user=usuario)

            respuestas = [
                self.client.post('/api/archivos-importados/', {'nombre_archivo': 'x.csv'}),
                self.client.post('/api/conexiones-dw/', {'nombre': 'otra', 'servidor': 's', 'base_datos': 'b'}),
                self.client.patch(f'/api/conexiones-dw/{self.conexion.id}/', {'servidor': 'otro'}),
                self.client.put(f'/api/conexiones-dw/{self.conexion.id}/', {'nombre': 'DW', 'servidor': 'x', 'base_datos': 'y'}),
                self.client.delete(f'/api/archivos-importados/{self.archivo.id}/'),
            ]

            for response in respuestas:
                self.assertIn(
                    response.status_code,
                    (status.HTTP_403_FORBIDDEN, status.HTTP_405_METHOD_NOT_ALLOWED),
                    rol,
                )

        self.conexion.refresh_from_db()
        self.assertEqual(self.conexion.servidor, 'srv')
        self.assertEqual(ConexionDW.objects.count(), 1)
        self.assertTrue(ArchivoImportado.objects.filter(id=self.archivo.id).exists())

    def test_sin_autenticacion_responde_401(self):
        self.assertEqual(self.client.get('/api/conexiones-dw/').status_code, status.HTTP_401_UNAUTHORIZED)

    def test_medicion_no_acepta_vinculos_de_integracion(self):
        campos = MedicionSerializer().fields

        self.assertTrue(campos['archivo_importado'].read_only)
        self.assertTrue(campos['consulta_dw'].read_only)


# ---------------------------------------------------------------- M10

class UltimoAdministradorSistemaTests(SeguridadBase):
    def setUp(self):
        super().setUp()
        self.admin = crear_usuario('admin_unico', ROL_ADMIN_SISTEMA)
        self.client.force_authenticate(user=self.admin)

    def url(self, usuario):
        return f'/api/usuarios/{usuario.id}/'

    def assertSigueAdminActivo(self, usuario):
        usuario.refresh_from_db()
        self.assertEqual(usuario.rol.nombre, ROL_ADMIN_SISTEMA)
        self.assertTrue(usuario.is_active)
        self.assertTrue(usuario.estado)

    def test_ultimo_admin_no_puede_quitarse_el_rol(self):
        for rol in (ROL_ADMIN_PLANIFICACION, ROL_EJECUTOR_OPERATIVO, ROL_USUARIO_CONSULTA):
            response = self.client.patch(self.url(self.admin), {'rol': obtener_rol(rol).id}, format='json')
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, rol)

        response = self.client.patch(self.url(self.admin), {'rol': None}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertSigueAdminActivo(self.admin)

    def test_ultimo_admin_no_puede_desactivarse_por_edicion(self):
        for payload in ({'estado': False}, {'is_active': False}, {'estado': False, 'is_active': False}):
            response = self.client.patch(self.url(self.admin), payload, format='json')
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, payload)

        self.assertSigueAdminActivo(self.admin)

    def test_puede_editar_sus_datos_personales(self):
        response = self.client.patch(self.url(self.admin), {
            'first_name': 'Nombre', 'last_name': 'Actualizado', 'correo': 'nuevo_admin@sniff.test',
            'rol': self.admin.rol_id,
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.first_name, 'Nombre')
        self.assertSigueAdminActivo(self.admin)

    def test_con_otro_admin_activo_si_puede_cambiar_su_rol(self):
        crear_usuario('admin_segundo', ROL_ADMIN_SISTEMA)

        response = self.client.patch(
            self.url(self.admin), {'rol': obtener_rol(ROL_USUARIO_CONSULTA).id}, format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_varios_administradores_pueden_coexistir_e_inactivarse_entre_si(self):
        segundo = crear_usuario('admin_segundo_b', ROL_ADMIN_SISTEMA)
        tercero = crear_usuario('admin_tercero', ROL_ADMIN_SISTEMA)

        self.assertEqual(self.client.delete(self.url(segundo)).status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.delete(self.url(tercero)).status_code, status.HTTP_200_OK)
        self.assertSigueAdminActivo(self.admin)

    def test_admins_inactivos_no_cuentan(self):
        crear_usuario('admin_inactivo', ROL_ADMIN_SISTEMA, is_active=False)
        estado_inactivo = crear_usuario('admin_estado_inactivo', ROL_ADMIN_SISTEMA)
        Usuario.objects.filter(pk=estado_inactivo.pk).update(estado=False)

        response = self.client.patch(
            self.url(self.admin), {'rol': obtener_rol(ROL_USUARIO_CONSULTA).id}, format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertSigueAdminActivo(self.admin)

    def test_superusuario_sin_rol_cuenta_como_respaldo_tecnico(self):
        crear_usuario('super_sin_rol', rol_nombre=None, is_superuser=True, is_staff=True)

        response = self.client.patch(
            self.url(self.admin), {'rol': obtener_rol(ROL_USUARIO_CONSULTA).id}, format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_superusuario_con_otro_rol_no_equivale_a_administrador_del_sistema(self):
        crear_usuario('super_con_rol', ROL_USUARIO_CONSULTA, is_superuser=True, is_staff=True)

        response = self.client.patch(
            self.url(self.admin), {'rol': obtener_rol(ROL_USUARIO_CONSULTA).id}, format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertSigueAdminActivo(self.admin)

    def test_no_se_puede_inactivar_al_ultimo_admin_por_otra_via(self):
        # Superusuario técnico sin rol (único otro "admin" posible) intenta
        # inactivar al último admin funcional: él mismo cuenta como admin,
        # así que se permite; sin él, no habría nadie que pudiera hacerlo.
        tecnico = crear_usuario('super_tecnico', rol_nombre=None, is_superuser=True)
        self.client.force_authenticate(user=tecnico)

        self.assertEqual(self.client.delete(self.url(self.admin)).status_code, status.HTTP_200_OK)

        # Ahora el técnico es el último y no puede inactivarse a sí mismo.
        self.assertEqual(self.client.delete(self.url(tecnico)).status_code, status.HTTP_400_BAD_REQUEST)

    def test_reactivar_y_editar_otros_usuarios_sigue_funcionando(self):
        otro = crear_usuario('ejecutor_editable', ROL_EJECUTOR_OPERATIVO)

        self.assertEqual(self.client.delete(self.url(otro)).status_code, status.HTTP_200_OK)
        response = self.client.patch(self.url(otro), {'estado': True, 'is_active': True}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        otro.refresh_from_db()
        self.assertTrue(otro.is_active)

    def test_is_staff_no_se_concede_desde_el_modulo_de_usuarios(self):
        otro = crear_usuario('sin_staff', ROL_EJECUTOR_OPERATIVO)

        response = self.client.patch(self.url(otro), {'is_staff': True}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        otro.refresh_from_db()
        self.assertFalse(otro.is_staff)


# ---------------------------------------------------------------- B5

class ValidacionPasswordTests(SeguridadBase):
    def setUp(self):
        super().setUp()
        self.admin = crear_usuario('admin_passwords', ROL_ADMIN_SISTEMA)
        self.client.force_authenticate(user=self.admin)

    def crear(self, username, password):
        return self.client.post('/api/usuarios/', {
            'username': username,
            'first_name': 'Carlos',
            'last_name': 'Mendez',
            'correo': f'{username}@sniff.test',
            'rol': obtener_rol(ROL_EJECUTOR_OPERATIVO).id,
            'password': password,
        }, format='json')

    def test_password_inicial_debil_es_rechazada(self):
        # numérica, común, corta, similar al usuario
        for password in ('12345678', 'qwertyuiop', 'Ab1', 'carlosmendez1'):
            with self.subTest(password=password):
                response = self.crear('carlosmendez', password)

                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn('password', response.data)
                self.assertNotIn(password, ' '.join(response.data['password']))

        self.assertFalse(Usuario.objects.filter(username='carlosmendez').exists())

    def test_password_inicial_valida_es_aceptada(self):
        response = self.crear('nuevo_valido', PASSWORD_FUERTE)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertNotIn('password', response.data)
        usuario = Usuario.objects.get(username='nuevo_valido')
        self.assertTrue(usuario.check_password(PASSWORD_FUERTE))
        self.assertTrue(usuario.debe_cambiar_password)

    def asignar_temporal(self, solicitud, password):
        return self.client.post(
            f'/api/solicitudes-restablecimiento/{solicitud.id}/asignar-password-temporal/',
            {'password_temporal': password},
            format='json',
        )

    def test_password_temporal_debil_es_rechazada_sin_cambiar_nada(self):
        usuario = crear_usuario('olvido_temporal', ROL_EJECUTOR_OPERATIVO)
        solicitud = SolicitudRestablecimientoPassword.objects.create(
            usuario=usuario, identificador_ingresado='olvido_temporal', estado='aprobada',
        )

        for password in ('12345678', 'qwertyuiop', 'olvido_temporal'):
            with self.subTest(password=password):
                response = self.asignar_temporal(solicitud, password)

                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn('password_temporal', response.data)
                self.assertNotIn(password, ' '.join(response.data['password_temporal']))

        usuario.refresh_from_db()
        solicitud.refresh_from_db()
        self.assertTrue(usuario.check_password(PASSWORD_PRUEBA))
        self.assertFalse(usuario.debe_cambiar_password)
        self.assertEqual(solicitud.estado, 'aprobada')

    def test_password_temporal_valida_completa_el_flujo(self):
        usuario = crear_usuario('olvido_valido', ROL_EJECUTOR_OPERATIVO)
        solicitud = SolicitudRestablecimientoPassword.objects.create(
            usuario=usuario, identificador_ingresado='olvido_valido', estado='aprobada',
        )

        response = self.asignar_temporal(solicitud, PASSWORD_FUERTE)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        usuario.refresh_from_db()
        solicitud.refresh_from_db()
        self.assertTrue(usuario.check_password(PASSWORD_FUERTE))
        self.assertTrue(usuario.debe_cambiar_password)
        self.assertEqual(solicitud.estado, 'atendida')

    def test_password_definitiva_sigue_validandose(self):
        usuario = crear_usuario('cambia_definitiva', ROL_EJECUTOR_OPERATIVO)
        self.client.force_authenticate(user=usuario)

        response = self.client.post('/api/usuarios/cambiar-password/', {
            'password_actual': PASSWORD_PRUEBA,
            'password_nuevo': '12345678',
            'password_confirmacion': '12345678',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_las_contrasenas_no_quedan_en_bitacora(self):
        usuario = crear_usuario('olvido_bitacora', ROL_EJECUTOR_OPERATIVO)
        solicitud = SolicitudRestablecimientoPassword.objects.create(
            usuario=usuario, identificador_ingresado='olvido_bitacora', estado='aprobada',
        )

        self.crear('nuevo_bitacora', PASSWORD_FUERTE)
        self.asignar_temporal(solicitud, 'Temporal-Cooperativa-2026')

        textos = ' '.join(Bitacora.objects.values_list('descripcion', flat=True))
        self.assertNotIn(PASSWORD_FUERTE, textos)
        self.assertNotIn('Temporal-Cooperativa-2026', textos)

    def test_cuentas_existentes_conservan_su_password(self):
        existente = crear_usuario('existente_debil', ROL_EJECUTOR_OPERATIVO)
        existente.set_password('123')  # contraseña previa a la política
        existente.save()

        response = self.client.patch(self.url_usuario(existente), {'first_name': 'Edita'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        existente.refresh_from_db()
        self.assertTrue(existente.check_password('123'))
        self.assertFalse(existente.debe_cambiar_password)

    def url_usuario(self, usuario):
        return f'/api/usuarios/{usuario.id}/'


# ---------------------------------------------------------------- B2

LIMITES_PRUEBA = {
    'login_ip': '6/minute',
    'login_usuario': '3/minute',
    'restablecimiento_ip': '5/hour',
    'restablecimiento_identificador': '2/hour',
}


@override_settings(SNIFF_LIMITES_SOLICITUDES=LIMITES_PRUEBA)
class LimiteIntentosTests(SeguridadBase):
    def login(self, username, password='incorrecta', **extra):
        return self.client.post(URL_LOGIN, {'username': username, 'password': password}, **extra)

    def recuperar(self, identificador, **extra):
        return self.client.post(URL_RECUPERAR, {'identificador': identificador}, **extra)

    def test_login_limite_por_usuario_responde_429_controlado(self):
        crear_usuario('victima')

        for _ in range(3):
            self.assertEqual(self.login('victima').status_code, status.HTTP_401_UNAUTHORIZED)

        response = self.login('victima', PASSWORD_PRUEBA)

        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertIn('Demasiados intentos', str(response.data['detail']))
        self.assertIn('Retry-After', response)

    def test_login_limite_por_ip(self):
        for indice in range(6):
            self.login(f'usuario_{indice}')

        self.assertEqual(self.login('usuario_nuevo').status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_x_forwarded_for_no_evade_el_limite_por_ip(self):
        for indice in range(6):
            self.login(f'spoof_{indice}', HTTP_X_FORWARDED_FOR=f'10.0.0.{indice}')

        response = self.login('spoof_final', HTTP_X_FORWARDED_FOR='10.0.0.99')

        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_el_limite_no_bloquea_la_cuenta_de_forma_permanente(self):
        usuario = crear_usuario('bloqueo_temporal')

        for _ in range(4):
            self.login('bloqueo_temporal')

        self.assertEqual(self.login('bloqueo_temporal', PASSWORD_PRUEBA).status_code, 429)

        cache.clear()  # equivale a que termine la ventana del límite

        self.assertEqual(self.login('bloqueo_temporal', PASSWORD_PRUEBA).status_code, status.HTTP_200_OK)
        usuario.refresh_from_db()
        self.assertTrue(usuario.is_active)

    def test_otros_usuarios_no_se_ven_afectados_por_el_limite_de_una_cuenta(self):
        crear_usuario('cuenta_atacada')
        crear_usuario('cuenta_normal')

        for _ in range(3):
            self.login('cuenta_atacada')

        self.assertEqual(self.login('cuenta_normal', PASSWORD_PRUEBA).status_code, status.HTTP_200_OK)

    def test_recuperacion_no_revela_si_la_cuenta_existe(self):
        crear_usuario('existe_recupera')

        existente = [self.recuperar('existe_recupera') for _ in range(3)]
        cache.clear()
        inexistente = [self.recuperar('no_existe_recupera') for _ in range(3)]

        self.assertEqual([r.status_code for r in existente], [200, 200, 429])
        self.assertEqual([r.status_code for r in inexistente], [200, 200, 429])
        self.assertEqual(existente[0].data, inexistente[0].data)
        self.assertEqual(existente[2].data, inexistente[2].data)

    def test_recuperacion_limite_por_ip(self):
        for indice in range(5):
            self.assertEqual(self.recuperar(f'cuenta_{indice}').status_code, status.HTTP_200_OK)

        self.assertEqual(self.recuperar('cuenta_extra').status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_recuperacion_sigue_creando_la_solicitud_dentro_del_limite(self):
        usuario = crear_usuario('flujo_recupera')

        response = self.recuperar('flujo_recupera')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(SolicitudRestablecimientoPassword.objects.filter(usuario=usuario, estado='pendiente').exists())

    def test_cuerpo_no_dict_no_produce_error_500(self):
        response = self.client.post(URL_LOGIN, ['no', 'es', 'dict'], format='json')

        self.assertLess(response.status_code, 500)

    @override_settings(SNIFF_LIMITES_SOLICITUDES={**LIMITES_PRUEBA, 'login_usuario': '', 'login_ip': ''})
    def test_un_limite_vacio_queda_desactivado(self):
        crear_usuario('sin_limite')

        for _ in range(8):
            self.assertEqual(self.login('sin_limite').status_code, status.HTTP_401_UNAUTHORIZED)
