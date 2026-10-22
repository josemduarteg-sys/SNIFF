"""C2: inicio de la medición de un KPI creado a mitad de año.

Hernán confirmó que un KPI puede crearse a mitad de año y se mide desde ese
día hasta terminar el año. Decisiones del proyecto: la fecha base es la de
autorización (la de creación si un KPI histórico no la tiene), nunca antes
del inicio de la vigencia del plan anual; el primer periodo exigible es el de
la cuadrícula del plan que contiene esa fecha (puede ser parcial)."""

from datetime import date, datetime
from decimal import Decimal
from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.estrategia.models import ObjetivoEspecifico, ObjetivoGeneral, PlanAnual, PlanEstrategico
from apps.usuarios.models import Rol, Usuario

from .models import Alerta, EstadoCumplimiento, Frecuencia, IndicadorKPI, Medicion
from .services import (
    TIPO_ALERTA_PERIODO_VENCIDO,
    cerrar_mediciones_vencidas,
    crear_rangos_provisionales,
    evaluar_solicitud_ampliacion,
    generar_alertas_periodos_vencidos,
    obtener_info_siguiente_periodo,
    obtener_o_crear_meta_vigente,
    obtener_o_crear_periodo,
    obtener_primer_periodo_exigible,
)


def crear_usuario(username, rol_nombre):
    rol, _ = Rol.objects.get_or_create(nombre=rol_nombre, defaults={'descripcion': 'Rol de prueba', 'estado': True})
    usuario = Usuario.objects.create_user(username=username, password='clave-prueba-123')
    usuario.rol = rol
    usuario.correo = f'{username}@sniff.test'
    usuario.save()
    return usuario


def momento(fecha):
    return timezone.make_aware(datetime(fecha.year, fecha.month, fecha.day, 10, 0))


class InicioKpiBase(APITestCase):
    def setUp(self):
        self.admin = crear_usuario('admin_c2', 'Administrador de planificación')
        self.ejecutor = crear_usuario('ejecutor_c2', 'Ejecutor operativo')

        for nombre, color in [('Incumplido', 'rojo'), ('En riesgo', 'amarillo'), ('Favorable', 'verde')]:
            EstadoCumplimiento.objects.get_or_create(nombre=nombre, defaults={'color': color, 'estado': True})

        self.plan = PlanEstrategico.objects.create(
            titulo='Plan C2', fecha_inicio=date(2027, 1, 1), fecha_fin=date(2030, 12, 31),
            estado=PlanEstrategico.ESTADO_EN_USO, creado_por=self.admin,
        )
        self.objetivo_general = ObjetivoGeneral.objects.create(plan_estrategico=self.plan, texto_objetivo='OG', creado_por=self.admin)
        self.plan_anual = self.crear_plan_anual(2027)

    def crear_plan_anual(self, anio, inicio=None, fin=None):
        # Un solo plan anual en uso por plan estratégico: el anterior se
        # cierra (base de pruebas) antes de abrir el nuevo.
        PlanAnual.objects.filter(plan_estrategico=self.plan, estado=PlanAnual.ESTADO_EN_USO).update(
            estado=PlanAnual.ESTADO_CERRADO,
        )
        plan_anual = PlanAnual.objects.create(
            plan_estrategico=self.plan, anio=anio, estado=PlanAnual.ESTADO_EN_USO,
            fecha_inicio=inicio or date(anio, 1, 1), fecha_fin=fin or date(anio, 12, 31), creado_por=self.admin,
        )
        plan_anual.objetivo_especifico_c2 = ObjetivoEspecifico.objects.create(
            plan_anual=plan_anual, objetivo_general=self.objetivo_general, texto_objetivo=f'OE {anio}', creado_por=self.admin,
        )
        return plan_anual

    def crear_kpi(self, autorizado=None, creado=None, frecuencia='Mensual', plan_anual=None, nombre=None):
        """KPI autorizado con fechas controladas (fecha_creacion es automática:
        se fija después con update)."""
        plan_anual = plan_anual or self.plan_anual
        kpi = IndicadorKPI.objects.create(
            objetivo_especifico=plan_anual.objetivo_especifico_c2,
            frecuencia=Frecuencia.objects.get_or_create(nombre=frecuencia, defaults={'estado': True})[0],
            nombre=nombre or f'KPI {frecuencia} {autorizado or creado}', formula_medicion='R', unidad_medida='%',
            valor_meta=Decimal('85'), estado='autorizado', creado_por=self.admin,
        )
        IndicadorKPI.objects.filter(pk=kpi.pk).update(
            fecha_creacion=momento(creado or autorizado or date(2026, 12, 1)),
            fecha_autorizacion=momento(autorizado) if autorizado else None,
        )
        crear_rangos_provisionales(kpi)
        return IndicadorKPI.objects.get(pk=kpi.pk)

    def info(self, kpi, hoy):
        return obtener_info_siguiente_periodo(kpi, fecha_referencia=hoy)

    def medicion(self, kpi, mes, valor='90'):
        periodo = obtener_o_crear_periodo(kpi, date(2027, mes, 1))
        return Medicion.objects.create(
            indicador=kpi, meta=obtener_o_crear_meta_vigente(kpi), periodo=periodo,
            estado_cumplimiento=EstadoCumplimiento.objects.get(nombre='Favorable'),
            fecha_medicion=periodo.fecha_fin, valor_resultado=Decimal(valor), registrado_por=self.ejecutor,
        )


class PrimerPeriodoTests(InicioKpiBase):
    def test_kpi_creado_antes_del_inicio_del_plan_mide_desde_el_primer_periodo(self):
        kpi = self.crear_kpi(autorizado=date(2026, 12, 15), creado=date(2026, 12, 10))

        info = self.info(kpi, date(2027, 1, 31))

        self.assertEqual(kpi.fecha_inicio_seguimiento, date(2027, 1, 1))
        self.assertEqual(info['periodo_nombre'], 'enero 2027')
        self.assertFalse(info['periodo_parcial'])
        self.assertTrue(info['disponible'])

    def test_autorizado_a_mitad_de_anio_en_cada_frecuencia(self):
        """Autorizado el 15/05/2027 con la cuadrícula del plan (enero)."""
        esperados = {
            'Mensual': ('mayo 2027', date(2027, 5, 31)),
            'Bimestral': ('mayo - junio 2027', date(2027, 6, 30)),
            'Trimestral': ('abril - junio 2027', date(2027, 6, 30)),
            'Semestral': ('enero - junio 2027', date(2027, 6, 30)),
            'Anual': ('enero - diciembre 2027', date(2027, 12, 31)),
        }

        for frecuencia, (nombre, cierre) in esperados.items():
            kpi = self.crear_kpi(autorizado=date(2027, 5, 15), frecuencia=frecuencia)
            info = self.info(kpi, date(2027, 5, 20))

            self.assertEqual((info['periodo_nombre'], info['fecha_cierre']), (nombre, cierre), frecuencia)
            self.assertEqual(info['inicio_seguimiento'], date(2027, 5, 15), frecuencia)
            self.assertTrue(info['periodo_parcial'], frecuencia)

    def test_primer_periodo_parcial_de_octubre(self):
        kpi = self.crear_kpi(autorizado=date(2027, 10, 9))

        antes = self.info(kpi, date(2027, 10, 20))
        self.assertEqual(antes['periodo_nombre'], 'octubre 2027')
        self.assertEqual(antes['fecha_cierre'], date(2027, 10, 31))
        self.assertEqual(antes['inicio_seguimiento'], date(2027, 10, 9))
        self.assertTrue(antes['periodo_parcial'])
        self.assertFalse(antes['disponible'])  # Se registra desde el cierre.

        self.assertTrue(self.info(kpi, date(2027, 10, 31))['disponible'])

        self.client.force_authenticate(user=self.ejecutor)
        with mock.patch('apps.indicadores.services.hoy', return_value=date(2027, 10, 31)):
            respuesta = self.client.post('/api/mediciones/', {'indicador': kpi.id, 'valor_resultado': '80'}, format='json')

        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED, respuesta.data)
        self.assertEqual(Medicion.objects.get(indicador=kpi).periodo.fecha_inicio, date(2027, 10, 1))

    def test_autorizacion_posterior_a_la_creacion(self):
        kpi = self.crear_kpi(creado=date(2027, 3, 10), autorizado=date(2027, 6, 2))

        self.assertEqual(kpi.fecha_inicio_seguimiento, date(2027, 6, 2))
        self.assertEqual(self.info(kpi, date(2027, 6, 30))['periodo_nombre'], 'junio 2027')

    def test_kpi_historico_sin_fecha_de_autorizacion_usa_la_de_creacion(self):
        kpi = self.crear_kpi(creado=date(2027, 4, 20), autorizado=None)

        self.assertIsNone(kpi.fecha_autorizacion)
        self.assertEqual(kpi.fecha_inicio_seguimiento, date(2027, 4, 20))
        self.assertEqual(self.info(kpi, date(2027, 4, 30))['periodo_nombre'], 'abril 2027')

    def test_plan_anual_con_fechas_especificas(self):
        plan_anual = self.crear_plan_anual(2028, inicio=date(2028, 3, 1), fin=date(2028, 12, 31))

        # Cuadrícula bimestral anclada en marzo: mar-abr, may-jun...
        kpi = self.crear_kpi(autorizado=date(2028, 6, 10), frecuencia='Bimestral', plan_anual=plan_anual)
        self.assertEqual(self.info(kpi, date(2028, 6, 20))['periodo_nombre'], 'mayo - junio 2028')

        # Autorizado antes del inicio del plan: empieza con el plan, no antes.
        temprano = self.crear_kpi(autorizado=date(2028, 1, 15), frecuencia='Bimestral', plan_anual=plan_anual)
        self.assertEqual(temprano.fecha_inicio_seguimiento, date(2028, 3, 1))
        self.assertEqual(self.info(temprano, date(2028, 4, 30))['periodo_nombre'], 'marzo - abril 2028')

    def test_autorizado_despues_de_la_vigencia_no_tiene_periodos(self):
        kpi = self.crear_kpi(autorizado=date(2028, 1, 5))

        info = self.info(kpi, date(2028, 2, 10))

        self.assertIsNone(info['fecha_cierre'])
        self.assertIn('No existen más periodos', info['motivo'])
        self.assertEqual(cerrar_mediciones_vencidas(fecha_referencia=date(2028, 3, 1))['cierres_creados'], 0)

        # Plan que termina a mitad de mes y KPI autorizado después.
        corto = self.crear_plan_anual(2029, inicio=date(2029, 1, 1), fin=date(2029, 6, 15))
        tardio = self.crear_kpi(autorizado=date(2029, 6, 20), plan_anual=corto)
        self.assertGreater(obtener_primer_periodo_exigible(tardio), date(2029, 6, 1))
        self.assertIsNone(self.info(tardio, date(2029, 7, 10))['fecha_cierre'])


class HistoricosYCierreTests(InicioKpiBase):
    def test_mediciones_retroactivas_se_conservan_y_no_se_exigen_periodos_intermedios(self):
        """Como los KPI #9 y #10: autorizado el 24/09 con mediciones
        retroactivas de enero a marzo."""
        kpi = self.crear_kpi(autorizado=date(2027, 9, 24))
        retroactivas = [self.medicion(kpi, mes) for mes in (1, 2, 3)]

        self.assertEqual(self.info(kpi, date(2027, 9, 30))['periodo_nombre'], 'septiembre 2027')

        resultado = cerrar_mediciones_vencidas(fecha_referencia=date(2027, 10, 21))

        omisiones = Medicion.objects.filter(indicador=kpi, cierre_automatico=True)
        self.assertEqual(resultado['cierres_creados'], 1)
        self.assertEqual([m.periodo.fecha_inicio for m in omisiones], [date(2027, 9, 1)])
        # Las retroactivas siguen intactas y no hay omisiones de abril a agosto.
        self.assertEqual(Medicion.objects.filter(indicador=kpi, cierre_automatico=False).count(), 3)
        for medicion in retroactivas:
            medicion.refresh_from_db()
            self.assertEqual(medicion.valor_resultado, Decimal('90'))
        self.assertFalse(Medicion.objects.filter(indicador=kpi, periodo__fecha_inicio__range=(date(2027, 4, 1), date(2027, 8, 1))).exists())

    def test_kpi_con_mediciones_hasta_agosto_sigue_en_septiembre(self):
        """Como los KPI #11 y #12."""
        kpi = self.crear_kpi(autorizado=date(2027, 9, 27))
        for mes in range(1, 9):
            self.medicion(kpi, mes)

        self.assertEqual(self.info(kpi, date(2027, 9, 30))['periodo_nombre'], 'septiembre 2027')

    def test_cierre_sin_omisiones_anteriores_al_inicio(self):
        """Como los KPI #13 a #15: autorizados el 09/10, sin mediciones. Antes
        de C2 el cierre habría creado nueve omisiones (enero a septiembre)."""
        kpi = self.crear_kpi(autorizado=date(2027, 10, 9))

        self.assertEqual(cerrar_mediciones_vencidas(fecha_referencia=date(2027, 10, 21))['cierres_creados'], 0)
        self.assertEqual(cerrar_mediciones_vencidas(fecha_referencia=date(2027, 11, 6))['cierres_creados'], 1)
        self.assertEqual(
            [m.periodo.fecha_inicio for m in Medicion.objects.filter(indicador=kpi, cierre_automatico=True)],
            [date(2027, 10, 1)],
        )

    def test_simulacion_de_la_tarea_diaria_no_guarda_nada(self):
        self.crear_kpi(autorizado=date(2027, 10, 9))
        salida = StringIO()

        with mock.patch('apps.indicadores.services.hoy', return_value=date(2027, 11, 6)):
            call_command('ejecutar_tareas_mediciones', '--simular', stdout=salida)

        self.assertIn('Cierres automáticos: 1', salida.getvalue())
        self.assertFalse(Medicion.objects.exists())

    def test_alertas_solo_desde_el_inicio_del_seguimiento(self):
        kpi = self.crear_kpi(autorizado=date(2027, 10, 9))

        # Al 21/10 ningún periodo exigible cerró: no hay alerta de enero a septiembre.
        generar_alertas_periodos_vencidos(fecha_referencia=date(2027, 10, 21))
        self.assertFalse(Alerta.objects.filter(indicador=kpi).exists())

        generar_alertas_periodos_vencidos(fecha_referencia=date(2027, 11, 2))
        alerta = Alerta.objects.get(indicador=kpi, tipo_alerta=TIPO_ALERTA_PERIODO_VENCIDO)
        self.assertIn('periodo de octubre 2027 (', alerta.mensaje)

    def test_solicitud_de_ampliacion_apunta_al_primer_periodo_exigible(self):
        kpi = self.crear_kpi(autorizado=date(2027, 10, 9))

        info, motivo = evaluar_solicitud_ampliacion(kpi, fecha_referencia=date(2027, 10, 31))

        self.assertEqual(motivo, '')
        self.assertEqual(info['periodo_nombre'], 'octubre 2027')

    def test_la_api_expone_el_inicio_del_seguimiento(self):
        kpi = self.crear_kpi(autorizado=date(2027, 10, 9))
        self.client.force_authenticate(user=self.admin)

        with mock.patch('apps.indicadores.services.hoy', return_value=date(2027, 10, 31)):
            detalle = self.client.get(f'/api/indicadores-kpi/{kpi.id}/').data
            siguiente = self.client.get('/api/mediciones/siguiente-periodo/', {'indicador': kpi.id}).data

        self.assertEqual(detalle['fecha_inicio_seguimiento'], date(2027, 10, 9))
        self.assertEqual(siguiente['inicio_seguimiento'], date(2027, 10, 9))
        self.assertTrue(siguiente['periodo_parcial'])
        self.assertEqual(siguiente['periodo_nombre'], 'octubre 2027')
