"""Etapa 5: solicitud y autorización de días adicionales para registrar
mediciones (SolicitudAmpliacionPlazo).

Calendario de las pruebas (KPI mensual 2027, plazo general de 5 días):
enero cierra el 31/01, su plazo ordinario termina el 05/02 y el plazo
máximo de una solicitud (ordinario + 10 días) es el 15/02."""

from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal
from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.auditoria.models import Bitacora, Notificacion
from apps.estrategia.models import ObjetivoEspecifico, ObjetivoGeneral, PlanAnual, PlanEstrategico
from apps.usuarios.models import Rol, Usuario

from . import services
from .models import (
    Alerta,
    ConfiguracionMediciones,
    EstadoCumplimiento,
    Frecuencia,
    IndicadorKPI,
    Medicion,
    ResponsableKPI,
    SolicitudAmpliacionPlazo,
)
from .services import (
    MODULO_AMPLIACIONES,
    TIPO_ALERTA_PERIODO_SIN_REGISTRO,
    TIPO_ALERTA_PERIODO_VENCIDO,
    cerrar_mediciones_vencidas,
    crear_rangos_provisionales,
    generar_alertas_periodos_vencidos,
    obtener_info_siguiente_periodo,
    obtener_o_crear_meta_vigente,
    obtener_o_crear_periodo,
)

URL = '/api/solicitudes-ampliacion/'

CIERRE_ENERO = date(2027, 1, 31)
LIMITE_ORDINARIO = date(2027, 2, 5)
LIMITE_MAXIMO = date(2027, 2, 15)


def crear_usuario(username, rol_nombre, **extra):
    rol, _ = Rol.objects.get_or_create(nombre=rol_nombre, defaults={'descripcion': 'Rol de prueba', 'estado': True})
    usuario = Usuario.objects.create_user(username=username, password='clave-prueba-123', **extra)
    usuario.rol = rol
    usuario.correo = f'{username}@sniff.test'
    usuario.save()
    return usuario


class AmpliacionesBase(APITestCase):
    def setUp(self):
        self.admin = crear_usuario('admin_ampl', 'Administrador de planificación')
        self.admin2 = crear_usuario('admin2_ampl', 'Administrador de planificación')
        self.admin_sistema = crear_usuario('sistema_ampl', 'Administrador del sistema')
        self.consulta = crear_usuario('consulta_ampl', 'Usuario de consulta')
        self.ana = crear_usuario('ana_ampl', 'Ejecutor operativo', first_name='Ana', last_name='López')
        self.beto = crear_usuario('beto_ampl', 'Ejecutor operativo')

        for nombre, color in [('Incumplido', 'rojo'), ('En riesgo', 'amarillo'), ('Favorable', 'verde')]:
            EstadoCumplimiento.objects.get_or_create(nombre=nombre, defaults={'color': color, 'estado': True})

        self.frecuencia = Frecuencia.objects.create(nombre='Mensual', estado=True)
        self.plan = PlanEstrategico.objects.create(
            titulo='Plan ampliaciones', fecha_inicio=date(2027, 1, 1), fecha_fin=date(2030, 12, 31),
            estado=PlanEstrategico.ESTADO_EN_USO, creado_por=self.admin,
        )
        objetivo_general = ObjetivoGeneral.objects.create(plan_estrategico=self.plan, texto_objetivo='OG', creado_por=self.admin)
        self.plan_anual = PlanAnual.objects.create(
            plan_estrategico=self.plan, anio=2027, estado=PlanAnual.ESTADO_EN_USO,
            fecha_inicio=date(2027, 1, 1), fecha_fin=date(2027, 12, 31), creado_por=self.admin,
        )
        self.objetivo_especifico = ObjetivoEspecifico.objects.create(
            plan_anual=self.plan_anual, objetivo_general=objetivo_general, texto_objetivo='OE', creado_por=self.admin,
        )
        self.kpi = self.crear_kpi('KPI cartera')
        self.kpi2 = self.crear_kpi('KPI cobros')

    def crear_kpi(self, nombre, estado='autorizado'):
        kpi = IndicadorKPI.objects.create(
            objetivo_especifico=self.objetivo_especifico, frecuencia=self.frecuencia, nombre=nombre,
            formula_medicion='Resultado', unidad_medida='%', valor_meta=Decimal('85'),
            estado=estado, creado_por=self.admin,
        )
        crear_rangos_provisionales(kpi)
        return kpi

    @contextmanager
    def en_fecha(self, fecha):
        with mock.patch('apps.indicadores.services.hoy', return_value=fecha):
            yield

    def como(self, usuario):
        self.client.force_authenticate(user=usuario)

    def solicitar(self, fecha, dias=10, motivo='Falta el reporte del área contable.', kpi=None, usuario=None):
        self.como(usuario or self.ana)
        with self.en_fecha(fecha):
            return self.client.post(
                URL, {'indicador': (kpi or self.kpi).id, 'dias_solicitados': dias, 'motivo': motivo}, format='json',
            )

    def crear_pendiente(self, fecha=CIERRE_ENERO, dias=10, kpi=None, usuario=None):
        response = self.solicitar(fecha, dias=dias, kpi=kpi, usuario=usuario)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        return SolicitudAmpliacionPlazo.objects.get(pk=response.data['id'])

    def accion(self, solicitud, nombre, fecha, usuario=None, **datos):
        self.como(usuario or self.admin)
        with self.en_fecha(fecha):
            return self.client.post(f'{URL}{solicitud.id}/{nombre}/', datos, format='json')

    def autorizada(self, dias=10, fecha_solicitud=CIERRE_ENERO, fecha_autorizacion=date(2027, 2, 1), kpi=None, **datos):
        solicitud = self.crear_pendiente(fecha_solicitud, dias=dias, kpi=kpi)
        response = self.accion(solicitud, 'autorizar', fecha_autorizacion, **datos)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        solicitud.refresh_from_db()
        return solicitud

    def registrar(self, fecha, kpi=None, valor='80', usuario=None):
        self.como(usuario or self.ana)
        with self.en_fecha(fecha):
            return self.client.post(
                '/api/mediciones/', {'indicador': (kpi or self.kpi).id, 'valor_resultado': valor}, format='json',
            )

    def info(self, fecha, kpi=None):
        return obtener_info_siguiente_periodo(kpi or self.kpi, fecha_referencia=fecha)

    def cerrar(self, fecha):
        with self.en_fecha(fecha):
            return cerrar_mediciones_vencidas()

    def bitacoras(self):
        return list(
            Bitacora.objects.filter(modulo=MODULO_AMPLIACIONES).order_by('id').values_list('usuario__username', 'descripcion')
        )

    def notificaciones(self, usuario, tipo=None):
        consulta = Notificacion.objects.filter(usuario_destino=usuario)

        if tipo:
            consulta = consulta.filter(tipo=tipo)

        return consulta

    def omisiones(self, kpi=None):
        return Medicion.objects.filter(indicador=kpi or self.kpi, cierre_automatico=True)


class SolicitudValidaTests(AmpliacionesBase):
    def test_solicitud_el_dia_del_cierre(self):
        response = self.solicitar(CIERRE_ENERO, dias=7)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        solicitud = SolicitudAmpliacionPlazo.objects.get()
        self.assertEqual(solicitud.estado, 'pendiente')
        self.assertEqual(solicitud.solicitante, self.ana)
        self.assertEqual(solicitud.periodo.fecha_inicio, date(2027, 1, 1))
        self.assertEqual(solicitud.fecha_limite_ordinaria, LIMITE_ORDINARIO)
        self.assertIsNone(solicitud.fecha_limite_extraordinaria)
        self.assertEqual(response.data['fecha_limite_solicitada'], '2027-02-12')
        self.assertEqual(response.data['fecha_limite_maxima'], '2027-02-15')
        self.assertEqual(response.data['solicitante_nombre'], 'Ana López')

    def test_solicitud_el_ultimo_dia_del_plazo_ordinario(self):
        self.assertEqual(self.solicitar(LIMITE_ORDINARIO).status_code, status.HTTP_201_CREATED)

    def test_uno_y_diez_dias_son_validos(self):
        self.assertEqual(self.solicitar(CIERRE_ENERO, dias=1).status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.solicitar(CIERRE_ENERO, dias=10, kpi=self.kpi2).status_code, status.HTTP_201_CREATED)

    def test_el_periodo_lo_fija_el_backend(self):
        response = self.solicitar(CIERRE_ENERO)
        self.como(self.ana)

        with self.en_fecha(CIERRE_ENERO):
            otro = self.client.post(URL, {
                'indicador': self.kpi2.id, 'dias_solicitados': 3, 'motivo': 'x',
                'periodo': response.data['periodo'] + 50, 'fecha_limite_ordinaria': '2027-12-31', 'estado': 'autorizada',
            }, format='json')

        solicitud = SolicitudAmpliacionPlazo.objects.get(pk=otro.data['id'])
        self.assertEqual(solicitud.estado, 'pendiente')
        self.assertEqual(solicitud.fecha_limite_ordinaria, LIMITE_ORDINARIO)
        self.assertEqual(solicitud.periodo.fecha_inicio, date(2027, 1, 1))

    def test_registra_bitacora_y_avisa_solo_a_administradores_de_planificacion(self):
        solicitud = self.crear_pendiente()

        self.assertEqual(self.bitacoras(), [(
            'ana_ampl',
            'Solicitó 10 día(s) adicional(es) para el KPI KPI cartera (periodo Enero 2027, plazo ordinario '
            'hasta el 05/02/2027). Motivo: Falta el reporte del área contable.',
        )])
        enlace = f'/mediciones?tab=solicitudes&solicitud={solicitud.id}'
        for admin in (self.admin, self.admin2):
            self.assertEqual(self.notificaciones(admin, 'ampliacion_solicitada').get().enlace, enlace)
        for otro in (self.admin_sistema, self.consulta, self.ana, self.beto):
            self.assertFalse(self.notificaciones(otro).exists())


class SolicitudInvalidaTests(AmpliacionesBase):
    def assertRechazada(self, response, texto):
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertIn(texto, str(response.data))
        self.assertFalse(SolicitudAmpliacionPlazo.objects.exists())

    def test_antes_del_cierre_del_periodo(self):
        self.assertRechazada(self.solicitar(date(2027, 1, 30)), 'solo pueden pedirse desde su cierre')

    def test_despues_del_plazo_ordinario(self):
        self.assertRechazada(self.solicitar(date(2027, 2, 6)), 'ya no pueden pedirse días adicionales')

    def test_dias_fuera_de_rango(self):
        self.assertRechazada(self.solicitar(CIERRE_ENERO, dias=0), 'al menos 1 día')
        self.assertRechazada(self.solicitar(CIERRE_ENERO, dias=-2), 'al menos 1 día')
        self.assertRechazada(self.solicitar(CIERRE_ENERO, dias=11), 'más de 10 días')
        self.assertRechazada(self.solicitar(CIERRE_ENERO, dias='diez'), 'número entero')

    def test_motivo_obligatorio(self):
        self.assertRechazada(self.solicitar(CIERRE_ENERO, motivo=''), 'motivo')
        self.assertRechazada(self.solicitar(CIERRE_ENERO, motivo='   '), 'motivo')

    def test_kpi_borrador_o_anulado(self):
        borrador = self.crear_kpi('KPI borrador', estado='borrador')
        anulado = self.crear_kpi('KPI anulado', estado='anulado')

        self.assertRechazada(self.solicitar(CIERRE_ENERO, kpi=borrador), 'KPI autorizados')
        self.assertRechazada(self.solicitar(CIERRE_ENERO, kpi=anulado), 'KPI autorizados')

    def test_plan_anual_o_estrategico_cerrado(self):
        PlanAnual.objects.filter(pk=self.plan_anual.pk).update(estado=PlanAnual.ESTADO_CERRADO)
        self.assertRechazada(self.solicitar(CIERRE_ENERO), 'Cerrados')

        PlanAnual.objects.filter(pk=self.plan_anual.pk).update(estado=PlanAnual.ESTADO_EN_USO)
        PlanEstrategico.objects.filter(pk=self.plan.pk).update(estado=PlanEstrategico.ESTADO_CERRADO)
        self.assertRechazada(self.solicitar(CIERRE_ENERO), 'Cerrados')

    def test_periodo_con_medicion_real_no_se_puede_ampliar(self):
        self.assertEqual(self.registrar(CIERRE_ENERO).status_code, status.HTTP_201_CREATED)

        # El siguiente periodo pasa a ser febrero, que todavía no cerró.
        self.assertRechazada(self.solicitar(date(2027, 2, 2)), 'febrero 2027 solo pueden pedirse desde su cierre')

    def test_periodo_cerrado_automaticamente_no_se_reabre(self):
        self.cerrar(date(2027, 2, 6))
        self.assertEqual(self.omisiones().count(), 1)

        # Enero ya tiene su omisión: la solicitud apunta a febrero.
        self.assertRechazada(self.solicitar(date(2027, 2, 6)), 'febrero 2027')
        self.assertEqual(self.omisiones().count(), 1)


class DuplicadosYConcurrenciaTests(AmpliacionesBase):
    def test_una_sola_pendiente_por_kpi_y_periodo(self):
        self.crear_pendiente()

        response = self.solicitar(date(2027, 2, 1), usuario=self.beto)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Ya existe una solicitud pendiente', str(response.data))
        self.assertEqual(SolicitudAmpliacionPlazo.objects.count(), 1)

    def test_otro_kpi_no_se_ve_afectado(self):
        self.crear_pendiente()
        self.assertEqual(self.solicitar(CIERRE_ENERO, kpi=self.kpi2).status_code, status.HTTP_201_CREATED)

    def test_carrera_entre_dos_solicitudes_responde_400(self):
        """Si dos peticiones pasan la validación a la vez, la restricción
        única parcial impide la segunda y se responde 400, no 500."""
        self.crear_pendiente()
        evaluar_real = services.evaluar_solicitud_ampliacion

        def evaluar_sin_ver_la_pendiente(indicador, fecha_referencia=None):
            info, _ = evaluar_real(indicador, fecha_referencia)
            return info, ''

        with mock.patch('apps.indicadores.services.evaluar_solicitud_ampliacion', side_effect=evaluar_sin_ver_la_pendiente):
            response = self.solicitar(date(2027, 2, 1), usuario=self.beto)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(SolicitudAmpliacionPlazo.objects.count(), 1)
        self.assertEqual(len(self.bitacoras()), 1)

    def test_restricciones_de_base_de_datos(self):
        solicitud = self.crear_pendiente()
        datos = {
            'indicador': self.kpi, 'periodo': solicitud.periodo, 'solicitante': self.beto, 'motivo': 'x',
            'dias_solicitados': 5, 'fecha_limite_ordinaria': LIMITE_ORDINARIO,
        }

        with self.assertRaises(IntegrityError), transaction.atomic():
            SolicitudAmpliacionPlazo.objects.create(**datos)

        with self.assertRaises(IntegrityError), transaction.atomic():
            SolicitudAmpliacionPlazo.objects.create(**{**datos, 'estado': 'rechazada', 'dias_solicitados': 11})

        with self.assertRaises(IntegrityError), transaction.atomic():
            SolicitudAmpliacionPlazo.objects.create(**{**datos, 'estado': 'rechazada', 'dias_autorizados': 6})

        # Autorizada sin fecha extraordinaria ni quien la revisó.
        with self.assertRaises(IntegrityError), transaction.atomic():
            SolicitudAmpliacionPlazo.objects.create(**{**datos, 'estado': 'autorizada', 'dias_autorizados': 5})

        autorizada = {
            **datos, 'estado': 'autorizada', 'dias_autorizados': 5, 'revisado_por': self.admin,
            'fecha_limite_extraordinaria': date(2027, 2, 10),
        }
        SolicitudAmpliacionPlazo.objects.create(**autorizada)

        # Dos autorizaciones contradictorias para el mismo periodo.
        with self.assertRaises(IntegrityError), transaction.atomic():
            SolicitudAmpliacionPlazo.objects.create(**{**autorizada, 'fecha_limite_extraordinaria': date(2027, 2, 15)})

        # Las rechazadas pueden ser varias (historial).
        SolicitudAmpliacionPlazo.objects.create(**{**datos, 'estado': 'rechazada'})
        SolicitudAmpliacionPlazo.objects.create(**{**datos, 'estado': 'rechazada'})


class AutorizacionTests(AmpliacionesBase):
    def test_autorizacion_completa(self):
        solicitud = self.autorizada(dias=10)

        self.assertEqual(solicitud.estado, 'autorizada')
        self.assertEqual(solicitud.dias_autorizados, 10)
        self.assertEqual(solicitud.fecha_limite_extraordinaria, LIMITE_MAXIMO)
        self.assertEqual(solicitud.revisado_por, self.admin)
        self.assertIsNotNone(solicitud.fecha_resolucion)
        self.assertEqual(self.bitacoras()[-1], (
            'admin_ampl',
            'Autorizó 10 de 10 día(s) solicitado(s) en la solicitud de ampliación #'
            f'{solicitud.id} del KPI KPI cartera (periodo Enero 2027), pedida por ana_ampl. '
            'Nuevo plazo de registro: 15/02/2027.',
        ))
        aviso = self.notificaciones(self.ana, 'ampliacion_autorizada').get()
        self.assertIn('hasta el 15/02/2027', aviso.mensaje)

    def test_autorizacion_parcial(self):
        solicitud = self.autorizada(dias=7, dias_autorizados=3, observacion='Alcanza con tres días.')

        self.assertEqual(solicitud.dias_solicitados, 7)
        self.assertEqual(solicitud.dias_autorizados, 3)
        self.assertEqual(solicitud.fecha_limite_extraordinaria, date(2027, 2, 8))
        self.assertEqual(solicitud.observacion_revision, 'Alcanza con tres días.')

    def test_no_autoriza_mas_de_lo_pedido_ni_cero(self):
        solicitud = self.crear_pendiente(dias=4)

        for dias, texto in ((5, 'más días de los solicitados'), (11, 'más días de los solicitados'),
                            (0, 'al menos 1 día'), ('dos', 'número entero')):
            response = self.accion(solicitud, 'autorizar', date(2027, 2, 1), dias_autorizados=dias)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn(texto, response.data['detail'])

        solicitud.refresh_from_db()
        self.assertEqual(solicitud.estado, 'pendiente')

    def test_autorizacion_despues_del_plazo_ordinario_exige_un_plazo_vigente(self):
        solicitud = self.crear_pendiente(dias=10)

        response = self.accion(solicitud, 'autorizar', date(2027, 2, 10), dias_autorizados=3)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('08/02/2027, que ya pasó. Autorizá al menos 5 día(s)', response.data['detail'])

        response = self.accion(solicitud, 'autorizar', date(2027, 2, 10), dias_autorizados=5)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        solicitud.refresh_from_db()
        self.assertEqual(solicitud.fecha_limite_extraordinaria, date(2027, 2, 10))

        # El mismo día del nuevo límite todavía se puede registrar.
        self.assertEqual(self.registrar(date(2027, 2, 10)).status_code, status.HTTP_201_CREATED)

    def test_el_ultimo_dia_del_plazo_maximo_todavia_se_autoriza(self):
        solicitud = self.crear_pendiente()

        response = self.accion(solicitud, 'autorizar', LIMITE_MAXIMO)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['fecha_limite_extraordinaria'], '2027-02-15')

    def test_no_se_resuelve_despues_del_plazo_maximo(self):
        solicitud = self.crear_pendiente()

        for nombre, datos in (('autorizar', {}), ('rechazar', {'observacion': 'tarde'})):
            response = self.accion(solicitud, nombre, date(2027, 2, 16), **datos)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn('Venció el plazo máximo', response.data['detail'])

        retiro = self.accion(solicitud, 'retirar', date(2027, 2, 16), usuario=self.ana)
        self.assertEqual(retiro.status_code, status.HTTP_400_BAD_REQUEST)

        solicitud.refresh_from_db()
        self.assertEqual(solicitud.estado, 'pendiente')

        self.como(self.admin)
        with self.en_fecha(date(2027, 2, 16)):
            self.assertTrue(self.client.get(f'{URL}{solicitud.id}/').data['plazo_resolucion_vencido'])

    def test_estados_definitivos(self):
        solicitud = self.autorizada()

        for nombre, datos in (('autorizar', {}), ('rechazar', {'observacion': 'x'})):
            response = self.accion(solicitud, nombre, date(2027, 2, 2), **datos)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn('ya no está pendiente', response.data['detail'])

        self.assertEqual(self.notificaciones(self.ana, 'ampliacion_autorizada').count(), 1)

    def test_no_autoriza_un_periodo_que_ya_tiene_medicion(self):
        solicitud = self.crear_pendiente()
        Medicion.objects.create(
            indicador=self.kpi, meta=obtener_o_crear_meta_vigente(self.kpi), periodo=solicitud.periodo,
            estado_cumplimiento=EstadoCumplimiento.objects.get(nombre='Favorable'),
            fecha_medicion=CIERRE_ENERO, valor_resultado=Decimal('90'), registrado_por=self.ana,
        )

        response = self.accion(solicitud, 'autorizar', date(2027, 2, 1))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('ya tiene una medición', response.data['detail'])

    def test_no_autoriza_kpi_anulado_ni_de_plan_cerrado(self):
        solicitud = self.crear_pendiente()

        PlanAnual.objects.filter(pk=self.plan_anual.pk).update(estado=PlanAnual.ESTADO_CERRADO)
        response = self.accion(solicitud, 'autorizar', date(2027, 2, 1))
        self.assertIn('ya no puede resolverse', response.data['detail'])

        PlanAnual.objects.filter(pk=self.plan_anual.pk).update(estado=PlanAnual.ESTADO_EN_USO)
        IndicadorKPI.objects.filter(pk=self.kpi.pk).update(estado='anulado')
        response = self.accion(solicitud, 'autorizar', date(2027, 2, 1))
        self.assertIn('solo puede rechazarse', response.data['detail'])

    def test_con_una_autorizacion_no_se_puede_volver_a_pedir(self):
        self.autorizada(dias=3)

        response = self.solicitar(date(2027, 2, 2), usuario=self.beto)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('ya tiene una ampliación autorizada hasta el 08/02/2027', str(response.data))


class RechazoYRetiroTests(AmpliacionesBase):
    def test_rechazo_exige_observacion(self):
        solicitud = self.crear_pendiente()

        for observacion in ('', '   '):
            response = self.accion(solicitud, 'rechazar', date(2027, 2, 1), observacion=observacion)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn('motivo del rechazo', str(response.data))

    def test_rechazo_queda_como_historial_y_se_avisa(self):
        solicitud = self.crear_pendiente()

        response = self.accion(solicitud, 'rechazar', date(2027, 2, 1), observacion='No hay justificación suficiente.')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        solicitud.refresh_from_db()
        self.assertEqual(solicitud.estado, 'rechazada')
        self.assertEqual(solicitud.revisado_por, self.admin)
        self.assertIsNone(solicitud.dias_autorizados)
        self.assertIn('No hay justificación suficiente.', self.notificaciones(self.ana, 'ampliacion_rechazada').get().mensaje)
        self.assertTrue(self.bitacoras()[-1][1].startswith('Rechazó la solicitud de ampliación'))
        # El plazo no cambia.
        self.assertEqual(self.info(date(2027, 2, 1))['fecha_limite_registro'], LIMITE_ORDINARIO)

    def test_despues_de_un_rechazo_se_puede_pedir_otra_dentro_del_plazo_ordinario(self):
        primera = self.crear_pendiente()
        self.accion(primera, 'rechazar', date(2027, 2, 1), observacion='Falta detalle.')

        self.assertEqual(self.solicitar(LIMITE_ORDINARIO).status_code, status.HTTP_201_CREATED)
        self.assertEqual(SolicitudAmpliacionPlazo.objects.filter(estado='rechazada').count(), 1)

    def test_despues_de_un_rechazo_fuera_del_plazo_ordinario_no(self):
        primera = self.crear_pendiente()
        self.accion(primera, 'rechazar', date(2027, 2, 6), observacion='Falta detalle.')

        self.assertEqual(self.solicitar(date(2027, 2, 6)).status_code, status.HTTP_400_BAD_REQUEST)

    def test_el_ejecutor_retira_su_solicitud(self):
        solicitud = self.crear_pendiente()

        response = self.accion(solicitud, 'retirar', date(2027, 2, 1), usuario=self.ana)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        solicitud.refresh_from_db()
        self.assertEqual(solicitud.estado, 'retirada')
        self.assertIsNotNone(solicitud.fecha_resolucion)
        self.assertEqual(self.bitacoras()[-1][0], 'ana_ampl')
        self.assertTrue(self.bitacoras()[-1][1].startswith('Retiró la solicitud de ampliación'))
        self.assertTrue(self.notificaciones(self.admin, 'ampliacion_retirada').exists())
        # Puede volver a pedir dentro del plazo ordinario.
        self.assertEqual(self.solicitar(date(2027, 2, 2)).status_code, status.HTTP_201_CREATED)

    def test_solo_el_solicitante_retira_y_solo_si_esta_pendiente(self):
        solicitud = self.crear_pendiente()

        self.assertEqual(self.accion(solicitud, 'retirar', date(2027, 2, 1), usuario=self.beto).status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.accion(solicitud, 'retirar', date(2027, 2, 1), usuario=self.admin).status_code, status.HTTP_403_FORBIDDEN)

        self.accion(solicitud, 'rechazar', date(2027, 2, 1), observacion='No.')
        response = self.accion(solicitud, 'retirar', date(2027, 2, 1), usuario=self.ana)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        solicitud.refresh_from_db()
        self.assertEqual(solicitud.estado, 'rechazada')


class RegistroConAmpliacionTests(AmpliacionesBase):
    def test_pendiente_con_plazo_ordinario_vencido_no_permite_registrar(self):
        self.crear_pendiente()

        info = self.info(date(2027, 2, 6))
        self.assertFalse(info['disponible'])
        self.assertIn('pendiente de resolución', info['motivo'])

        response = self.registrar(date(2027, 2, 6))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('pendiente de resolución', str(response.data))

    def test_registro_el_ultimo_dia_ampliado(self):
        self.autorizada(dias=10)

        self.assertTrue(self.info(LIMITE_MAXIMO)['disponible'])
        self.assertEqual(self.registrar(LIMITE_MAXIMO).status_code, status.HTTP_201_CREATED)

    def test_no_registra_al_dia_siguiente_del_plazo_ampliado(self):
        self.autorizada(dias=10)

        response = self.registrar(date(2027, 2, 16))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('venció su ventana de registro', str(response.data))

    def test_la_ampliacion_no_afecta_otros_periodos_ni_otros_kpi(self):
        self.autorizada(dias=10)
        self.assertEqual(self.registrar(date(2027, 2, 12)).status_code, status.HTTP_201_CREATED)

        febrero = self.info(date(2027, 3, 1))
        self.assertEqual(febrero['periodo_nombre'], 'febrero 2027')
        self.assertEqual(febrero['fecha_limite_registro'], date(2027, 3, 5))
        self.assertIsNone(febrero['ampliacion_autorizada'])

        otro = self.info(date(2027, 2, 12), kpi=self.kpi2)
        self.assertEqual(otro['fecha_limite_registro'], LIMITE_ORDINARIO)
        self.assertFalse(otro['disponible'])

    def test_registrar_dentro_del_plazo_ordinario_deja_sin_efecto_la_pendiente(self):
        solicitud = self.crear_pendiente()

        self.assertEqual(self.registrar(date(2027, 2, 3)).status_code, status.HTTP_201_CREATED)

        solicitud.refresh_from_db()
        self.assertEqual(solicitud.estado, 'sin_efecto')
        self.assertEqual(solicitud.observacion_revision, 'se registró la medición del periodo.')
        self.assertIn('quedó sin efecto', self.bitacoras()[-1][1])
        self.assertEqual(self.bitacoras()[-1][0], 'ana_ampl')
        # Quien registró es la solicitante: no se avisa a sí misma.
        self.assertFalse(self.notificaciones(self.ana, 'ampliacion_sin_efecto').exists())

    def test_registro_de_otro_ejecutor_avisa_a_la_solicitante(self):
        self.crear_pendiente()

        self.registrar(date(2027, 2, 3), usuario=self.beto)

        self.assertTrue(self.notificaciones(self.ana, 'ampliacion_sin_efecto').exists())

    def test_siguiente_periodo_informa_las_fechas(self):
        self.como(self.ana)

        with self.en_fecha(CIERRE_ENERO):
            datos = self.client.get('/api/mediciones/siguiente-periodo/', {'indicador': self.kpi.id}).data
        self.assertTrue(datos['puede_solicitar_ampliacion'])
        self.assertEqual(datos['fecha_limite_ordinaria'], LIMITE_ORDINARIO)
        self.assertIsNone(datos['fecha_limite_extraordinaria'])

        solicitud = self.autorizada(dias=4)
        self.como(self.ana)

        with self.en_fecha(date(2027, 2, 7)):
            datos = self.client.get('/api/mediciones/siguiente-periodo/', {'indicador': self.kpi.id}).data
        self.assertTrue(datos['disponible'])
        self.assertEqual(datos['fecha_limite_registro'], date(2027, 2, 9))
        self.assertEqual(datos['fecha_limite_extraordinaria'], date(2027, 2, 9))
        self.assertEqual(datos['ampliacion_autorizada']['id'], solicitud.id)
        self.assertFalse(datos['puede_solicitar_ampliacion'])

    def test_registrada_con_ampliacion_para_el_dashboard(self):
        self.autorizada(dias=10)
        respuesta = self.registrar(date(2027, 2, 10))
        medicion_id = respuesta.data['id']
        # fecha_registro es la hora real del servidor: se fija la del escenario.
        Medicion.objects.filter(pk=medicion_id).update(fecha_registro=timezone.make_aware(datetime(2027, 2, 10, 9, 0)))

        self.cerrar(date(2027, 3, 6))  # Omisiones del otro KPI y de febrero.

        self.como(self.consulta)
        listado = {m['id']: m for m in self.client.get('/api/mediciones/').data}

        self.assertTrue(listado[medicion_id]['registrada_con_ampliacion'])
        self.assertEqual(
            [m['registrada_con_ampliacion'] for i, m in listado.items() if i != medicion_id],
            [False] * (len(listado) - 1),
        )

    def test_registrada_dentro_del_plazo_ordinario_no_cuenta_como_ampliacion(self):
        self.autorizada(dias=10)
        respuesta = self.registrar(date(2027, 2, 3))
        Medicion.objects.filter(pk=respuesta.data['id']).update(fecha_registro=timezone.make_aware(datetime(2027, 2, 3, 9, 0)))

        self.como(self.consulta)
        self.assertFalse(self.client.get(f"/api/mediciones/{respuesta.data['id']}/").data['registrada_con_ampliacion'])


class CierreAutomaticoTests(AmpliacionesBase):
    def test_sin_solicitud_el_cierre_sigue_igual(self):
        self.assertEqual(self.cerrar(LIMITE_ORDINARIO)['cierres_creados'], 0)
        self.assertEqual(self.cerrar(date(2027, 2, 6))['cierres_creados'], 2)  # Los dos KPI.

    def test_una_pendiente_detiene_el_cierre_hasta_su_plazo_maximo_inclusive(self):
        solicitud = self.crear_pendiente()

        for fecha in (date(2027, 2, 6), date(2027, 2, 10), LIMITE_MAXIMO):
            resultado = self.cerrar(fecha)
            self.assertEqual(resultado['kpi_en_espera'], 1)
            self.assertFalse(self.omisiones().exists())

        # El otro KPI, sin solicitud, se cerró el 06/02.
        self.assertEqual(self.omisiones(self.kpi2).count(), 1)

        resultado = self.cerrar(date(2027, 2, 16))

        solicitud.refresh_from_db()
        self.assertEqual(solicitud.estado, 'vencida')
        self.assertEqual(resultado['solicitudes_vencidas'], 1)
        self.assertEqual(self.omisiones().count(), 1)
        self.assertEqual(self.omisiones().get().periodo, solicitud.periodo)

        registro = Bitacora.objects.filter(modulo=MODULO_AMPLIACIONES, usuario__isnull=True).get()
        self.assertIn('quedó vencida', registro.descripcion)
        self.assertIn('15/02/2027', registro.descripcion)
        self.assertTrue(self.notificaciones(self.ana, 'ampliacion_vencida').exists())

    def test_cierre_respeta_la_fecha_extraordinaria(self):
        self.autorizada(dias=7)  # Hasta el 12/02.

        self.assertEqual(self.cerrar(date(2027, 2, 12))['detalle'][0]['indicador_id'], self.kpi2.id)
        self.assertFalse(self.omisiones().exists())

        self.cerrar(date(2027, 2, 13))

        omision = self.omisiones().get()
        alerta = Alerta.objects.get(medicion=omision, tipo_alerta=TIPO_ALERTA_PERIODO_SIN_REGISTRO)
        self.assertIn('plazo vencido el 12/02/2027, incluida la ampliación autorizada', alerta.mensaje)

    def test_el_cierre_es_idempotente(self):
        solicitud = self.crear_pendiente()
        self.cerrar(date(2027, 2, 16))
        self.cerrar(date(2027, 2, 16))
        segunda = self.cerrar(date(2027, 2, 17))

        self.assertEqual(self.omisiones().count(), 1)
        self.assertEqual(segunda['solicitudes_vencidas'], 0)
        self.assertEqual(Bitacora.objects.filter(modulo=MODULO_AMPLIACIONES, usuario__isnull=True).count(), 1)
        self.assertEqual(self.notificaciones(self.ana, 'ampliacion_vencida').count(), 1)
        solicitud.refresh_from_db()
        self.assertEqual(solicitud.estado, 'vencida')

    def test_simulacion_no_cambia_solicitudes(self):
        solicitud = self.crear_pendiente()

        with self.en_fecha(date(2027, 2, 16)):
            call_command('ejecutar_tareas_mediciones', '--simular', stdout=StringIO())

        solicitud.refresh_from_db()
        self.assertEqual(solicitud.estado, 'pendiente')
        self.assertFalse(self.omisiones().exists())
        self.assertFalse(Bitacora.objects.filter(usuario__isnull=True).exists())

    def test_la_tarea_diaria_informa_las_solicitudes(self):
        self.crear_pendiente()
        salida = StringIO()

        with self.en_fecha(date(2027, 2, 10)):
            call_command('ejecutar_tareas_mediciones', stdout=salida)

        self.assertIn('KPI en espera por ampliación pendiente: 1', salida.getvalue())

    def test_si_falla_el_vencimiento_el_cierre_no_queda_retenido(self):
        solicitud = self.crear_pendiente()

        with mock.patch('apps.auditoria.services.registrar_bitacora_sistema', side_effect=RuntimeError('BD caída')):
            resultado = self.cerrar(date(2027, 2, 16))

        solicitud.refresh_from_db()
        self.assertEqual(solicitud.estado, 'pendiente')
        self.assertEqual(len(resultado['errores']), 1)
        self.assertIn(f'Solicitud de ampliación #{solicitud.id}', resultado['errores'][0]['error'])
        # Pasado el plazo máximo, la pendiente ya no detiene el cierre.
        self.assertEqual(self.omisiones().count(), 1)

        # La siguiente ejecución la marca Vencida (no Sin efecto).
        self.cerrar(date(2027, 2, 17))
        solicitud.refresh_from_db()
        self.assertEqual(solicitud.estado, 'vencida')

    def test_pendiente_de_plan_cerrado_o_kpi_anulado_queda_sin_efecto(self):
        primera = self.crear_pendiente()
        segunda = self.crear_pendiente(kpi=self.kpi2)
        IndicadorKPI.objects.filter(pk=self.kpi2.pk).update(estado='anulado')
        PlanAnual.objects.filter(pk=self.plan_anual.pk).update(estado=PlanAnual.ESTADO_CERRADO)

        resultado = self.cerrar(date(2027, 2, 2))

        primera.refresh_from_db()
        segunda.refresh_from_db()
        self.assertEqual((primera.estado, segunda.estado), ('sin_efecto', 'sin_efecto'))
        self.assertEqual(resultado['solicitudes_sin_efecto'], 2)
        self.assertIn('Cerrado', primera.observacion_revision)
        self.assertEqual(segunda.observacion_revision, 'el KPI fue anulado.')
        self.assertFalse(Medicion.objects.exists())


class CambioPlazoGeneralTests(AmpliacionesBase):
    def cambiar_plazo(self, dias):
        configuracion = ConfiguracionMediciones.obtener()
        configuracion.dias_plazo_registro = dias
        configuracion.save()

    def test_reducir_el_plazo_general_no_acorta_una_ampliacion(self):
        self.autorizada(dias=10)
        self.cambiar_plazo(2)

        self.assertEqual(self.info(date(2027, 2, 10))['fecha_limite_registro'], LIMITE_MAXIMO)
        self.assertEqual(self.info(date(2027, 2, 10))['fecha_limite_ordinaria'], date(2027, 2, 2))
        self.assertEqual(self.registrar(LIMITE_MAXIMO).status_code, status.HTTP_201_CREATED)

    def test_ampliar_el_plazo_general_por_encima_de_la_ampliacion_prevalece(self):
        self.autorizada(dias=3)  # Hasta el 08/02.
        self.cambiar_plazo(20)

        self.assertEqual(self.info(date(2027, 2, 10))['fecha_limite_registro'], date(2027, 2, 20))

    def test_la_pendiente_conserva_su_referencia_ordinaria(self):
        solicitud = self.crear_pendiente()
        self.cambiar_plazo(2)

        self.assertEqual(self.cerrar(date(2027, 2, 10))['kpi_en_espera'], 1)
        response = self.accion(solicitud, 'autorizar', date(2027, 2, 14))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        solicitud.refresh_from_db()
        self.assertEqual(solicitud.fecha_limite_ordinaria, LIMITE_ORDINARIO)
        self.assertEqual(solicitud.fecha_limite_extraordinaria, LIMITE_MAXIMO)


class AlertasYNotificacionesTests(AmpliacionesBase):
    def setUp(self):
        super().setUp()
        ResponsableKPI.objects.create(indicador=self.kpi, usuario=self.ana)
        ResponsableKPI.objects.create(indicador=self.kpi, usuario=self.beto)

    def alertas_periodo(self):
        return Alerta.objects.filter(indicador=self.kpi, tipo_alerta=TIPO_ALERTA_PERIODO_VENCIDO).order_by('id')

    def test_alerta_con_pendiente_y_plazo_ordinario_vencido(self):
        self.crear_pendiente()

        with self.en_fecha(date(2027, 2, 6)):
            generar_alertas_periodos_vencidos()

        alerta = self.alertas_periodo().get()
        self.assertIn('solicitud de días adicionales pendiente', alerta.mensaje)
        self.assertIn('terminó el 05/02/2027', alerta.mensaje)

    def test_alerta_generada_con_ampliacion_autorizada(self):
        self.autorizada(dias=10)

        with self.en_fecha(date(2027, 2, 6)):
            generar_alertas_periodos_vencidos()

        self.assertIn('ampliación autorizada: puede registrarse hasta el 15/02/2027', self.alertas_periodo().get().mensaje)

    def test_autorizar_reemplaza_la_alerta_vigente_sin_reescribir_la_anterior(self):
        with self.en_fecha(date(2027, 2, 1)):
            generar_alertas_periodos_vencidos()
        anterior = self.alertas_periodo().get()
        mensaje_anterior = anterior.mensaje

        self.autorizada(dias=10, fecha_solicitud=date(2027, 2, 1), fecha_autorizacion=date(2027, 2, 6))

        anterior.refresh_from_db()
        self.assertEqual(anterior.estado_alerta, 'descartada')
        self.assertEqual(anterior.mensaje, mensaje_anterior)
        self.assertIn('hasta el 05/02/2027', anterior.mensaje)

        vigente = self.alertas_periodo().get(estado_alerta='pendiente')
        self.assertIn('hasta el 15/02/2027', vigente.mensaje)

        # Los avisos individuales a responsables se retiraron del flujo: nadie
        # recibe un aviso por la alerta nueva; la solicitante conserva el suyo.
        enlace = f'/mediciones?indicador={self.kpi.id}&alerta={vigente.id}'
        self.assertFalse(Notificacion.objects.filter(enlace=enlace).exists())
        self.assertEqual(self.notificaciones(self.ana, 'ampliacion_autorizada').count(), 1)

        # La tarea diaria no duplica la alerta del periodo.
        with self.en_fecha(date(2027, 2, 7)):
            generar_alertas_periodos_vencidos()
        self.assertEqual(self.alertas_periodo().count(), 2)

        # Al registrar, la alerta vigente se resuelve.
        self.registrar(date(2027, 2, 8))
        self.assertFalse(self.alertas_periodo().filter(estado_alerta='pendiente').exists())

    def test_sin_alerta_previa_no_se_crea_una_al_autorizar(self):
        self.autorizada()
        self.assertFalse(self.alertas_periodo().exists())

    def test_anular_el_kpi_deja_sin_efecto_la_pendiente(self):
        solicitud = self.crear_pendiente()
        self.como(self.admin)

        response = self.client.post(f'/api/indicadores-kpi/{self.kpi.id}/anular/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        solicitud.refresh_from_db()
        self.assertEqual(solicitud.estado, 'sin_efecto')
        self.assertEqual(self.bitacoras()[-1][0], 'admin_ampl')
        self.assertTrue(self.notificaciones(self.ana, 'ampliacion_sin_efecto').exists())

    def test_bitacora_completa_del_ciclo(self):
        primera = self.crear_pendiente()
        self.accion(primera, 'retirar', date(2027, 2, 1), usuario=self.ana)
        segunda = self.crear_pendiente(date(2027, 2, 1))
        self.accion(segunda, 'rechazar', date(2027, 2, 2), observacion='No.')
        tercera = self.crear_pendiente(date(2027, 2, 3))
        self.accion(tercera, 'autorizar', date(2027, 2, 4), dias_autorizados=2)

        acciones = [descripcion.split(' ')[0] for _, descripcion in self.bitacoras()]
        self.assertEqual(acciones, ['Solicitó', 'Retiró', 'Solicitó', 'Rechazó', 'Solicitó', 'Autorizó'])
        self.assertEqual(SolicitudAmpliacionPlazo.objects.count(), 3)

    def test_falla_de_bitacora_revierte_la_solicitud(self):
        with mock.patch('apps.auditoria.services.registrar_bitacora', side_effect=RuntimeError('BD caída')):
            response = self.solicitar(CIERRE_ENERO)

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertFalse(SolicitudAmpliacionPlazo.objects.exists())


class PermisosTests(AmpliacionesBase):
    def test_roles_sin_acceso(self):
        solicitud = self.crear_pendiente()

        for usuario in (self.admin_sistema, self.consulta):
            self.como(usuario)
            self.assertEqual(self.client.get(URL).status_code, status.HTTP_403_FORBIDDEN)
            self.assertEqual(self.client.get(f'{URL}{solicitud.id}/').status_code, status.HTTP_403_FORBIDDEN)
            self.assertEqual(self.solicitar(CIERRE_ENERO, kpi=self.kpi2, usuario=usuario).status_code, status.HTTP_403_FORBIDDEN)
            for nombre in ('autorizar', 'rechazar', 'retirar'):
                self.assertEqual(
                    self.accion(solicitud, nombre, date(2027, 2, 1), usuario=usuario, observacion='x').status_code,
                    status.HTTP_403_FORBIDDEN,
                )

        solicitud.refresh_from_db()
        self.assertEqual(solicitud.estado, 'pendiente')

    def test_el_administrador_de_planificacion_ve_todas_pero_no_solicita(self):
        self.crear_pendiente()
        self.crear_pendiente(kpi=self.kpi2, usuario=self.beto)

        self.como(self.admin)
        self.assertEqual(len(self.client.get(URL).data), 2)
        self.assertEqual(len(self.client.get(URL, {'estado': 'pendiente', 'indicador': self.kpi2.id}).data), 1)
        self.assertEqual(self.solicitar(CIERRE_ENERO, usuario=self.admin).status_code, status.HTTP_403_FORBIDDEN)

    def test_el_ejecutor_ve_solo_las_suyas_y_no_resuelve(self):
        propia = self.crear_pendiente()
        ajena = self.crear_pendiente(kpi=self.kpi2, usuario=self.beto)

        self.como(self.ana)
        self.assertEqual([s['id'] for s in self.client.get(URL).data], [propia.id])
        self.assertEqual(self.client.get(f'{URL}{ajena.id}/').status_code, status.HTTP_404_NOT_FOUND)

        for nombre in ('autorizar', 'rechazar'):
            self.assertEqual(
                self.accion(propia, nombre, date(2027, 2, 1), usuario=self.ana, observacion='x').status_code,
                status.HTTP_403_FORBIDDEN,
            )

    def test_sin_edicion_ni_borrado(self):
        solicitud = self.crear_pendiente()

        # El permiso se evalúa antes que el método: se rechaza con 403 o 405.
        for usuario in (self.ana, self.admin):
            self.como(usuario)
            for respuesta in (
                self.client.patch(f'{URL}{solicitud.id}/', {'dias_solicitados': 2}, format='json'),
                self.client.put(f'{URL}{solicitud.id}/', {}, format='json'),
                self.client.delete(f'{URL}{solicitud.id}/'),
            ):
                self.assertIn(respuesta.status_code, (403, 405))

        self.assertTrue(SolicitudAmpliacionPlazo.objects.filter(pk=solicitud.pk, estado='pendiente').exists())

    def test_sin_autenticacion(self):
        self.client.force_authenticate(user=None)
        self.assertEqual(self.client.get(URL).status_code, status.HTTP_401_UNAUTHORIZED)


class CierreDePlanTests(AmpliacionesBase):
    """Ajuste de la Etapa 5: al Cerrar un Plan anual o estratégico, sus
    solicitudes pendientes quedan Sin efecto en la misma operación."""

    def setUp(self):
        super().setUp()
        self.pendiente = self.crear_pendiente()
        # Solicitudes ya resueltas: el cierre no debe tocarlas.
        periodo = self.pendiente.periodo
        base = {
            'indicador': self.kpi, 'periodo': periodo, 'solicitante': self.ana, 'motivo': 'x',
            'dias_solicitados': 3, 'fecha_limite_ordinaria': LIMITE_ORDINARIO,
        }
        self.resueltas = [
            SolicitudAmpliacionPlazo.objects.create(**base, estado=estado)
            for estado in ('rechazada', 'retirada', 'vencida', 'sin_efecto')
        ]
        self.resueltas.append(SolicitudAmpliacionPlazo.objects.create(
            **{**base, 'indicador': self.kpi2}, estado='autorizada', dias_autorizados=3,
            revisado_por=self.admin, fecha_limite_extraordinaria=date(2027, 2, 8),
        ))
        self.estados_resueltas = [(s.id, s.estado, s.observacion_revision) for s in self.resueltas]
        self.mediciones_antes = list(Medicion.objects.values_list('id', 'valor_resultado'))

    def cerrar_plan(self, url):
        self.como(self.admin)
        with self.en_fecha(date(2027, 2, 2)):
            return self.client.post(url)

    def cerrar_plan_anual(self):
        return self.cerrar_plan(f'/api/planes-anuales/{self.plan_anual.id}/cerrar/')

    def cerrar_plan_estrategico(self):
        return self.cerrar_plan(f'/api/planes-estrategicos/{self.plan.id}/cerrar/')

    def assertResueltasIntactas(self):
        actuales = [
            (s.id, s.estado, s.observacion_revision)
            for s in SolicitudAmpliacionPlazo.objects.filter(id__in=[r.id for r in self.resueltas]).order_by('id')
        ]
        self.assertEqual(actuales, self.estados_resueltas)
        self.assertEqual(list(Medicion.objects.values_list('id', 'valor_resultado')), self.mediciones_antes)

    def test_cerrar_el_plan_anual_deja_sin_efecto_la_pendiente(self):
        response = self.cerrar_plan_anual()

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.pendiente.refresh_from_db()
        self.assertEqual(self.pendiente.estado, 'sin_efecto')
        self.assertEqual(self.pendiente.observacion_revision, f'se cerró el {self.plan_anual.nombre}.')
        self.assertIsNotNone(self.pendiente.fecha_resolucion)
        self.assertResueltasIntactas()

        usuario, descripcion = self.bitacoras()[-1]
        self.assertEqual(usuario, 'admin_ampl')
        self.assertIn(f'#{self.pendiente.id}', descripcion)
        self.assertIn('quedó sin efecto: se cerró el', descripcion)
        aviso = self.notificaciones(self.ana, 'ampliacion_sin_efecto').get()
        self.assertEqual(aviso.enlace, f'/mediciones?tab=solicitudes&solicitud={self.pendiente.id}')

    def test_cerrar_el_plan_estrategico_deja_sin_efecto_la_pendiente(self):
        response = self.cerrar_plan_estrategico()

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.pendiente.refresh_from_db()
        self.assertEqual(self.pendiente.estado, 'sin_efecto')
        self.assertEqual(self.pendiente.observacion_revision, 'se cerró el Plan estratégico Plan ampliaciones.')
        self.assertResueltasIntactas()
        self.assertEqual(self.notificaciones(self.ana, 'ampliacion_sin_efecto').count(), 1)

    def test_solo_afecta_a_los_kpi_del_plan_cerrado(self):
        otro_plan = PlanEstrategico.objects.create(
            titulo='Otro plan', fecha_inicio=date(2027, 1, 1), fecha_fin=date(2030, 12, 31),
            estado=PlanEstrategico.ESTADO_EN_USO, creado_por=self.admin,
        )
        objetivo = ObjetivoGeneral.objects.create(plan_estrategico=otro_plan, texto_objetivo='OG2', creado_por=self.admin)
        otro_anual = PlanAnual.objects.create(
            plan_estrategico=otro_plan, anio=2027, estado=PlanAnual.ESTADO_EN_USO,
            fecha_inicio=date(2027, 1, 1), fecha_fin=date(2027, 12, 31), creado_por=self.admin,
        )
        self.objetivo_especifico = ObjetivoEspecifico.objects.create(
            plan_anual=otro_anual, objetivo_general=objetivo, texto_objetivo='OE2', creado_por=self.admin,
        )
        ajena = self.crear_pendiente(kpi=self.crear_kpi('KPI de otro plan'))

        self.cerrar_plan_estrategico()

        ajena.refresh_from_db()
        self.assertEqual(ajena.estado, 'pendiente')

    def test_sin_duplicados_al_cerrar_plan_anual_y_luego_estrategico(self):
        self.cerrar_plan_anual()
        bitacoras = len(self.bitacoras())

        self.assertEqual(self.cerrar_plan_estrategico().status_code, status.HTTP_200_OK)
        self.assertEqual(self.cerrar_plan_anual().status_code, status.HTTP_400_BAD_REQUEST)

        self.assertEqual(len(self.bitacoras()), bitacoras)
        self.assertEqual(self.notificaciones(self.ana, 'ampliacion_sin_efecto').count(), 1)
        self.pendiente.refresh_from_db()
        self.assertEqual(self.pendiente.observacion_revision, f'se cerró el {self.plan_anual.nombre}.')

    def test_despues_del_cierre_no_se_puede_resolver(self):
        self.cerrar_plan_anual()

        for nombre, usuario, datos in (
            ('autorizar', self.admin, {}),
            ('rechazar', self.admin, {'observacion': 'x'}),
            ('retirar', self.ana, {}),
        ):
            response = self.accion(self.pendiente, nombre, date(2027, 2, 2), usuario=usuario, **datos)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.pendiente.refresh_from_db()
        self.assertEqual(self.pendiente.estado, 'sin_efecto')

    def test_pendiente_de_un_plan_cerrado_sin_pasar_por_el_cierre_tampoco_se_resuelve(self):
        # Defensa adicional: plan cerrado por fuera de la API.
        PlanAnual.objects.filter(pk=self.plan_anual.pk).update(estado=PlanAnual.ESTADO_CERRADO)

        for nombre, usuario, datos in (
            ('autorizar', self.admin, {}),
            ('rechazar', self.admin, {'observacion': 'x'}),
            ('retirar', self.ana, {}),
        ):
            response = self.accion(self.pendiente, nombre, date(2027, 2, 2), usuario=usuario, **datos)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn('ya no puede resolverse', response.data['detail'])

        self.pendiente.refresh_from_db()
        self.assertEqual(self.pendiente.estado, 'pendiente')

    def test_si_falla_la_bitacora_de_la_solicitud_se_revierte_todo_el_cierre(self):
        from apps.auditoria import services as auditoria

        registrar_real = auditoria.registrar_bitacora

        def fallar_en_ampliaciones(usuario, accion, modulo, descripcion, request=None):
            if modulo == MODULO_AMPLIACIONES:
                raise RuntimeError('BD caída')
            return registrar_real(usuario, accion, modulo, descripcion, request=request)

        with mock.patch('apps.auditoria.services.registrar_bitacora', side_effect=fallar_en_ampliaciones):
            response = self.cerrar_plan_anual()

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.plan_anual.refresh_from_db()
        self.pendiente.refresh_from_db()
        self.assertEqual(self.plan_anual.estado, PlanAnual.ESTADO_EN_USO)
        self.assertEqual(self.pendiente.estado, 'pendiente')
        self.assertFalse(Bitacora.objects.filter(modulo='Planes anuales').exists())
        self.assertFalse(self.notificaciones(self.ana, 'ampliacion_sin_efecto').exists())

    def test_cierre_sin_solicitudes_pendientes_no_registra_nada_extra(self):
        self.accion(self.pendiente, 'retirar', date(2027, 2, 1), usuario=self.ana)
        bitacoras = len(self.bitacoras())

        self.assertEqual(self.cerrar_plan_anual().status_code, status.HTTP_200_OK)
        self.assertEqual(len(self.bitacoras()), bitacoras)
        self.assertFalse(self.notificaciones(self.ana, 'ampliacion_sin_efecto').exists())


class ConsultaBloqueoAmpliacionTests(AmpliacionesBase):
    """Regresión: el bloqueo con select_related('revisado_por') (opcional,
    LEFT OUTER JOIN) fallaba en PostgreSQL al autorizar, rechazar o retirar.
    SQLite no lo reproduce: se comprueba la estructura de la consulta."""

    def test_bloquea_solo_la_fila_de_la_solicitud_sin_outer_join(self):
        from .views import consulta_bloqueo_solicitud_ampliacion

        consulta = consulta_bloqueo_solicitud_ampliacion()

        self.assertTrue(consulta.query.select_for_update)
        self.assertEqual(consulta.query.select_for_update_of, ('self',))
        self.assertNotIn('LEFT OUTER JOIN', str(consulta.query).upper())
        self.assertNotIn('revisado_por', consulta.query.select_related)
