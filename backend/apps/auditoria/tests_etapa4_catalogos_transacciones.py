"""Etapa 4 (continuación): bitácora de catálogos (Rangos, Metas, Frecuencias,
Estados de cumplimiento) y verificación de ATOMIC_REQUESTS con commits
reales (TransactionTestCase), incluido el login y sus intentos fallidos."""

from datetime import date
from decimal import Decimal
from unittest import mock

from django.core.cache import cache
from django.db import IntegrityError
from django.test import TransactionTestCase
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from apps.estrategia.models import Area, ObjetivoEspecifico, ObjetivoGeneral, PlanAnual, PlanEstrategico
from apps.indicadores.models import (
    EstadoCumplimiento,
    Frecuencia,
    IndicadorKPI,
    Medicion,
    MetaKPI,
    RangoKPI,
)
from apps.indicadores.rangos_de_prueba import configurar_rangos_70_85
from apps.indicadores.services import (
    obtener_estado_para_medicion,
    obtener_o_crear_meta_vigente,
    obtener_o_crear_periodo,
)
from apps.usuarios.models import Rol, SolicitudRestablecimientoPassword, Usuario

from .models import Bitacora, Notificacion

PASSWORD = 'Cooperativa-Segura-2026'
CUATRO_ROLES = (
    'Administrador del sistema',
    'Administrador de planificación',
    'Ejecutor operativo',
    'Usuario de consulta',
)


def crear_usuario(username, rol_nombre, **extra):
    rol, _ = Rol.objects.get_or_create(nombre=rol_nombre, defaults={'descripcion': 'Rol de prueba', 'estado': True})
    usuario = Usuario.objects.create_user(username=username, password=PASSWORD, **extra)
    usuario.rol = rol
    usuario.correo = f'{username}@sniff.test'
    usuario.save()
    return usuario


class BitacoraCatalogosTests(APITestCase):
    def setUp(self):
        self.admin = crear_usuario('admin_catalogos', 'Administrador de planificación')
        self.client.force_authenticate(user=self.admin)

        for nombre, color in [('Incumplido', 'rojo'), ('En riesgo', 'amarillo'), ('Favorable', 'verde')]:
            EstadoCumplimiento.objects.get_or_create(nombre=nombre, defaults={'color': color, 'estado': True})

        self.frecuencia = Frecuencia.objects.create(nombre='Mensual', estado=True)
        plan = PlanEstrategico.objects.create(
            titulo='Plan catálogos', fecha_inicio=date(2027, 1, 1), fecha_fin=date(2030, 12, 31),
            estado=PlanEstrategico.ESTADO_EN_USO, creado_por=self.admin,
        )
        objetivo_general = ObjetivoGeneral.objects.create(
            plan_estrategico=plan, texto_objetivo='OG', creado_por=self.admin,
        )
        plan_anual = PlanAnual.objects.create(
            plan_estrategico=plan, anio=2027, estado=PlanAnual.ESTADO_EN_USO,
            fecha_inicio=date(2027, 1, 1), fecha_fin=date(2027, 12, 31), creado_por=self.admin,
        )
        objetivo_especifico = ObjetivoEspecifico.objects.create(
            plan_anual=plan_anual, objetivo_general=objetivo_general, texto_objetivo='OE', creado_por=self.admin,
        )
        self.kpi = IndicadorKPI.objects.create(
            objetivo_especifico=objetivo_especifico, frecuencia=self.frecuencia, nombre='KPI catálogos',
            formula_medicion='Resultado', unidad_medida='%', valor_meta=Decimal('85'),
            estado='autorizado', creado_por=self.admin,
        )
        configurar_rangos_70_85(self.kpi)

    def registros(self, modulo):
        return list(Bitacora.objects.filter(modulo=modulo).order_by('id').values_list('accion', 'descripcion'))

    def test_rangos_kpi(self):
        rango = RangoKPI.objects.get(indicador=self.kpi, estado_cumplimiento__nombre='Favorable')

        # D3: 90 no se superpone con En riesgo (70 a menos de 85).
        self.client.patch(f'/api/rangos-kpi/{rango.id}/', {'valor_minimo': '90'}, format='json')
        self.client.patch(f'/api/rangos-kpi/{rango.id}/', {'valor_minimo': '90'}, format='json')  # sin cambio
        self.client.patch(f'/api/rangos-kpi/{rango.id}/', {'estado': False}, format='json')

        registros = self.registros('Rangos KPI')
        self.assertEqual(len(registros), 2)
        self.assertEqual(registros[0][0], 'actualizar')
        self.assertIn('rango "Favorable" del KPI KPI catálogos', registros[0][1])
        self.assertIn('valor_minimo: 85.0000 → 90', registros[0][1])
        self.assertEqual(registros[1], ('eliminar', 'Desactivó el rango "Favorable" del KPI KPI catálogos.'))
        self.assertEqual(Bitacora.objects.get(modulo='Rangos KPI', accion='actualizar').usuario, self.admin)

    def test_cambiar_un_rango_no_recalcula_mediciones_historicas(self):
        periodo = obtener_o_crear_periodo(self.kpi, date(2027, 1, 1))
        meta = obtener_o_crear_meta_vigente(self.kpi)
        medicion = Medicion.objects.create(
            indicador=self.kpi, meta=meta, periodo=periodo,
            estado_cumplimiento=obtener_estado_para_medicion(self.kpi, meta, Decimal('82')),
            registrado_por=self.admin, fecha_medicion=periodo.fecha_fin, valor_resultado=Decimal('82'),
        )
        en_riesgo = RangoKPI.objects.get(indicador=self.kpi, estado_cumplimiento__nombre='En riesgo')
        favorable = RangoKPI.objects.get(indicador=self.kpi, estado_cumplimiento__nombre='Favorable')

        # Con los rangos nuevos 82 sería Favorable (D3: sin superponerse,
        # primero se acorta En riesgo y después se baja Favorable).
        self.assertEqual(self.client.patch(f'/api/rangos-kpi/{en_riesgo.id}/', {'valor_maximo': '80'}, format='json').status_code, 200)
        self.assertEqual(self.client.patch(f'/api/rangos-kpi/{favorable.id}/', {'valor_minimo': '80'}, format='json').status_code, 200)

        medicion.refresh_from_db()
        self.assertEqual(medicion.estado_cumplimiento.nombre, 'En riesgo')

    def test_metas(self):
        meta = obtener_o_crear_meta_vigente(self.kpi)

        self.client.patch(f'/api/metas-kpi/{meta.id}/', {'valor_meta': '90'}, format='json')

        accion, descripcion = self.registros('Metas KPI')[0]
        self.assertEqual(accion, 'actualizar')
        self.assertIn(f'la meta #{meta.id} del KPI KPI catálogos', descripcion)
        self.assertIn('valor_meta: 85.0000 → 90', descripcion)

    def test_frecuencias(self):
        respuesta = self.client.post('/api/frecuencias/', {'nombre': 'Quincenal'}, format='json')
        self.client.patch(f'/api/frecuencias/{respuesta.data["id"]}/', {'descripcion': 'Cada 15 días'}, format='json')

        self.assertEqual(self.registros('Frecuencias'), [
            ('crear', 'Creó la frecuencia Quincenal.'),
            ('actualizar', 'Actualizó la frecuencia Quincenal (descripcion: vacío → Cada 15 días).'),
        ])

    def test_estados_de_cumplimiento(self):
        respuesta = self.client.post('/api/estados-cumplimiento/', {'nombre': 'Destacado', 'color': 'verde'}, format='json')
        self.client.patch(f'/api/estados-cumplimiento/{respuesta.data["id"]}/', {'color': 'azul'}, format='json')

        self.assertEqual(self.registros('Estados de cumplimiento'), [
            ('crear', 'Creó el estado de cumplimiento Destacado.'),
            ('actualizar', 'Actualizó el estado de cumplimiento Destacado (color: verde → azul).'),
        ])

    def test_otros_tres_roles_no_modifican_catalogos_ni_dejan_registro(self):
        rango = RangoKPI.objects.filter(indicador=self.kpi).first()

        for indice, rol in enumerate(CUATRO_ROLES):
            if rol == 'Administrador de planificación':
                continue

            self.client.force_authenticate(user=crear_usuario(f'otro_rol_{indice}', rol))
            respuestas = [
                self.client.patch(f'/api/rangos-kpi/{rango.id}/', {'valor_minimo': '1'}, format='json'),
                self.client.post('/api/frecuencias/', {'nombre': f'Intento {indice}'}, format='json'),
                self.client.post('/api/estados-cumplimiento/', {'nombre': f'Intento {indice}', 'color': 'rojo'}, format='json'),
            ]

            for respuesta in respuestas:
                self.assertEqual(respuesta.status_code, status.HTTP_403_FORBIDDEN, rol)

        self.assertFalse(Bitacora.objects.filter(modulo__in=['Rangos KPI', 'Frecuencias', 'Estados de cumplimiento']).exists())

    def test_fallo_de_bitacora_revierte_el_cambio_de_catalogo(self):
        rango = RangoKPI.objects.get(indicador=self.kpi, estado_cumplimiento__nombre='Favorable')

        with mock.patch('apps.auditoria.services.registrar_bitacora', side_effect=RuntimeError('BD caída')):
            respuesta = self.client.patch(f'/api/rangos-kpi/{rango.id}/', {'valor_minimo': '90'}, format='json')

        self.assertEqual(respuesta.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        rango.refresh_from_db()
        self.assertEqual(rango.valor_minimo, Decimal('85'))


class AtomicidadConCommitsRealesTests(TransactionTestCase):
    """ATOMIC_REQUESTS verificado sin la transacción envolvente de TestCase:
    lo que se ve acá es lo que queda confirmado en la base de datos."""

    def setUp(self):
        cache.clear()
        self.cliente = APIClient()
        self.admin_sistema = crear_usuario('tx_admin_sistema', 'Administrador del sistema')
        self.admin = crear_usuario('tx_admin_planif', 'Administrador de planificación')
        self.ejecutor = crear_usuario('tx_ejecutor', 'Ejecutor operativo')

    def tearDown(self):
        cache.clear()

    def login(self, username, password=PASSWORD):
        return self.cliente.post('/api/auth/login/', {'username': username, 'password': password}, format='json')

    def test_intento_fallido_queda_confirmado_aunque_la_respuesta_sea_401(self):
        respuesta = self.login(self.ejecutor.username, 'incorrecta')

        self.assertEqual(respuesta.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertTrue(Bitacora.objects.filter(usuario=self.ejecutor, accion='error').exists())

    def test_login_exitoso_confirma_bitacora_y_ultimo_acceso(self):
        respuesta = self.login(self.ejecutor.username)

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(Bitacora.objects.filter(usuario=self.ejecutor, accion='inicio_sesion').count(), 1)
        self.ejecutor.refresh_from_db()
        self.assertIsNotNone(self.ejecutor.ultimo_acceso)

    def test_login_con_bitacora_caida_no_confirma_nada_ni_entrega_tokens(self):
        with mock.patch('apps.auditoria.services.registrar_bitacora', side_effect=RuntimeError('BD caída')):
            respuesta = self.login(self.ejecutor.username)

        self.assertEqual(respuesta.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertNotIn('access', respuesta.data)
        self.ejecutor.refresh_from_db()
        self.assertIsNone(self.ejecutor.ultimo_acceso)
        self.assertFalse(Bitacora.objects.filter(accion='inicio_sesion').exists())

    def test_intento_fallido_con_bitacora_caida_sigue_respondiendo_401(self):
        with mock.patch('apps.auditoria.services.registrar_bitacora', side_effect=RuntimeError('BD caída')):
            respuesta = self.login(self.ejecutor.username, 'incorrecta')

        self.assertEqual(respuesta.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_limite_de_intentos_no_deja_registros_parciales(self):
        from django.test import override_settings

        limites = {'login_ip': '', 'login_usuario': '2/minute', 'restablecimiento_ip': '', 'restablecimiento_identificador': ''}

        with override_settings(SNIFF_LIMITES_SOLICITUDES=limites):
            codigos = [self.login(self.ejecutor.username, 'incorrecta').status_code for _ in range(3)]

        self.assertEqual(codigos, [401, 401, 429])
        # El 429 corta antes de autenticar: solo los dos intentos reales quedan registrados.
        self.assertEqual(Bitacora.objects.filter(usuario=self.ejecutor, accion='error').count(), 2)

    def test_operacion_revertida_no_queda_confirmada(self):
        self.cliente.force_authenticate(user=self.admin)

        with mock.patch('apps.auditoria.services.registrar_bitacora', side_effect=RuntimeError('BD caída')):
            respuesta = self.cliente.post('/api/areas/', {'nombre': 'Área revertida'}, format='json')

        self.assertEqual(respuesta.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertFalse(Area.objects.filter(nombre='Área revertida').exists())

    def test_error_de_integridad_controlado_no_responde_exito(self):
        """poner-en-uso de Plan anual atrapa un IntegrityError (carrera con la
        restricción de un solo Plan anual En uso): con ATOMIC_REQUESTS debe
        responder 400, sin confirmar ni el cambio ni su bitácora."""
        plan = PlanEstrategico.objects.create(
            titulo='Plan tx', fecha_inicio=date(2027, 1, 1), fecha_fin=date(2030, 12, 31),
            estado=PlanEstrategico.ESTADO_EN_USO, creado_por=self.admin,
        )
        plan_anual = PlanAnual.objects.create(
            plan_estrategico=plan, anio=2027, fecha_inicio=date(2027, 1, 1), fecha_fin=date(2027, 12, 31),
            creado_por=self.admin,
        )
        self.cliente.force_authenticate(user=self.admin)

        with mock.patch.object(PlanAnual, 'save', side_effect=IntegrityError('carrera')):
            respuesta = self.cliente.post(f'/api/planes-anuales/{plan_anual.id}/poner-en-uso/')

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        plan_anual.refresh_from_db()
        self.assertEqual(plan_anual.estado, PlanAnual.ESTADO_BORRADOR)
        self.assertFalse(Bitacora.objects.filter(descripcion__startswith='Puso en uso el Plan 2027').exists())

    def test_flujo_de_recuperacion_confirma_solicitud_bitacora_y_notificacion(self):
        respuesta = self.cliente.post(
            '/api/usuarios/solicitar-restablecimiento/', {'identificador': self.ejecutor.username}, format='json',
        )

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        solicitud = SolicitudRestablecimientoPassword.objects.get(usuario=self.ejecutor)
        self.assertTrue(Bitacora.objects.filter(modulo='Restablecimiento de contraseña').exists())
        self.assertTrue(Notificacion.objects.filter(usuario_destino=self.admin_sistema).exists())

        self.cliente.force_authenticate(user=self.admin_sistema)
        # La contraseña temporal se asigna solo después de aprobar.
        aprobar = self.cliente.post(f'/api/solicitudes-restablecimiento/{solicitud.id}/aprobar/')
        self.assertEqual(aprobar.status_code, status.HTTP_200_OK)
        asignar = self.cliente.post(
            f'/api/solicitudes-restablecimiento/{solicitud.id}/asignar-password-temporal/',
            {'password_temporal': 'Temporal-Cooperativa-2026'}, format='json',
        )
        self.cliente.force_authenticate(user=None)

        self.assertEqual(asignar.status_code, status.HTTP_200_OK)
        self.assertEqual(self.login(self.ejecutor.username, 'Temporal-Cooperativa-2026').status_code, status.HTTP_200_OK)

    def test_consultas_y_renovacion_funcionan_dentro_de_la_transaccion(self):
        login = self.login(self.ejecutor.username)
        self.cliente.credentials(HTTP_AUTHORIZATION=f'Bearer {login.data["access"]}')

        self.assertEqual(self.cliente.get('/api/planes-estrategicos/').status_code, status.HTTP_200_OK)
        self.assertEqual(self.cliente.get('/api/usuarios/me/').status_code, status.HTTP_200_OK)

        self.cliente.credentials()
        renovado = self.cliente.post('/api/auth/refresh/', {'refresh': login.data['refresh']}, format='json')
        self.assertEqual(renovado.status_code, status.HTTP_200_OK)

        # Un GET no deja nada escrito; solo el inicio de sesión quedó en bitácora.
        self.assertEqual(Bitacora.objects.count(), 1)

    def test_los_cuatro_roles_inician_sesion_con_commits_reales(self):
        crear_usuario('tx_consulta', 'Usuario de consulta')

        for username in ('tx_admin_sistema', 'tx_admin_planif', 'tx_ejecutor', 'tx_consulta'):
            self.assertEqual(self.login(username).status_code, status.HTTP_200_OK, username)

        self.assertEqual(Bitacora.objects.filter(accion='inicio_sesion').count(), 4)
