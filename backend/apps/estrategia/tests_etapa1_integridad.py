"""Etapa 1 de correcciones post-auditoría (20/10/2026): integridad de la
jerarquía Plan estratégico -> Objetivo general / Plan anual -> Objetivo
específico. Hallazgos A1, A2 y la parte de integridad de M9."""

from datetime import date
from decimal import Decimal

from rest_framework import status
from rest_framework.test import APITestCase

from apps.auditoria.models import Bitacora
from apps.indicadores.models import Alerta, EstadoCumplimiento, Frecuencia, IndicadorKPI, Medicion
from apps.indicadores.services import (
    crear_rangos_provisionales,
    obtener_estado_para_medicion,
    obtener_o_crear_meta_vigente,
    obtener_o_crear_periodo,
)
from apps.usuarios.models import Rol, Usuario

from .models import (
    ObjetivoEspecifico,
    ObjetivoGeneral,
    PlanAnual,
    PlanEstrategico,
    PonderacionAnualObjetivoGeneral,
)
from .services import obtener_o_crear_objetivo_especifico_directo


def crear_usuario(username, rol_nombre):
    rol, _ = Rol.objects.get_or_create(
        nombre=rol_nombre,
        defaults={'descripcion': 'Rol de prueba', 'estado': True},
    )

    usuario = Usuario.objects.create_user(username=username, password='clave-prueba-123')
    usuario.rol = rol
    usuario.correo = f'{username}@sniff.test'
    usuario.save()

    return usuario


class IntegridadJerarquiaBase(APITestCase):
    def setUp(self):
        self.usuario = crear_usuario('admin_planif_etapa1', 'Administrador de planificación')
        self.client.force_authenticate(user=self.usuario)

        self.plan_a = self.crear_plan('Plan A', PlanEstrategico.ESTADO_EN_USO)
        self.plan_b = self.crear_plan('Plan B', PlanEstrategico.ESTADO_EN_USO)
        self.plan_borrador = self.crear_plan('Plan Borrador', PlanEstrategico.ESTADO_BORRADOR)
        self.plan_cerrado = self.crear_plan('Plan Cerrado', PlanEstrategico.ESTADO_CERRADO)

        self.og_a = self.crear_objetivo_general(self.plan_a, 'Objetivo general A')
        self.og_a2 = self.crear_objetivo_general(self.plan_a, 'Objetivo general A2')
        self.og_b = self.crear_objetivo_general(self.plan_b, 'Objetivo general B')

        self.pa_a_2027 = self.crear_plan_anual(self.plan_a, 2027, PlanAnual.ESTADO_EN_USO)
        self.pa_a_2028 = self.crear_plan_anual(self.plan_a, 2028, PlanAnual.ESTADO_BORRADOR)
        self.pa_b_2027 = self.crear_plan_anual(self.plan_b, 2027, PlanAnual.ESTADO_EN_USO)
        self.pa_b_2028 = self.crear_plan_anual(self.plan_b, 2028, PlanAnual.ESTADO_CERRADO)
        self.pa_b_2029 = self.crear_plan_anual(self.plan_b, 2029, PlanAnual.ESTADO_BORRADOR)

        self.frecuencia = Frecuencia.objects.create(nombre='Mensual', estado=True)

    def crear_plan(self, titulo, estado):
        return PlanEstrategico.objects.create(
            titulo=titulo,
            # Objetos date (no strings): las propiedades de vigencia del KPI
            # comparan estas fechas en memoria sin recargarlas de la base.
            fecha_inicio=date(2027, 1, 1),
            fecha_fin=date(2030, 12, 31),
            estado=estado,
            creado_por=self.usuario,
        )

    def crear_objetivo_general(self, plan, texto):
        return ObjetivoGeneral.objects.create(
            plan_estrategico=plan, texto_objetivo=texto, creado_por=self.usuario,
        )

    def crear_plan_anual(self, plan, anio, estado):
        return PlanAnual.objects.create(
            plan_estrategico=plan, anio=anio, estado=estado, creado_por=self.usuario,
        )

    def crear_objetivo_especifico(self, plan_anual, objetivo_general, texto='Objetivo específico'):
        return ObjetivoEspecifico.objects.create(
            plan_anual=plan_anual,
            objetivo_general=objetivo_general,
            texto_objetivo=texto,
            creado_por=self.usuario,
        )

    def crear_kpi(self, objetivo_especifico, nombre='KPI etapa 1', estado='autorizado'):
        return IndicadorKPI.objects.create(
            objetivo_especifico=objetivo_especifico,
            frecuencia=self.frecuencia,
            nombre=nombre,
            formula_medicion='Resultado / Meta x 100',
            unidad_medida='%',
            valor_meta=Decimal('85'),
            estado=estado,
            creado_por=self.usuario,
        )


class ObjetivoGeneralTrasladoTests(IntegridadJerarquiaBase):
    """A1: cambio de Plan estratégico de un objetivo general."""

    def url(self, objetivo):
        return f'/api/objetivos-generales/{objetivo.id}/'

    def test_sin_dependencias_puede_trasladarse_a_plan_en_uso(self):
        response = self.client.patch(self.url(self.og_a), {'plan_estrategico': self.plan_b.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.og_a.refresh_from_db()
        self.assertEqual(self.og_a.plan_estrategico_id, self.plan_b.id)

    def test_sin_dependencias_no_puede_trasladarse_a_plan_borrador(self):
        response = self.client.patch(self.url(self.og_a), {'plan_estrategico': self.plan_borrador.id})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.og_a.refresh_from_db()
        self.assertEqual(self.og_a.plan_estrategico_id, self.plan_a.id)

    def test_no_puede_trasladarse_a_plan_cerrado(self):
        response = self.client.patch(self.url(self.og_a), {'plan_estrategico': self.plan_cerrado.id})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.og_a.refresh_from_db()
        self.assertEqual(self.og_a.plan_estrategico_id, self.plan_a.id)

    def test_con_objetivo_especifico_no_puede_trasladarse(self):
        objetivo_especifico = self.crear_objetivo_especifico(self.pa_a_2027, self.og_a)

        response = self.client.patch(self.url(self.og_a), {'plan_estrategico': self.plan_b.id})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('plan_estrategico', response.data)
        self.og_a.refresh_from_db()
        objetivo_especifico.refresh_from_db()
        self.assertEqual(self.og_a.plan_estrategico_id, self.plan_a.id)
        self.assertEqual(objetivo_especifico.objetivo_general_id, self.og_a.id)
        self.assertEqual(objetivo_especifico.plan_anual_id, self.pa_a_2027.id)

    def test_con_kpi_directo_no_puede_trasladarse(self):
        implicito = obtener_o_crear_objetivo_especifico_directo(self.pa_a_2027, self.og_a, self.usuario)
        kpi = self.crear_kpi(implicito)

        response = self.client.patch(self.url(self.og_a), {'plan_estrategico': self.plan_b.id})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        kpi.refresh_from_db()
        self.assertEqual(kpi.objetivo_general.id, self.og_a.id)
        self.assertEqual(kpi.plan_estrategico.id, self.plan_a.id)

    def test_con_ponderacion_anual_no_puede_trasladarse(self):
        PonderacionAnualObjetivoGeneral.objects.create(
            objetivo_general=self.og_a, plan_anual=self.pa_a_2027,
            porcentaje=Decimal('40'), creado_por=self.usuario,
        )

        response = self.client.patch(self.url(self.og_a), {'plan_estrategico': self.plan_b.id})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.og_a.refresh_from_db()
        self.assertEqual(self.og_a.plan_estrategico_id, self.plan_a.id)

    def test_con_dependencias_editar_texto_reenviando_el_mismo_plan_funciona(self):
        # Es lo que envía el formulario al editar solo el texto.
        self.crear_objetivo_especifico(self.pa_a_2027, self.og_a)

        response = self.client.patch(self.url(self.og_a), {
            'plan_estrategico': self.plan_a.id,
            'texto_objetivo': 'Texto corregido',
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.og_a.refresh_from_db()
        self.assertEqual(self.og_a.texto_objetivo, 'Texto corregido')

    def test_campo_puede_cambiar_plan_estrategico(self):
        self.crear_objetivo_especifico(self.pa_a_2027, self.og_a)

        con_dependencias = self.client.get(self.url(self.og_a))
        sin_dependencias = self.client.get(self.url(self.og_a2))

        self.assertFalse(con_dependencias.data['puede_cambiar_plan_estrategico'])
        self.assertTrue(sin_dependencias.data['puede_cambiar_plan_estrategico'])

    def test_ejecutor_operativo_no_puede_trasladar(self):
        ejecutor = crear_usuario('ejecutor_etapa1', 'Ejecutor operativo')
        self.client.force_authenticate(user=ejecutor)

        response = self.client.patch(self.url(self.og_a2), {'plan_estrategico': self.plan_b.id})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_usuario_consulta_no_puede_trasladar(self):
        consulta = crear_usuario('consulta_etapa1', 'Usuario de consulta')
        self.client.force_authenticate(user=consulta)

        response = self.client.patch(self.url(self.og_a2), {'plan_estrategico': self.plan_b.id})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class ObjetivoEspecificoTrasladoTests(IntegridadJerarquiaBase):
    """A2: cambio de Plan anual u Objetivo general de un objetivo específico."""

    def url(self, objetivo):
        return f'/api/objetivos-especificos/{objetivo.id}/'

    def test_sin_kpi_puede_trasladarse_a_plan_anual_en_uso_coherente(self):
        objetivo = self.crear_objetivo_especifico(self.pa_a_2027, self.og_a)

        response = self.client.patch(self.url(objetivo), {
            'plan_anual': self.pa_b_2027.id,
            'objetivo_general': self.og_b.id,
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        objetivo.refresh_from_db()
        self.assertEqual(objetivo.plan_anual_id, self.pa_b_2027.id)
        self.assertEqual(objetivo.objetivo_general_id, self.og_b.id)

    def test_sin_kpi_puede_cambiar_objetivo_general_del_mismo_plan(self):
        objetivo = self.crear_objetivo_especifico(self.pa_a_2027, self.og_a)

        response = self.client.patch(self.url(objetivo), {'objetivo_general': self.og_a2.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_sin_kpi_no_puede_trasladarse_a_plan_anual_borrador(self):
        objetivo = self.crear_objetivo_especifico(self.pa_a_2027, self.og_a)

        response = self.client.patch(self.url(objetivo), {'plan_anual': self.pa_a_2028.id})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        objetivo.refresh_from_db()
        self.assertEqual(objetivo.plan_anual_id, self.pa_a_2027.id)

    def test_sin_kpi_no_puede_trasladarse_a_plan_anual_cerrado(self):
        objetivo = self.crear_objetivo_especifico(self.pa_a_2027, self.og_a)

        response = self.client.patch(self.url(objetivo), {
            'plan_anual': self.pa_b_2028.id,
            'objetivo_general': self.og_b.id,
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        objetivo.refresh_from_db()
        self.assertEqual(objetivo.plan_anual_id, self.pa_a_2027.id)

    def test_no_acepta_objetivo_general_de_otra_estrategia(self):
        objetivo = self.crear_objetivo_especifico(self.pa_a_2027, self.og_a)

        response = self.client.patch(self.url(objetivo), {'objetivo_general': self.og_b.id})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_con_kpi_no_puede_cambiar_objetivo_general(self):
        objetivo = self.crear_objetivo_especifico(self.pa_a_2027, self.og_a)
        kpi = self.crear_kpi(objetivo)

        response = self.client.patch(self.url(objetivo), {'objetivo_general': self.og_a2.id})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('objetivo_general', response.data)
        objetivo.refresh_from_db()
        kpi.refresh_from_db()
        self.assertEqual(objetivo.objetivo_general_id, self.og_a.id)
        self.assertEqual(kpi.objetivo_especifico_id, objetivo.id)

    def test_con_kpi_no_puede_cambiar_plan_anual(self):
        objetivo = self.crear_objetivo_especifico(self.pa_a_2027, self.og_a)
        self.crear_kpi(objetivo)

        response = self.client.patch(self.url(objetivo), {
            'plan_anual': self.pa_b_2027.id,
            'objetivo_general': self.og_b.id,
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('plan_anual', response.data)
        objetivo.refresh_from_db()
        self.assertEqual(objetivo.plan_anual_id, self.pa_a_2027.id)

    def test_con_kpi_anulado_tambien_queda_protegido(self):
        objetivo = self.crear_objetivo_especifico(self.pa_a_2027, self.og_a)
        self.crear_kpi(objetivo, estado='anulado')

        response = self.client.patch(self.url(objetivo), {'objetivo_general': self.og_a2.id})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_con_kpi_editar_texto_reenviando_las_mismas_relaciones_funciona(self):
        objetivo = self.crear_objetivo_especifico(self.pa_a_2027, self.og_a)
        self.crear_kpi(objetivo)

        response = self.client.patch(self.url(objetivo), {
            'plan_anual': self.pa_a_2027.id,
            'objetivo_general': self.og_a.id,
            'texto_objetivo': 'Texto corregido',
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        objetivo.refresh_from_db()
        self.assertEqual(objetivo.texto_objetivo, 'Texto corregido')

    def test_campo_puede_cambiar_relaciones(self):
        con_kpi = self.crear_objetivo_especifico(self.pa_a_2027, self.og_a, 'Con KPI')
        sin_kpi = self.crear_objetivo_especifico(self.pa_a_2027, self.og_a, 'Sin KPI')
        self.crear_kpi(con_kpi)

        self.assertFalse(self.client.get(self.url(con_kpi)).data['puede_cambiar_relaciones'])
        self.assertTrue(self.client.get(self.url(sin_kpi)).data['puede_cambiar_relaciones'])

    def test_objetivo_implicito_no_es_editable_por_la_api(self):
        implicito = obtener_o_crear_objetivo_especifico_directo(self.pa_a_2027, self.og_a, self.usuario)

        response = self.client.patch(self.url(implicito), {'objetivo_general': self.og_a2.id})

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        implicito.refresh_from_db()
        self.assertEqual(implicito.objetivo_general_id, self.og_a.id)

    def test_ejecutor_operativo_no_puede_trasladar(self):
        objetivo = self.crear_objetivo_especifico(self.pa_a_2027, self.og_a)
        ejecutor = crear_usuario('ejecutor_oe_etapa1', 'Ejecutor operativo')
        self.client.force_authenticate(user=ejecutor)

        response = self.client.patch(self.url(objetivo), {'objetivo_general': self.og_a2.id})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class PlanAnualTrasladoTests(IntegridadJerarquiaBase):
    """M9 (parte de integridad): Plan anual en Borrador con dependencias."""

    def url(self, plan_anual):
        return f'/api/planes-anuales/{plan_anual.id}/'

    def test_borrador_sin_dependencias_puede_cambiar_plan_estrategico(self):
        response = self.client.patch(self.url(self.pa_a_2028), {'plan_estrategico': self.plan_b.id, 'anio': 2030})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.pa_a_2028.refresh_from_db()
        self.assertEqual(self.pa_a_2028.plan_estrategico_id, self.plan_b.id)

    def test_borrador_con_ponderacion_no_puede_cambiar_plan_estrategico(self):
        PonderacionAnualObjetivoGeneral.objects.create(
            objetivo_general=self.og_a, plan_anual=self.pa_a_2028,
            porcentaje=Decimal('25'), creado_por=self.usuario,
        )

        response = self.client.patch(self.url(self.pa_a_2028), {'plan_estrategico': self.plan_b.id, 'anio': 2030})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('plan_estrategico', response.data)
        self.pa_a_2028.refresh_from_db()
        self.assertEqual(self.pa_a_2028.plan_estrategico_id, self.plan_a.id)

    def test_campo_puede_cambiar_plan_estrategico(self):
        self.assertTrue(self.client.get(self.url(self.pa_a_2028)).data['puede_cambiar_plan_estrategico'])
        # En uso: bloqueado por la regla de Bloque 1, aunque no tenga dependencias.
        self.assertFalse(self.client.get(self.url(self.pa_a_2027)).data['puede_cambiar_plan_estrategico'])


class PonderacionAnualTrasladoTests(IntegridadJerarquiaBase):
    """Una ponderación existente solo corrige su porcentaje."""

    def setUp(self):
        super().setUp()
        self.ponderacion = PonderacionAnualObjetivoGeneral.objects.create(
            objetivo_general=self.og_a, plan_anual=self.pa_a_2027,
            porcentaje=Decimal('30'), creado_por=self.usuario,
        )

    def url(self):
        return f'/api/ponderaciones-anuales/{self.ponderacion.id}/'

    def test_corregir_porcentaje_reenviando_las_mismas_relaciones_funciona(self):
        response = self.client.patch(self.url(), {
            'objetivo_general': self.og_a.id,
            'plan_anual': self.pa_a_2027.id,
            'porcentaje': '45.00',
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.ponderacion.refresh_from_db()
        self.assertEqual(self.ponderacion.porcentaje, Decimal('45.00'))

    def test_no_puede_trasladarse_a_otro_plan_anual(self):
        response = self.client.patch(self.url(), {'plan_anual': self.pa_a_2028.id})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.ponderacion.refresh_from_db()
        self.assertEqual(self.ponderacion.plan_anual_id, self.pa_a_2027.id)

    def test_no_puede_trasladarse_a_otro_objetivo_general(self):
        response = self.client.patch(self.url(), {'objetivo_general': self.og_a2.id})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.ponderacion.refresh_from_db()
        self.assertEqual(self.ponderacion.objetivo_general_id, self.og_a.id)

    def test_delete_rechazado(self):
        response = self.client.delete(self.url())

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertTrue(PonderacionAnualObjetivoGeneral.objects.filter(id=self.ponderacion.id).exists())


class CompletarVigenciaPlanAnualTests(IntegridadJerarquiaBase):
    """M9 (autorizado el 20/10/2026): completado único de las fechas de un
    Plan anual antiguo En uso con ambas fechas vacías."""

    def setUp(self):
        super().setUp()

        for nombre, color in [('Incumplido', 'rojo'), ('En riesgo', 'amarillo'), ('Favorable', 'verde')]:
            EstadoCumplimiento.objects.get_or_create(nombre=nombre, defaults={'color': color, 'estado': True})

    def url(self, plan_anual):
        return f'/api/planes-anuales/{plan_anual.id}/completar-vigencia/'

    def completar(self, plan_anual, fecha_inicio='2027-01-01', fecha_fin='2027-12-31'):
        payload = {}

        if fecha_inicio is not None:
            payload['fecha_inicio'] = fecha_inicio

        if fecha_fin is not None:
            payload['fecha_fin'] = fecha_fin

        return self.client.post(self.url(plan_anual), payload)

    def crear_medicion(self, kpi, mes):
        crear_rangos_provisionales(kpi)
        periodo = obtener_o_crear_periodo(kpi, date(2027, mes, 1))
        meta = obtener_o_crear_meta_vigente(kpi)

        return Medicion.objects.create(
            indicador=kpi,
            meta=meta,
            periodo=periodo,
            estado_cumplimiento=obtener_estado_para_medicion(kpi, meta, Decimal('80')),
            registrado_por=self.usuario,
            fecha_medicion=periodo.fecha_fin,
            valor_resultado=Decimal('80'),
        )

    def assertSinFechas(self, plan_anual):
        plan_anual.refresh_from_db()
        self.assertIsNone(plan_anual.fecha_inicio)
        self.assertIsNone(plan_anual.fecha_fin)

    # --- Casos válidos ---------------------------------------------------

    def test_completa_las_fechas_y_registra_bitacora(self):
        response = self.completar(self.pa_a_2027)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.pa_a_2027.refresh_from_db()
        self.assertEqual(self.pa_a_2027.fecha_inicio, date(2027, 1, 1))
        self.assertEqual(self.pa_a_2027.fecha_fin, date(2027, 12, 31))
        self.assertEqual(self.pa_a_2027.estado, PlanAnual.ESTADO_EN_USO)
        self.assertFalse(response.data['puede_completar_vigencia'])

        registro = Bitacora.objects.filter(modulo='Planes anuales', usuario=self.usuario).latest('fecha_hora')
        self.assertIn('Completó la vigencia', registro.descripcion)
        self.assertIn('01/01/2027', registro.descripcion)
        self.assertIn('31/12/2027', registro.descripcion)

    def test_acepta_vigencia_que_incluye_las_mediciones_existentes(self):
        kpi = self.crear_kpi(self.crear_objetivo_especifico(self.pa_a_2027, self.og_a))
        self.crear_medicion(kpi, 3)
        self.crear_medicion(kpi, 4)

        response = self.completar(self.pa_a_2027, '2027-03-15', '2027-12-31')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_despues_de_guardarlas_quedan_bloqueadas(self):
        self.assertEqual(self.completar(self.pa_a_2027).status_code, status.HTTP_200_OK)

        segundo_intento = self.completar(self.pa_a_2027, '2027-02-01', '2027-11-30')
        edicion_normal = self.client.patch(
            f'/api/planes-anuales/{self.pa_a_2027.id}/', {'fecha_inicio': '2027-02-01'},
        )

        self.assertEqual(segundo_intento.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(edicion_normal.status_code, status.HTTP_400_BAD_REQUEST)
        self.pa_a_2027.refresh_from_db()
        self.assertEqual(self.pa_a_2027.fecha_inicio, date(2027, 1, 1))
        self.assertEqual(self.pa_a_2027.fecha_fin, date(2027, 12, 31))

    def test_no_crea_mediciones_ni_cierres_automaticos(self):
        kpi = self.crear_kpi(self.crear_objetivo_especifico(self.pa_a_2027, self.og_a))
        self.crear_medicion(kpi, 1)
        mediciones = list(Medicion.objects.values_list('id', 'valor_resultado', 'periodo_id'))
        alertas = Alerta.objects.count()

        self.assertEqual(self.completar(self.pa_a_2027).status_code, status.HTTP_200_OK)

        self.assertEqual(list(Medicion.objects.values_list('id', 'valor_resultado', 'periodo_id')), mediciones)
        self.assertFalse(Medicion.objects.filter(cierre_automatico=True).exists())
        self.assertEqual(Alerta.objects.count(), alertas)

    def test_campo_puede_completar_vigencia(self):
        def valor(plan_anual):
            return self.client.get(f'/api/planes-anuales/{plan_anual.id}/').data['puede_completar_vigencia']

        self.assertTrue(valor(self.pa_a_2027))      # En uso sin fechas
        self.assertFalse(valor(self.pa_a_2028))     # Borrador
        self.assertFalse(valor(self.pa_b_2028))     # Cerrado

    # --- Casos inválidos -------------------------------------------------

    def test_exige_ambas_fechas_juntas(self):
        solo_inicio = self.completar(self.pa_a_2027, fecha_fin=None)
        solo_fin = self.completar(self.pa_a_2027, fecha_inicio=None)

        self.assertEqual(solo_inicio.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('fecha_fin', solo_inicio.data)
        self.assertEqual(solo_fin.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('fecha_inicio', solo_fin.data)
        self.assertSinFechas(self.pa_a_2027)

    def test_rechaza_fecha_invalida(self):
        response = self.completar(self.pa_a_2027, 'no-es-fecha', '2027-12-31')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertSinFechas(self.pa_a_2027)

    def test_rechaza_fin_anterior_al_inicio(self):
        response = self.completar(self.pa_a_2027, '2027-06-01', '2027-05-31')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('fecha_fin', response.data)
        self.assertSinFechas(self.pa_a_2027)

    def test_rechaza_fechas_fuera_del_anio(self):
        response = self.completar(self.pa_a_2027, '2027-01-01', '2028-01-31')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertSinFechas(self.pa_a_2027)

    def test_rechaza_fechas_fuera_de_la_vigencia_del_plan_estrategico(self):
        plan = PlanEstrategico.objects.create(
            titulo='Plan desde marzo', fecha_inicio=date(2027, 3, 1), fecha_fin=date(2030, 12, 31),
            estado=PlanEstrategico.ESTADO_EN_USO, creado_por=self.usuario,
        )
        plan_anual = self.crear_plan_anual(plan, 2027, PlanAnual.ESTADO_EN_USO)

        response = self.completar(plan_anual, '2027-01-01', '2027-12-31')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('fecha_inicio', response.data)
        self.assertSinFechas(plan_anual)

    def test_rechaza_vigencia_que_excluye_mediciones_existentes(self):
        kpi = self.crear_kpi(self.crear_objetivo_especifico(self.pa_a_2027, self.og_a))
        self.crear_medicion(kpi, 1)
        self.crear_medicion(kpi, 12)

        inicio_tardio = self.completar(self.pa_a_2027, '2027-02-01', '2027-12-31')
        fin_temprano = self.completar(self.pa_a_2027, '2027-01-01', '2027-11-30')

        self.assertEqual(inicio_tardio.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(fin_temprano.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertSinFechas(self.pa_a_2027)

    def test_cuenta_mediciones_de_kpi_directo(self):
        implicito = obtener_o_crear_objetivo_especifico_directo(self.pa_a_2027, self.og_a, self.usuario)
        self.crear_medicion(self.crear_kpi(implicito), 1)

        response = self.completar(self.pa_a_2027, '2027-02-01', '2027-12-31')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertSinFechas(self.pa_a_2027)

    def test_rechaza_plan_anual_que_ya_tiene_fechas(self):
        PlanAnual.objects.filter(id=self.pa_a_2027.id).update(fecha_inicio=date(2027, 1, 1))

        response = self.completar(self.pa_a_2027)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.pa_a_2027.refresh_from_db()
        self.assertIsNone(self.pa_a_2027.fecha_fin)

    def test_rechaza_plan_anual_borrador(self):
        response = self.completar(self.pa_a_2028, '2028-01-01', '2028-12-31')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertSinFechas(self.pa_a_2028)

    def test_rechaza_plan_anual_cerrado(self):
        response = self.completar(self.pa_b_2028, '2028-01-01', '2028-12-31')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertSinFechas(self.pa_b_2028)

    def test_rechaza_plan_anual_en_uso_de_plan_estrategico_cerrado(self):
        plan_anual = self.crear_plan_anual(self.plan_cerrado, 2027, PlanAnual.ESTADO_EN_USO)

        response = self.completar(plan_anual)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertSinFechas(plan_anual)

    def test_solo_administrador_de_planificacion(self):
        for username, rol in [
            ('ejecutor_vigencia', 'Ejecutor operativo'),
            ('consulta_vigencia', 'Usuario de consulta'),
            ('sistema_vigencia', 'Administrador del sistema'),
        ]:
            self.client.force_authenticate(user=crear_usuario(username, rol))

            response = self.completar(self.pa_a_2027)

            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, rol)

        self.assertSinFechas(self.pa_a_2027)
