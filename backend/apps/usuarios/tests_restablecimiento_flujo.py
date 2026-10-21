"""Solicitudes de restablecimiento de contraseña: la aprobación y la
asignación de la contraseña temporal son operaciones independientes.

  Pendiente  -> aprobar o rechazar (sin observación obligatoria).
  Aprobada   -> asignar contraseña temporal, una sola vez (pasa a Atendida).
  Atendida / Rechazada -> sin acciones."""

from unittest import mock, skipUnless

from django.core.cache import cache
from django.db import connection, transaction
from rest_framework import status
from rest_framework.test import APITestCase

from apps.auditoria.models import Bitacora, Notificacion

from .models import Rol, SolicitudRestablecimientoPassword, Usuario

URL = '/api/solicitudes-restablecimiento/'
PASSWORD_ORIGINAL = 'Original-Sniff-2026'
PASSWORD_TEMPORAL = 'Temporal-Cooperativa-2026'
PASSWORD_NUEVO = 'Definitiva-Cooperativa-2027'
MODULO = 'Restablecimiento de contraseña'


def crear_usuario(username, rol_nombre):
    rol, _ = Rol.objects.get_or_create(nombre=rol_nombre, defaults={'descripcion': 'Rol de prueba', 'estado': True})
    usuario = Usuario.objects.create_user(username=username, password=PASSWORD_ORIGINAL)
    usuario.rol = rol
    usuario.correo = f'{username}@sniff.test'
    usuario.save()
    return usuario


class FlujoRestablecimientoBase(APITestCase):
    def setUp(self):
        cache.clear()
        self.admin = crear_usuario('admin_sistema_rest', 'Administrador del sistema')
        self.olvido = crear_usuario('olvido_rest', 'Ejecutor operativo')

    def pedir_restablecimiento(self):
        self.client.force_authenticate(user=None)
        respuesta = self.client.post(
            '/api/usuarios/solicitar-restablecimiento/', {'identificador': self.olvido.username}, format='json',
        )
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        return SolicitudRestablecimientoPassword.objects.get(usuario=self.olvido)

    def accion(self, solicitud, nombre, datos=None, usuario=None):
        self.client.force_authenticate(user=usuario or self.admin)
        return self.client.post(f'{URL}{solicitud.id}/{nombre}/', datos or {}, format='json')

    def asignar(self, solicitud, password=PASSWORD_TEMPORAL):
        return self.accion(solicitud, 'asignar-password-temporal', {'password_temporal': password})

    def bitacoras(self):
        return list(Bitacora.objects.filter(modulo=MODULO).order_by('id').values_list('descripcion', flat=True))

    def assertPasswordOriginal(self):
        self.olvido.refresh_from_db()
        self.assertTrue(self.olvido.check_password(PASSWORD_ORIGINAL))
        self.assertFalse(self.olvido.debe_cambiar_password)


class AprobacionTests(FlujoRestablecimientoBase):
    def test_aprobar_sin_observacion_solo_cambia_el_estado(self):
        solicitud = self.pedir_restablecimiento()

        respuesta = self.accion(solicitud, 'aprobar')

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        solicitud.refresh_from_db()
        self.assertEqual(solicitud.estado, 'aprobada')
        self.assertEqual(solicitud.revisado_por, self.admin)
        self.assertIsNotNone(solicitud.fecha_revision)
        self.assertEqual(solicitud.observacion_admin, '')
        # Aprobar no asigna ni genera ninguna contraseña.
        self.assertIsNone(solicitud.atendido_por)
        self.assertIsNone(solicitud.fecha_atencion)
        self.assertPasswordOriginal()
        self.assertTrue(self.bitacoras()[-1].startswith(f'Aprobó la solicitud de restablecimiento #{solicitud.id}'))

    def test_no_se_aprueba_dos_veces_ni_algo_ya_resuelto(self):
        solicitud = self.pedir_restablecimiento()
        self.accion(solicitud, 'aprobar')
        registros = len(self.bitacoras())

        for nombre in ('aprobar', 'rechazar'):
            respuesta = self.accion(solicitud, nombre)
            self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertEqual(len(self.bitacoras()), registros)
        solicitud.refresh_from_db()
        self.assertEqual(solicitud.estado, 'aprobada')

    def test_rechazar_una_solicitud(self):
        solicitud = self.pedir_restablecimiento()

        respuesta = self.accion(solicitud, 'rechazar')

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        solicitud.refresh_from_db()
        self.assertEqual(solicitud.estado, 'rechazada')
        self.assertEqual(solicitud.revisado_por, self.admin)
        self.assertPasswordOriginal()
        self.assertTrue(self.bitacoras()[-1].startswith(f'Rechazó la solicitud de restablecimiento #{solicitud.id}'))

        # Rechazada: no admite aprobación ni asignación.
        self.assertEqual(self.accion(solicitud, 'aprobar').status_code, status.HTTP_400_BAD_REQUEST)
        asignar = self.asignar(solicitud)
        self.assertEqual(asignar.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('rechazada', asignar.data['detail'])
        self.assertPasswordOriginal()


class AsignacionTests(FlujoRestablecimientoBase):
    def test_no_se_asigna_contrasena_a_una_solicitud_pendiente(self):
        solicitud = self.pedir_restablecimiento()

        respuesta = self.asignar(solicitud)

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Primero hay que aprobar', respuesta.data['detail'])
        solicitud.refresh_from_db()
        self.assertEqual(solicitud.estado, 'pendiente')
        self.assertIsNone(solicitud.revisado_por)
        self.assertPasswordOriginal()

    def test_asignar_despues_de_aprobar_y_mantener_el_cambio_obligatorio(self):
        solicitud = self.pedir_restablecimiento()
        self.accion(solicitud, 'aprobar')

        respuesta = self.asignar(solicitud)

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        solicitud.refresh_from_db()
        self.olvido.refresh_from_db()
        self.assertEqual(solicitud.estado, 'atendida')
        self.assertEqual(solicitud.atendido_por, self.admin)
        self.assertTrue(self.olvido.check_password(PASSWORD_TEMPORAL))
        self.assertTrue(self.olvido.debe_cambiar_password)

        # Con la temporal, la API queda bloqueada hasta cambiarla.
        self.client.force_authenticate(user=None)
        login = self.client.post('/api/auth/login/', {'username': self.olvido.username, 'password': PASSWORD_TEMPORAL}, format='json')
        self.assertEqual(login.status_code, status.HTTP_200_OK)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
        self.assertEqual(self.client.get('/api/notificaciones/').status_code, status.HTTP_403_FORBIDDEN)

        cambio = self.client.post('/api/usuarios/cambiar-password/', {
            'password_actual': PASSWORD_TEMPORAL,
            'password_nuevo': PASSWORD_NUEVO,
            'password_confirmacion': PASSWORD_NUEVO,
        }, format='json')
        self.assertEqual(cambio.status_code, status.HTTP_200_OK)
        self.olvido.refresh_from_db()
        self.assertFalse(self.olvido.debe_cambiar_password)

    def test_no_se_permite_una_segunda_asignacion(self):
        solicitud = self.pedir_restablecimiento()
        self.accion(solicitud, 'aprobar')
        self.asignar(solicitud)
        registros = len(self.bitacoras())

        respuesta = self.asignar(solicitud, 'Otra-Temporal-Distinta-2026')

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('ya tiene una contraseña temporal asignada', respuesta.data['detail'])
        self.olvido.refresh_from_db()
        self.assertTrue(self.olvido.check_password(PASSWORD_TEMPORAL))
        self.assertEqual(len(self.bitacoras()), registros)
        # Atendida: tampoco se aprueba ni se rechaza.
        for nombre in ('aprobar', 'rechazar'):
            self.assertEqual(self.accion(solicitud, nombre).status_code, status.HTTP_400_BAD_REQUEST)

    def test_contrasena_debil_no_consume_la_solicitud(self):
        solicitud = self.pedir_restablecimiento()
        self.accion(solicitud, 'aprobar')

        respuesta = self.asignar(solicitud, '12345678')

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password_temporal', respuesta.data)
        solicitud.refresh_from_db()
        self.assertEqual(solicitud.estado, 'aprobada')
        self.assertPasswordOriginal()
        # Sigue pudiendo asignarse una válida.
        self.assertEqual(self.asignar(solicitud).status_code, status.HTTP_200_OK)

    def test_falla_de_bitacora_revierte_la_asignacion(self):
        solicitud = self.pedir_restablecimiento()
        self.accion(solicitud, 'aprobar')

        with mock.patch('apps.auditoria.services.registrar_bitacora', side_effect=RuntimeError('BD caída')):
            respuesta = self.asignar(solicitud)

        self.assertEqual(respuesta.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        solicitud.refresh_from_db()
        self.assertEqual(solicitud.estado, 'aprobada')
        self.assertPasswordOriginal()


class NotificacionesYPermisosTests(FlujoRestablecimientoBase):
    def test_flujo_completo_conserva_notificacion_y_bitacora(self):
        solicitud = self.pedir_restablecimiento()

        aviso = Notificacion.objects.get(usuario_destino=self.admin)
        self.assertIn(f'resaltarSolicitud={solicitud.id}', aviso.enlace)

        self.accion(solicitud, 'aprobar')
        self.asignar(solicitud)

        descripciones = self.bitacoras()
        self.assertTrue(any(d.startswith('Aprobó la solicitud') for d in descripciones))
        self.assertTrue(any(d.startswith(f'Asignó contraseña temporal al usuario {self.olvido.username}') for d in descripciones))
        self.assertNotIn(PASSWORD_TEMPORAL, ' '.join(descripciones))
        # Aprobar y asignar no generan avisos nuevos: solo el de la solicitud.
        self.assertEqual(Notificacion.objects.filter(usuario_destino=self.admin).count(), 1)

    def test_solo_el_administrador_del_sistema_gestiona_las_solicitudes(self):
        solicitud = self.pedir_restablecimiento()

        for rol in ('Administrador de planificación', 'Ejecutor operativo', 'Usuario de consulta'):
            otro = crear_usuario(f'otro_{rol[:6].strip()}', rol)
            for nombre in ('aprobar', 'rechazar'):
                self.assertEqual(self.accion(solicitud, nombre, usuario=otro).status_code, status.HTTP_403_FORBIDDEN)
            self.client.force_authenticate(user=otro)
            self.assertEqual(
                self.client.post(
                    f'{URL}{solicitud.id}/asignar-password-temporal/', {'password_temporal': PASSWORD_TEMPORAL}, format='json',
                ).status_code,
                status.HTTP_403_FORBIDDEN,
            )

        solicitud.refresh_from_db()
        self.assertEqual(solicitud.estado, 'pendiente')
        self.assertPasswordOriginal()


class ConsultaBloqueoTests(FlujoRestablecimientoBase):
    """Regresión: en PostgreSQL, select_for_update() con select_related de
    relaciones opcionales (LEFT OUTER JOIN) lanzaba NotSupportedError ("FOR
    UPDATE no puede ser aplicado al lado nulable de un outer join") y la
    asignación de la contraseña temporal respondía 500. SQLite no reproduce
    el error (ignora FOR UPDATE), así que se comprueba la estructura de la
    consulta; la prueba de abajo la ejecuta de verdad si el motor es
    PostgreSQL."""

    def test_bloquea_solo_la_fila_de_la_solicitud_sin_outer_join(self):
        from .views import consulta_bloqueo_solicitud_restablecimiento

        consulta = consulta_bloqueo_solicitud_restablecimiento()

        self.assertTrue(consulta.query.select_for_update)
        self.assertEqual(consulta.query.select_for_update_of, ('self',))
        self.assertNotIn('LEFT OUTER JOIN', str(consulta.query).upper())
        self.assertNotIn('revisado_por', consulta.query.select_related)
        self.assertNotIn('atendido_por', consulta.query.select_related)

    def test_las_tres_acciones_funcionan_con_revisor_y_atencion_vacios(self):
        aprobar = self.pedir_restablecimiento()
        self.assertEqual(self.accion(aprobar, 'aprobar').status_code, status.HTTP_200_OK)
        self.assertEqual(self.asignar(aprobar).status_code, status.HTTP_200_OK)

        SolicitudRestablecimientoPassword.objects.filter(pk=aprobar.pk).delete()
        rechazar = self.pedir_restablecimiento()
        respuesta = self.accion(rechazar, 'rechazar')
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertIsNone(respuesta.data.get('atendido_por'))


@skipUnless(connection.vendor == 'postgresql', 'Solo PostgreSQL rechaza FOR UPDATE sobre un outer join.')
class ConsultaBloqueoPostgreSQLTests(FlujoRestablecimientoBase):
    def test_la_consulta_de_bloqueo_se_ejecuta_en_postgresql(self):
        from .views import consulta_bloqueo_solicitud_restablecimiento

        solicitud = self.pedir_restablecimiento()

        with transaction.atomic():
            bloqueada = consulta_bloqueo_solicitud_restablecimiento().get(pk=solicitud.pk)

        self.assertEqual(bloqueada.pk, solicitud.pk)
