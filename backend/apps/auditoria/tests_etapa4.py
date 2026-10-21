"""Etapa 4 de correcciones post-auditoría (20/10/2026): alertas y
notificaciones (M6), bitácora (M7), integridad transaccional de las
operaciones con su registro de auditoría y obtención segura de la IP."""

from datetime import date
from decimal import Decimal
from unittest import mock

from django.conf import settings
from django.core.cache import cache
from django.db import IntegrityError
from django.test import RequestFactory, override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.estrategia.models import Area, ObjetivoEspecifico, ObjetivoGeneral, PlanAnual, PlanEstrategico
from apps.indicadores.models import (
    Alerta,
    ConfiguracionMediciones,
    EstadoCumplimiento,
    Frecuencia,
    IndicadorKPI,
    Medicion,
)
from apps.indicadores.services import (
    TIPO_ALERTA_PERIODO_SIN_REGISTRO,
    TIPO_ALERTA_PERIODO_VENCIDO,
    cerrar_mediciones_vencidas,
    crear_rangos_provisionales,
    generar_alertas_periodos_vencidos,
    obtener_estado_para_medicion,
    obtener_o_crear_meta_vigente,
    obtener_o_crear_periodo,
)
from apps.usuarios.models import Rol, Usuario

from .models import Bitacora, Notificacion
from .services import generar_recordatorios_pendientes, obtener_ip_usuario

PASSWORD = 'Cooperativa-Segura-2026'


def crear_usuario(username, rol_nombre, **extra):
    rol, _ = Rol.objects.get_or_create(nombre=rol_nombre, defaults={'descripcion': 'Rol de prueba', 'estado': True})
    usuario = Usuario.objects.create_user(username=username, password=PASSWORD, **extra)
    usuario.rol = rol
    usuario.correo = f'{username}@sniff.test'
    usuario.save()
    return usuario


class Etapa4Base(APITestCase):
    def setUp(self):
        cache.clear()
        self.admin = crear_usuario('admin_planif_e4', 'Administrador de planificación')
        self.admin_sistema = crear_usuario('admin_sistema_e4', 'Administrador del sistema')
        self.ejecutor = crear_usuario('ejecutor_e4', 'Ejecutor operativo')
        self.consulta = crear_usuario('consulta_e4', 'Usuario de consulta')

        for nombre, color in [('Incumplido', 'rojo'), ('En riesgo', 'amarillo'), ('Favorable', 'verde')]:
            EstadoCumplimiento.objects.get_or_create(nombre=nombre, defaults={'color': color, 'estado': True})

        self.frecuencia = Frecuencia.objects.create(nombre='Mensual', estado=True)
        self.plan = PlanEstrategico.objects.create(
            titulo='Plan etapa 4', fecha_inicio=date(2027, 1, 1), fecha_fin=date(2030, 12, 31),
            estado=PlanEstrategico.ESTADO_EN_USO, creado_por=self.admin,
        )
        objetivo_general = ObjetivoGeneral.objects.create(
            plan_estrategico=self.plan, texto_objetivo='Objetivo general etapa 4', creado_por=self.admin,
        )
        self.plan_anual = PlanAnual.objects.create(
            plan_estrategico=self.plan, anio=2027, estado=PlanAnual.ESTADO_EN_USO,
            fecha_inicio=date(2027, 1, 1), fecha_fin=date(2027, 12, 31), creado_por=self.admin,
        )
        self.objetivo_especifico = ObjetivoEspecifico.objects.create(
            plan_anual=self.plan_anual, objetivo_general=objetivo_general,
            texto_objetivo='Objetivo específico etapa 4', creado_por=self.admin,
        )

    def tearDown(self):
        cache.clear()

    def crear_kpi(self, nombre='KPI etapa 4', estado='autorizado'):
        kpi = IndicadorKPI.objects.create(
            objetivo_especifico=self.objetivo_especifico, frecuencia=self.frecuencia, nombre=nombre,
            formula_medicion='Resultado', unidad_medida='%', valor_meta=Decimal('85'),
            estado=estado, creado_por=self.admin,
        )
        crear_rangos_provisionales(kpi)
        return kpi

    def registrar_manual(self, kpi, mes, valor):
        periodo = obtener_o_crear_periodo(kpi, date(2027, mes, 1))
        meta = obtener_o_crear_meta_vigente(kpi)
        return Medicion.objects.create(
            indicador=kpi, meta=meta, periodo=periodo,
            estado_cumplimiento=obtener_estado_para_medicion(kpi, meta, Decimal(valor)),
            registrado_por=self.ejecutor, fecha_medicion=periodo.fecha_fin, valor_resultado=Decimal(valor),
        )

    def alertas_vencido(self, kpi):
        return Alerta.objects.filter(indicador=kpi, tipo_alerta=TIPO_ALERTA_PERIODO_VENCIDO)

    def ultima_bitacora(self, **filtros):
        return Bitacora.objects.filter(**filtros).order_by('-id').first()


# ====================================================================== M6

class AlertasPeriodoTests(Etapa4Base):
    def test_sin_alerta_antes_del_cierre_del_periodo(self):
        kpi = self.crear_kpi()

        generar_alertas_periodos_vencidos(fecha_referencia=date(2027, 1, 31))

        self.assertFalse(self.alertas_vencido(kpi).exists())

    def test_dentro_del_plazo_la_alerta_indica_hasta_cuando_registrar(self):
        kpi = self.crear_kpi()

        generar_alertas_periodos_vencidos(fecha_referencia=date(2027, 2, 2))

        mensaje = self.alertas_vencido(kpi).get().mensaje
        self.assertIn('pendiente el registro del periodo de enero 2027', mensaje)
        self.assertIn('hasta el 05/02/2027', mensaje)
        self.assertNotIn('vencido', mensaje)

    def test_fuera_del_plazo_la_alerta_indica_que_vencio(self):
        kpi = self.crear_kpi()

        generar_alertas_periodos_vencidos(fecha_referencia=date(2027, 2, 6))

        mensaje = self.alertas_vencido(kpi).get().mensaje
        self.assertIn('tiene vencido el periodo de enero 2027', mensaje)
        self.assertIn('terminó el 05/02/2027', mensaje)

    def test_respeta_el_plazo_configurado(self):
        configuracion = ConfiguracionMediciones.obtener()
        configuracion.dias_plazo_registro = 10
        configuracion.save()
        kpi = self.crear_kpi()

        generar_alertas_periodos_vencidos(fecha_referencia=date(2027, 2, 9))

        self.assertIn('hasta el 10/02/2027', self.alertas_vencido(kpi).get().mensaje)

    def test_no_alerta_kpi_de_plan_anual_cerrado(self):
        kpi = self.crear_kpi()
        self.plan_anual.estado = PlanAnual.ESTADO_CERRADO
        self.plan_anual.save(update_fields=['estado'])

        generar_alertas_periodos_vencidos(fecha_referencia=date(2027, 2, 6))

        self.assertFalse(self.alertas_vencido(kpi).exists())

    def test_no_alerta_kpi_de_plan_estrategico_cerrado(self):
        kpi = self.crear_kpi()
        self.plan.estado = PlanEstrategico.ESTADO_CERRADO
        self.plan.save(update_fields=['estado'])

        generar_alertas_periodos_vencidos(fecha_referencia=date(2027, 2, 6))

        self.assertFalse(self.alertas_vencido(kpi).exists())

    def test_no_alerta_kpi_anulado_ni_en_borrador(self):
        anulado = self.crear_kpi('KPI anulado', estado='anulado')
        borrador = self.crear_kpi('KPI borrador', estado='borrador')

        generar_alertas_periodos_vencidos(fecha_referencia=date(2027, 2, 6))

        self.assertFalse(Alerta.objects.filter(indicador__in=[anulado, borrador]).exists())

    def test_no_duplica_la_alerta_del_mismo_periodo(self):
        kpi = self.crear_kpi()

        generar_alertas_periodos_vencidos(fecha_referencia=date(2027, 2, 2))
        resultado = generar_alertas_periodos_vencidos(fecha_referencia=date(2027, 2, 4))

        self.assertEqual(self.alertas_vencido(kpi).count(), 1)
        self.assertEqual(resultado['omitidas'], 1)

    def test_nombre_de_kpi_con_un_periodo_no_confunde_la_deduplicacion(self):
        """Antes se buscaba solo "febrero 2027" en el mensaje: la alerta de
        enero de un KPI llamado "... febrero 2027" bloqueaba la de febrero."""
        kpi = self.crear_kpi('Recuperación febrero 2027')

        generar_alertas_periodos_vencidos(fecha_referencia=date(2027, 2, 2))
        self.registrar_manual(kpi, 1, '90')
        generar_alertas_periodos_vencidos(fecha_referencia=date(2027, 3, 2))

        mensajes = list(self.alertas_vencido(kpi).values_list('mensaje', flat=True))
        self.assertEqual(len(mensajes), 2)
        self.assertTrue(any('periodo de febrero 2027 (' in m for m in mensajes))

    def test_tres_tipos_de_alerta_distintos(self):
        """Incumplimiento del resultado, periodo pendiente/vencido y periodo
        cerrado sin registro conviven sin mezclarse."""
        kpi = self.crear_kpi()
        self.client.force_authenticate(user=self.ejecutor)
        with mock.patch('apps.indicadores.services.hoy', return_value=date(2027, 1, 31)):
            self.client.post('/api/mediciones/', {'indicador': kpi.id, 'valor_resultado': '50'})

        generar_alertas_periodos_vencidos(fecha_referencia=date(2027, 3, 2))   # febrero pendiente
        cerrar_mediciones_vencidas(fecha_referencia=date(2027, 3, 6))         # febrero sin registro

        tipos = dict(Alerta.objects.filter(indicador=kpi).values_list('tipo_alerta', 'estado_alerta'))
        self.assertEqual(tipos['KPI Incumplido'], 'pendiente')
        self.assertEqual(tipos[TIPO_ALERTA_PERIODO_VENCIDO], 'descartada')
        self.assertEqual(tipos[TIPO_ALERTA_PERIODO_SIN_REGISTRO], 'pendiente')


class AlertasVigentesYPermisosTests(Etapa4Base):
    def setUp(self):
        super().setUp()
        self.kpi = self.crear_kpi('KPI vigente')
        self.kpi_anulado = self.crear_kpi('KPI luego anulado')
        self.alerta = Alerta.objects.create(indicador=self.kpi, tipo_alerta='KPI En riesgo', mensaje='Vigente')
        self.alerta_anulado = Alerta.objects.create(
            indicador=self.kpi_anulado, tipo_alerta='KPI En riesgo', mensaje='De KPI anulado',
        )
        IndicadorKPI.objects.filter(pk=self.kpi_anulado.pk).update(estado='anulado')

    def ids(self, response):
        return {a['id'] for a in response.data}

    def test_vigentes_excluye_kpi_anulados_y_planes_cerrados(self):
        self.client.force_authenticate(user=self.admin)

        todas = self.client.get('/api/alertas/', {'estado_alerta': 'pendiente'})
        vigentes = self.client.get('/api/alertas/', {'estado_alerta': 'pendiente', 'vigentes': 1})

        self.assertEqual(self.ids(todas), {self.alerta.id, self.alerta_anulado.id})
        self.assertEqual(self.ids(vigentes), {self.alerta.id})

        self.plan_anual.estado = PlanAnual.ESTADO_CERRADO
        self.plan_anual.save(update_fields=['estado'])
        self.assertEqual(self.ids(self.client.get('/api/alertas/', {'vigentes': 1})), set())

    def test_las_alertas_excluidas_se_conservan_como_historial(self):
        self.client.force_authenticate(user=self.admin)

        self.client.post('/api/alertas/marcar-todas-revisadas/')

        self.alerta.refresh_from_db()
        self.alerta_anulado.refresh_from_db()
        self.assertEqual(self.alerta.estado_alerta, 'revisada')
        self.assertEqual(self.alerta_anulado.estado_alerta, 'pendiente')

    def test_alertas_no_se_crean_ni_editan_por_api(self):
        self.client.force_authenticate(user=self.admin)

        respuestas = [
            self.client.post('/api/alertas/', {'indicador': self.kpi.id, 'tipo_alerta': 'X', 'mensaje': 'X'}),
            self.client.patch(f'/api/alertas/{self.alerta.id}/', {'estado_alerta': 'descartada'}),
            self.client.put(f'/api/alertas/{self.alerta.id}/', {'mensaje': 'Otro'}),
            self.client.delete(f'/api/alertas/{self.alerta.id}/'),
        ]

        for response in respuestas:
            self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        self.alerta.refresh_from_db()
        self.assertEqual((self.alerta.estado_alerta, self.alerta.mensaje), ('pendiente', 'Vigente'))

    def test_solo_admin_planificacion_revisa_alertas(self):
        for usuario in (self.ejecutor, self.consulta, self.admin_sistema):
            self.client.force_authenticate(user=usuario)
            self.assertEqual(
                self.client.post(f'/api/alertas/{self.alerta.id}/marcar-revisada/').status_code,
                status.HTTP_403_FORBIDDEN,
            )
            self.assertEqual(self.client.get('/api/alertas/').status_code, status.HTTP_200_OK)

        self.alerta.refresh_from_db()
        self.assertEqual(self.alerta.estado_alerta, 'pendiente')


class NotificacionesDuplicadasTests(Etapa4Base):
    def test_recordatorios_del_mismo_dia_no_se_duplican(self):
        self.crear_kpi('KPI en borrador', estado='borrador')

        primero = generar_recordatorios_pendientes(fecha_referencia=timezone.localdate())
        segundo = generar_recordatorios_pendientes(fecha_referencia=timezone.localdate())

        self.assertEqual(primero['creadas'], 1)
        self.assertEqual(segundo['creadas'], 0)
        self.assertEqual(Notificacion.objects.filter(tipo='recordatorio_kpi_borrador').count(), 1)

    def test_recordatorios_solo_para_administrador_de_planificacion(self):
        self.crear_kpi('KPI en borrador', estado='borrador')

        generar_recordatorios_pendientes()

        destinatarios = set(Notificacion.objects.values_list('usuario_destino__username', flat=True))
        self.assertEqual(destinatarios, {self.admin.username})

    def test_reanular_un_kpi_no_duplica_la_notificacion(self):
        creador = crear_usuario('otro_admin_planif', 'Administrador de planificación')
        kpi = self.crear_kpi('KPI a anular')
        IndicadorKPI.objects.filter(pk=kpi.pk).update(creado_por=creador)
        self.client.force_authenticate(user=self.admin)

        self.client.post(f'/api/indicadores-kpi/{kpi.id}/anular/')
        self.client.post(f'/api/indicadores-kpi/{kpi.id}/anular/')

        self.assertEqual(Notificacion.objects.filter(tipo='kpi_anulado').count(), 1)


# ====================================================================== M7

class BitacoraSesionTests(Etapa4Base):
    def login(self, username, password=PASSWORD, **extra):
        return self.client.post('/api/auth/login/', {'username': username, 'password': password}, **extra)

    def test_inicio_de_sesion_exitoso_queda_registrado(self):
        response = self.login(self.ejecutor.username, REMOTE_ADDR='10.1.2.3')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        registro = self.ultima_bitacora(accion='inicio_sesion')
        self.assertEqual(registro.usuario, self.ejecutor)
        self.assertEqual(registro.ip_usuario, '10.1.2.3')
        self.assertNotIn(PASSWORD, registro.descripcion)
        self.assertNotIn(response.data['access'], registro.descripcion)

        self.ejecutor.refresh_from_db()
        self.assertIsNotNone(self.ejecutor.ultimo_acceso)
        self.assertIsNotNone(self.ejecutor.last_login)

    def test_intento_fallido_de_cuenta_existente_queda_registrado(self):
        response = self.login(self.ejecutor.username, 'incorrecta')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        registro = self.ultima_bitacora(accion='error', modulo='Inicio de sesión')
        self.assertEqual(registro.usuario, self.ejecutor)
        self.assertNotIn('incorrecta', registro.descripcion)
        self.assertFalse(Bitacora.objects.filter(accion='inicio_sesion').exists())

    def test_intento_con_cuenta_inexistente_no_revela_nada_ni_registra(self):
        response = self.login('no_existe', 'x')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertFalse(Bitacora.objects.filter(modulo='Inicio de sesión').exists())

    def test_cierre_de_sesion_explicito(self):
        self.client.force_authenticate(user=self.consulta)

        response = self.client.post('/api/auth/logout/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.ultima_bitacora(accion='cierre_sesion').usuario, self.consulta)

    def test_cierre_de_sesion_sin_autenticacion(self):
        self.assertEqual(self.client.post('/api/auth/logout/').status_code, status.HTTP_401_UNAUTHORIZED)

    def test_cierre_de_sesion_permitido_con_cambio_de_password_pendiente(self):
        from rest_framework_simplejwt.tokens import RefreshToken

        Usuario.objects.filter(pk=self.ejecutor.pk).update(debe_cambiar_password=True)
        self.ejecutor.refresh_from_db()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {RefreshToken.for_user(self.ejecutor).access_token}')

        self.assertEqual(self.client.post('/api/auth/logout/').status_code, status.HTTP_200_OK)

    def test_los_cuatro_roles_registran_inicio_de_sesion(self):
        for usuario in (self.admin, self.admin_sistema, self.ejecutor, self.consulta):
            self.assertEqual(self.login(usuario.username).status_code, status.HTTP_200_OK)

        self.assertEqual(Bitacora.objects.filter(accion='inicio_sesion').count(), 4)


class BitacoraOperacionesTests(Etapa4Base):
    def test_cambio_del_plazo_de_registro(self):
        self.client.force_authenticate(user=self.admin)

        self.client.patch('/api/configuracion-mediciones/', {'dias_plazo_registro': 8}, format='json')
        sin_cambio = self.client.patch('/api/configuracion-mediciones/', {'dias_plazo_registro': 8}, format='json')

        registros = Bitacora.objects.filter(modulo='Configuración de mediciones')
        self.assertEqual(sin_cambio.status_code, status.HTTP_200_OK)
        self.assertEqual(registros.count(), 1)
        self.assertIn('de 5 a 8 día(s)', registros.get().descripcion)

    def test_otros_roles_no_cambian_el_plazo(self):
        self.client.force_authenticate(user=self.ejecutor)

        response = self.client.patch('/api/configuracion-mediciones/', {'dias_plazo_registro': 2}, format='json')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Bitacora.objects.filter(modulo='Configuración de mediciones').exists())

    def test_creacion_y_cambios_de_areas(self):
        self.client.force_authenticate(user=self.admin)

        # JSON, como el frontend (en multipart un booleano ausente es False).
        area_id = self.client.post('/api/areas/', {'nombre': 'Créditos'}, format='json').data['id']
        self.client.patch(f'/api/areas/{area_id}/', {'nombre': 'Créditos y Cobros'}, format='json')
        self.client.patch(f'/api/areas/{area_id}/', {'estado': False}, format='json')
        self.client.patch(f'/api/areas/{area_id}/', {'estado': True}, format='json')

        descripciones = list(Bitacora.objects.filter(modulo='Áreas').order_by('id').values_list('accion', 'descripcion'))
        self.assertEqual(descripciones, [
            ('crear', 'Creó el área Créditos.'),
            ('actualizar', 'Actualizó el área Créditos (ahora Créditos y Cobros).'),
            ('eliminar', 'Inactivó el área Créditos y Cobros.'),
            ('actualizar', 'Reactivó el área Créditos y Cobros.'),
        ])

    def test_revision_de_alertas(self):
        kpi = self.crear_kpi()
        alerta = Alerta.objects.create(indicador=kpi, tipo_alerta='KPI En riesgo', mensaje='Revisar')
        Alerta.objects.create(indicador=kpi, tipo_alerta=TIPO_ALERTA_PERIODO_SIN_REGISTRO, mensaje='Otra')
        self.client.force_authenticate(user=self.admin)

        self.client.post(f'/api/alertas/{alerta.id}/marcar-revisada/')
        self.client.post(f'/api/alertas/{alerta.id}/marcar-revisada/')  # ya revisada: sin registro extra
        self.client.post('/api/alertas/marcar-todas-revisadas/')
        self.client.post('/api/alertas/marcar-todas-revisadas/')        # nada pendiente: sin registro

        descripciones = list(Bitacora.objects.filter(modulo='Alertas').order_by('id').values_list('descripcion', flat=True))
        self.assertEqual(len(descripciones), 2)
        self.assertIn(f'#{alerta.id}', descripciones[0])
        self.assertIn('1 alerta(s)', descripciones[1])

    def test_cambio_de_datos_del_propio_perfil(self):
        self.client.force_authenticate(user=self.ejecutor)

        self.client.patch('/api/usuarios/me/', {'correo': 'nuevo_correo@sniff.test'}, format='json')

        registro = self.ultima_bitacora(modulo='Perfil')
        self.assertEqual(registro.usuario, self.ejecutor)
        self.assertIn('correo', registro.descripcion)
        self.assertNotIn('nuevo_correo@sniff.test', registro.descripcion)


# ======================================================= Integridad (M7)

FALLA_BITACORA = mock.patch('apps.auditoria.services.registrar_bitacora', side_effect=RuntimeError('BD caída'))


class FalloDeBitacoraTests(Etapa4Base):
    """Si la bitácora no puede registrarse, la operación completa se revierte
    y el usuario recibe un 503 controlado (nunca un 500 ni una operación
    guardada sin su registro de auditoría)."""

    def assert503(self, response):
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertIn('no se guardó ningún cambio', str(response.data['detail']))

    def test_crear_area_se_revierte(self):
        self.client.force_authenticate(user=self.admin)

        with FALLA_BITACORA:
            response = self.client.post('/api/areas/', {'nombre': 'Área que no debe quedar'})

        self.assert503(response)
        self.assertFalse(Area.objects.filter(nombre='Área que no debe quedar').exists())

    def test_registrar_medicion_se_revierte_con_sus_alertas(self):
        kpi = self.crear_kpi()
        self.client.force_authenticate(user=self.ejecutor)

        with FALLA_BITACORA, mock.patch('apps.indicadores.services.hoy', return_value=date(2027, 1, 31)):
            response = self.client.post('/api/mediciones/', {'indicador': kpi.id, 'valor_resultado': '50'})

        self.assert503(response)
        self.assertFalse(Medicion.objects.filter(indicador=kpi).exists())
        self.assertFalse(Alerta.objects.filter(indicador=kpi).exists())

        # Reintentar después no duplica nada.
        with mock.patch('apps.indicadores.services.hoy', return_value=date(2027, 1, 31)):
            reintento = self.client.post('/api/mediciones/', {'indicador': kpi.id, 'valor_resultado': '50'})

        self.assertEqual(reintento.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Medicion.objects.filter(indicador=kpi).count(), 1)

    def test_autorizar_kpi_se_revierte(self):
        kpi = self.crear_kpi('KPI borrador', estado='borrador')
        self.client.force_authenticate(user=self.admin)

        with FALLA_BITACORA:
            response = self.client.post(f'/api/indicadores-kpi/{kpi.id}/autorizar/')

        self.assert503(response)
        kpi.refresh_from_db()
        self.assertEqual(kpi.estado, 'borrador')
        self.assertIsNone(kpi.fecha_autorizacion)

    def test_cambio_de_plazo_se_revierte(self):
        self.client.force_authenticate(user=self.admin)

        with FALLA_BITACORA:
            response = self.client.patch('/api/configuracion-mediciones/', {'dias_plazo_registro': 9}, format='json')

        self.assert503(response)
        self.assertEqual(ConfiguracionMediciones.obtener().dias_plazo_registro, 5)

    def test_inicio_de_sesion_no_entrega_tokens_sin_registro(self):
        with FALLA_BITACORA:
            response = self.client.post('/api/auth/login/', {'username': self.ejecutor.username, 'password': PASSWORD})

        self.assert503(response)
        self.assertNotIn('access', response.data)
        self.ejecutor.refresh_from_db()
        self.assertIsNone(self.ejecutor.ultimo_acceso)

    def test_inactivar_usuario_se_revierte(self):
        self.client.force_authenticate(user=self.admin_sistema)

        with FALLA_BITACORA:
            response = self.client.delete(f'/api/usuarios/{self.consulta.id}/')

        self.assert503(response)
        self.consulta.refresh_from_db()
        self.assertTrue(self.consulta.is_active)

    def test_medicion_duplicada_simultanea_responde_400(self):
        kpi = self.crear_kpi()
        self.client.force_authenticate(user=self.ejecutor)

        with mock.patch('rest_framework.serializers.ModelSerializer.create', side_effect=IntegrityError('duplicada')), \
                mock.patch('apps.indicadores.services.hoy', return_value=date(2027, 1, 31)):
            response = self.client.post('/api/mediciones/', {'indicador': kpi.id, 'valor_resultado': '50'})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Ya se registró una medición', str(response.data))


# ============================================================== IP (M7)

class IpBitacoraTests(Etapa4Base):
    def solicitud(self, **meta):
        return RequestFactory().get('/', **meta)

    def test_ip_directa(self):
        self.assertEqual(obtener_ip_usuario(self.solicitud(REMOTE_ADDR='192.168.1.20')), '192.168.1.20')

    def test_sin_proxies_ignora_x_forwarded_for(self):
        request = self.solicitud(REMOTE_ADDR='192.168.1.20', HTTP_X_FORWARDED_FOR='8.8.8.8')

        self.assertEqual(obtener_ip_usuario(request), '192.168.1.20')

    def test_detras_de_un_proxy_toma_la_ip_que_agrego_el_proxy(self):
        # El cliente puede mandar "1.1.1.1"; el proxy de confianza agrega la
        # IP real al final. Con NUM_PROXIES=1 se usa la última.
        request = self.solicitud(REMOTE_ADDR='10.0.0.1', HTTP_X_FORWARDED_FOR='1.1.1.1, 200.10.20.30')

        with override_settings(REST_FRAMEWORK={**settings.REST_FRAMEWORK, 'NUM_PROXIES': 1}):
            self.assertEqual(obtener_ip_usuario(request), '200.10.20.30')

    def test_valor_que_no_es_ip_se_guarda_vacio(self):
        request = self.solicitud(REMOTE_ADDR='no-es-ip')

        self.assertIsNone(obtener_ip_usuario(request))

    def test_la_bitacora_no_guarda_la_ip_falsificada(self):
        self.client.force_authenticate(user=self.consulta)

        self.client.post('/api/auth/logout/', REMOTE_ADDR='192.168.1.50', HTTP_X_FORWARDED_FOR='6.6.6.6')

        self.assertEqual(self.ultima_bitacora(accion='cierre_sesion').ip_usuario, '192.168.1.50')
