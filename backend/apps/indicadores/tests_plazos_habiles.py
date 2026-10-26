"""Transición real por inicio del período; sin cambiar reloj ni datos reales."""
from datetime import date, datetime
from unittest import mock
from django.test import SimpleTestCase
from django.utils import timezone
from . import plazos
from .serializers import MedicionSerializer, ConfiguracionMedicionesSerializer
from .models import Medicion, SolicitudAmpliacionPlazo, EstadoCumplimiento
from .tests_etapa5_ampliaciones import AmpliacionesBase
from .services import obtener_o_crear_periodo, obtener_o_crear_meta_vigente

class CalendarioTests(SimpleTestCase):
    def test_viernes_cruce_mes_y_decimo_habil(self):
        inicio = date(2027, 4, 1)
        cierre = date(2027, 4, 30)  # viernes
        ordinario = plazos.limite_ordinario(cierre, inicio)
        self.assertEqual(ordinario, date(2027, 5, 7))
        self.assertEqual(plazos.limite_maximo(cierre, ordinario, inicio), date(2027, 5, 14))
        self.assertEqual(plazos.limite_ampliado(ordinario, 5, inicio), date(2027, 5, 14))

    def test_corte_por_inicio_no_por_cierre(self):
        self.assertFalse(plazos.usa_dias_habiles(date(2026, 10, 1)))
        self.assertTrue(plazos.usa_dias_habiles(date(2026, 11, 1)))
        cierre = date(2026, 12, 31)
        self.assertEqual(plazos.limite_ordinario(cierre, date(2026, 10, 1)), date(2027, 1, 5))
        self.assertEqual(plazos.limite_ordinario(cierre, date(2026, 11, 1)), date(2027, 1, 7))

    def test_sabado_domingo_y_bisiesto(self):
        self.assertEqual(plazos.sumar_dias(date(2026, 10, 31), 5, True), date(2026, 11, 6))
        self.assertEqual(plazos.sumar_dias(date(2026, 11, 1), 5, True), date(2026, 11, 6))
        self.assertEqual(plazos.sumar_dias(date(2028, 2, 25), 5, True), date(2028, 3, 3))

    def test_minimo_autorizable_fin_de_semana(self):
        self.assertEqual(plazos.minimo_autorizable(date(2027, 2, 5), date(2027, 2, 6), date(2027, 1, 1)), 1)
        self.assertEqual(plazos.minimo_autorizable(date(2027, 2, 5), date(2027, 2, 9), date(2027, 1, 1)), 2)

class FlujoHabilTests(AmpliacionesBase):
    calendario_anterior = False
    def test_solicitud_quinto_dia_y_maximo(self):
        response = self.solicitar(date(2027, 2, 5), dias=5)
        self.assertEqual(response.status_code, 201, response.data)
        self.assertTrue(response.data['usa_dias_habiles'])
        self.assertEqual(response.data['fecha_limite_solicitada'], '2027-02-12')
        self.assertEqual(str(response.data['fecha_limite_maxima']), '2027-02-12')
        self.assertEqual(self.solicitar(date(2027, 2, 5), dias=6, kpi=self.kpi2).status_code, 400)

    def test_autorizacion_registro_ultimo_dia(self):
        solicitud = self.crear_pendiente(date(2027, 2, 5), dias=5)
        response = self.accion(solicitud, 'autorizar', date(2027, 2, 12))
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(str(response.data['fecha_limite_extraordinaria']), '2027-02-12')
        self.assertEqual(self.registrar(date(2027, 2, 12)).status_code, 201)

    def test_rechazo(self):
        solicitud = self.crear_pendiente(dias=5)
        response = self.accion(solicitud, 'rechazar', date(2027, 2, 1), observacion='No procede')
        self.assertEqual(response.status_code, 200, response.data)
        solicitud.refresh_from_db()
        self.assertEqual(solicitud.estado, 'rechazada')

    def test_pendiente_y_cierre_idempotente(self):
        self.crear_pendiente(dias=5)
        self.cerrar(date(2027, 2, 12))
        self.assertEqual(self.omisiones().count(), 0)
        self.assertEqual(self.registrar(date(2027, 2, 12)).status_code, 400)
        self.cerrar(date(2027, 2, 13))
        self.assertEqual(self.omisiones().count(), 1)
        self.cerrar(date(2027, 2, 13))
        self.assertEqual(self.omisiones().count(), 1)

    def test_cierre_ordinario_inclusivo(self):
        self.cerrar(date(2027, 2, 5))
        self.assertEqual(self.omisiones().count(), 0)
        self.cerrar(date(2027, 2, 6))
        self.assertEqual(self.omisiones().count(), 1)

    def test_configuracion_no_cambia_historicos(self):
        for dias in (1, 6, 10, 11):
            serializer = ConfiguracionMedicionesSerializer(data={'dias_plazo_registro': dias})
            self.assertFalse(serializer.is_valid())
        serializer = ConfiguracionMedicionesSerializer(data={'dias_plazo_registro': 5})
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_oportunidad_anterior_sigue_calendario(self):
        # Período anterior que cierra en viernes: +5 calendario vs +5 hábiles.
        periodo = obtener_o_crear_periodo(self.kpi, date(2026, 7, 1))
        medicion = Medicion.objects.create(
            indicador=self.kpi, periodo=periodo, meta=obtener_o_crear_meta_vigente(self.kpi),
            fecha_medicion=date(2026, 7, 31), valor_resultado=80, registrado_por=self.ana,
            estado_cumplimiento=EstadoCumplimiento.objects.get(nombre="En riesgo"),
        )
        registro = timezone.make_aware(datetime(2026, 8, 6, 12))
        Medicion.objects.filter(pk=medicion.pk).update(fecha_registro=registro)
        medicion.refresh_from_db()
        for hoy in (date(2026, 10, 25), date(2027, 5, 1)):
            with self.en_fecha(hoy):
                self.assertEqual(MedicionSerializer(medicion).data['oportunidad_registro'], 'Fuera de plazo')

    def test_reglas_anteriores_pendiente_y_autorizada(self):
        periodo = obtener_o_crear_periodo(self.kpi, date(2026, 7, 1))
        solicitud = SolicitudAmpliacionPlazo.objects.create(
            indicador=self.kpi, periodo=periodo, solicitante=self.ana, motivo='Prueba',
            dias_solicitados=10, fecha_limite_ordinaria=date(2026, 8, 5),
        )
        self.assertEqual(solicitud.fecha_limite_maxima, date(2026, 8, 15))
        response = self.accion(solicitud, 'autorizar', date(2026, 8, 6))
        self.assertEqual(response.status_code, 200, response.data)
        solicitud.refresh_from_db()
        self.assertEqual(solicitud.fecha_limite_extraordinaria, date(2026, 8, 15))

    def test_oportunidad_nueva_usa_vencimiento_habil(self):
        periodo = obtener_o_crear_periodo(self.kpi, date(2027, 4, 1))
        medicion = Medicion.objects.create(
            indicador=self.kpi, periodo=periodo, meta=obtener_o_crear_meta_vigente(self.kpi),
            fecha_medicion=date(2027, 4, 30), valor_resultado=80, registrado_por=self.ana,
            estado_cumplimiento=EstadoCumplimiento.objects.get(nombre="En riesgo"),
        )
        Medicion.objects.filter(pk=medicion.pk).update(
            fecha_registro=timezone.make_aware(datetime(2027, 5, 7, 23, 59)))
        medicion.refresh_from_db()
        datos = MedicionSerializer(medicion).data
        self.assertEqual(datos['oportunidad_registro'], 'Tardío')
        self.assertFalse(datos['registrada_con_ampliacion'])

    def test_c2_incorporacion_abril_y_cierre_en_viernes(self):
        self.kpi.fecha_autorizacion = timezone.make_aware(datetime(2027, 4, 15, 12))
        self.kpi.save(update_fields=['fecha_autorizacion'])
        info = self.info(date(2027, 5, 7))
        self.assertEqual(info['fecha_inicio_periodo'], date(2027, 4, 1))
        self.assertTrue(info['periodo_parcial'])
        self.assertEqual(info['inicio_seguimiento'], date(2027, 4, 15))
        self.assertEqual(info['fecha_limite_registro'], date(2027, 5, 7))
        self.assertTrue(info['disponible'])
        self.cerrar(date(2027, 5, 7))
        self.assertEqual(self.omisiones().count(), 0)
        self.cerrar(date(2027, 5, 8))
        self.cerrar(date(2027, 5, 8))
        self.assertEqual(self.omisiones().count(), 1)
        self.assertEqual(self.omisiones().get().periodo.fecha_inicio, date(2027, 4, 1))

    def test_no_registra_despues_del_decimo_habil(self):
        solicitud = self.crear_pendiente(dias=5)
        self.assertEqual(self.accion(solicitud, 'autorizar', date(2027, 2, 1)).status_code, 200)
        self.assertEqual(self.registrar(date(2027, 2, 13)).status_code, 400)
        self.cerrar(date(2027, 2, 13))
        self.cerrar(date(2027, 2, 13))
        self.assertEqual(self.omisiones().count(), 1)

    def test_flujo_real_a_ambos_lados_del_corte(self):
        self.plan.fecha_inicio = date(2026, 1, 1)
        self.plan.save(update_fields=['fecha_inicio'])
        self.plan_anual.anio = 2026
        self.plan_anual.fecha_inicio = date(2026, 1, 1)
        self.plan_anual.fecha_fin = date(2026, 12, 31)
        self.plan_anual.save(update_fields=['anio', 'fecha_inicio', 'fecha_fin'])
        for mes, cierre, limite in (
            (10, date(2026, 10, 31), date(2026, 11, 5)),
            (11, date(2026, 11, 30), date(2026, 12, 7)),
        ):
            with self.subTest(mes=mes):
                self.kpi.fecha_autorizacion = timezone.make_aware(datetime(2026, mes, 15, 12))
                self.kpi.save(update_fields=['fecha_autorizacion'])
                self.kpi.refresh_from_db()
                info = self.info(limite)
                self.assertEqual(info['fecha_inicio_periodo'], date(2026, mes, 1))
                self.assertEqual(info['fecha_cierre'], cierre)
                self.assertEqual(info['fecha_limite_registro'], limite)
                self.assertTrue(info['disponible'])
                self.assertEqual(self.info(date(2027, 5, 1))['fecha_limite_registro'], limite)
