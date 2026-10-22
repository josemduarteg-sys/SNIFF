"""Etapa 3 de correcciones post-auditoría (20/10/2026): C1 (cierre
automático no ejecutado), C2 (cierres retroactivos de KPI incorporados a
mitad de año) y C3 (omisiones "Sin registro" en lugar de 0.00).

Las pruebas con prefijo `test_actual_` DOCUMENTAN el comportamiento vigente
que depende de una decisión funcional pendiente (C2). No afirman que ese
comportamiento sea el correcto: anclan lo que el sistema hace hoy para que
el cambio, cuando se decida, sea deliberado y visible.

C3 ya está implementado (ajuste funcional adoptado durante la revisión del
sistema, que sustituye el criterio anterior de cerrar toda omisión en
0.00): ver OmisionSinRegistroTests."""

from datetime import date
from decimal import Decimal
from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.estrategia.models import ObjetivoEspecifico, ObjetivoGeneral, PlanAnual, PlanEstrategico
from apps.usuarios.models import Rol, Usuario

from .models import (
    Alerta,
    ConfiguracionMediciones,
    EstadoCumplimiento,
    Frecuencia,
    IndicadorKPI,
    Medicion,
    PeriodoMedicion,
    RangoKPI,
)
from .services import (
    TIPO_ALERTA_PERIODO_SIN_REGISTRO,
    TIPO_ALERTA_PERIODO_VENCIDO,
    calcular_promedio_acumulado_kpi,
    cerrar_mediciones_vencidas,
    contar_mediciones_kpi,
    contar_omisiones_kpi,
    generar_alertas_periodos_vencidos,
    obtener_estado_por_cumplimiento,
    recalcular_mediciones_pendientes,
    obtener_estado_acumulado_kpi,
    obtener_estado_para_medicion,
    obtener_info_siguiente_periodo,
    obtener_o_crear_meta_vigente,
    obtener_o_crear_periodo,
)
from .rangos_de_prueba import configurar_rangos_70_85


def crear_usuario(username, rol_nombre):
    rol, _ = Rol.objects.get_or_create(nombre=rol_nombre, defaults={'descripcion': 'Rol de prueba', 'estado': True})
    usuario = Usuario.objects.create_user(username=username, password='clave-prueba-123')
    usuario.rol = rol
    usuario.correo = f'{username}@sniff.test'
    usuario.save()
    return usuario


class CierresBase(APITestCase):
    def setUp(self):
        self.admin = crear_usuario('admin_etapa3', 'Administrador de planificación')
        self.ejecutor = crear_usuario('ejecutor_etapa3', 'Ejecutor operativo')

        for nombre, color in [('Incumplido', 'rojo'), ('En riesgo', 'amarillo'), ('Favorable', 'verde')]:
            EstadoCumplimiento.objects.get_or_create(nombre=nombre, defaults={'color': color, 'estado': True})

        self.mensual = Frecuencia.objects.create(nombre='Mensual', estado=True)
        self.trimestral = Frecuencia.objects.create(nombre='Trimestral', estado=True)

        plan = PlanEstrategico.objects.create(
            titulo='Plan etapa 3', fecha_inicio=date(2027, 1, 1), fecha_fin=date(2030, 12, 31),
            estado=PlanEstrategico.ESTADO_EN_USO, creado_por=self.admin,
        )
        objetivo_general = ObjetivoGeneral.objects.create(
            plan_estrategico=plan, texto_objetivo='Objetivo general etapa 3', creado_por=self.admin,
        )
        self.plan_anual = PlanAnual.objects.create(
            plan_estrategico=plan, anio=2027, estado=PlanAnual.ESTADO_EN_USO,
            fecha_inicio=date(2027, 1, 1), fecha_fin=date(2027, 12, 31), creado_por=self.admin,
        )
        self.objetivo_especifico = ObjetivoEspecifico.objects.create(
            plan_anual=self.plan_anual, objetivo_general=objetivo_general,
            texto_objetivo='Objetivo específico etapa 3', creado_por=self.admin,
        )

    def crear_kpi(self, nombre, frecuencia=None, unidad='%', creado=None, autorizado=None):
        kpi = IndicadorKPI.objects.create(
            objetivo_especifico=self.objetivo_especifico,
            frecuencia=frecuencia or self.mensual,
            nombre=nombre,
            formula_medicion='Resultado obtenido',
            unidad_medida=unidad,
            valor_meta=Decimal('85'),
            estado='autorizado',
            creado_por=self.admin,
            fecha_autorizacion=autorizado,
            autorizado_por=self.admin if autorizado else None,
        )
        configurar_rangos_70_85(kpi)

        if creado:
            IndicadorKPI.objects.filter(pk=kpi.pk).update(fecha_creacion=creado)
            kpi.refresh_from_db()

        return kpi

    def crear_kpi_inverso(self, nombre='Días de atraso'):
        """KPI donde menos es mejor (ej. días): rangos invertidos respecto a
        la plantilla — igual que el KPI 10 de la base de desarrollo."""
        kpi = self.crear_kpi(nombre, unidad='días')
        estados = {e.nombre: e for e in EstadoCumplimiento.objects.all()}
        configuracion = {
            'Favorable': (Decimal('0'), Decimal('3')),
            'En riesgo': (Decimal('3'), Decimal('6')),
            'Incumplido': (Decimal('6'), None),
        }

        for nombre_estado, (minimo, maximo) in configuracion.items():
            RangoKPI.objects.filter(indicador=kpi, estado_cumplimiento=estados[nombre_estado]).update(
                valor_minimo=minimo, valor_maximo=maximo,
            )

        return kpi

    def registrar_manual(self, kpi, mes, valor, anio=2027):
        periodo = obtener_o_crear_periodo(kpi, date(anio, mes, 1))
        meta = obtener_o_crear_meta_vigente(kpi)

        return Medicion.objects.create(
            indicador=kpi, meta=meta, periodo=periodo,
            estado_cumplimiento=obtener_estado_para_medicion(kpi, meta, Decimal(valor)),
            registrado_por=self.ejecutor, fecha_medicion=periodo.fecha_fin,
            valor_resultado=Decimal(valor),
        )

    def registrar_por_api(self, kpi, valor, fecha):
        self.client.force_authenticate(user=self.ejecutor)

        with mock.patch('apps.indicadores.services.hoy', return_value=fecha):
            return self.client.post('/api/mediciones/', {'indicador': kpi.id, 'valor_resultado': valor})

    def periodos_cerrados(self, kpi):
        return [
            m.periodo.fecha_inicio.month
            for m in Medicion.objects.filter(indicador=kpi, cierre_automatico=True).order_by('periodo__fecha_inicio')
        ]


# ------------------------------------------------------------------- C1

class BloqueoYRecuperacionTests(CierresBase):
    def test_periodo_vencido_sin_cierre_bloquea_el_registro(self):
        kpi = self.crear_kpi('KPI bloqueado')

        # Enero 2027 cierra el 31/01; con plazo de 5 días, vence el 05/02.
        info = obtener_info_siguiente_periodo(kpi, fecha_referencia=date(2027, 2, 6))

        self.assertFalse(info['disponible'])
        self.assertIn('pendiente de cierre automático', info['motivo'])
        self.assertEqual(self.registrar_por_api(kpi, '90', date(2027, 2, 6)).status_code, status.HTTP_400_BAD_REQUEST)

    def test_el_bloqueo_tambien_impide_registrar_periodos_posteriores_ya_abiertos(self):
        kpi = self.crear_kpi('KPI bloqueo encadenado')

        # 01/03: febrero ya cerró y está en su plazo, pero enero sigue sin
        # cerrarse; como el registro es secuencial, febrero tampoco se puede.
        response = self.registrar_por_api(kpi, '90', date(2027, 3, 1))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Medicion.objects.filter(indicador=kpi).exists())

    def test_recupera_varios_periodos_pendientes_en_orden_y_desbloquea(self):
        kpi = self.crear_kpi('KPI recuperación')

        # El proceso no corrió durante meses; al ejecutarse el 03/06 cierra
        # enero..abril (vencidos) y deja mayo, que está en su plazo (05/06).
        resultado = cerrar_mediciones_vencidas(fecha_referencia=date(2027, 6, 3))

        self.assertEqual(resultado['cierres_creados'], 4)
        self.assertEqual(self.periodos_cerrados(kpi), [1, 2, 3, 4])

        info = obtener_info_siguiente_periodo(kpi, fecha_referencia=date(2027, 6, 3))
        self.assertTrue(info['disponible'])
        self.assertEqual(info['periodo_nombre'], 'mayo 2027')
        self.assertEqual(self.registrar_por_api(kpi, '90', date(2027, 6, 3)).status_code, status.HTTP_201_CREATED)

    def test_ejecucion_repetida_no_duplica(self):
        kpi = self.crear_kpi('KPI idempotente')

        primero = cerrar_mediciones_vencidas(fecha_referencia=date(2027, 4, 10))
        segundo = cerrar_mediciones_vencidas(fecha_referencia=date(2027, 4, 10))
        tercero = cerrar_mediciones_vencidas(fecha_referencia=date(2027, 4, 11))

        self.assertEqual(primero['cierres_creados'], 3)
        self.assertEqual(segundo['cierres_creados'], 0)
        self.assertEqual(tercero['cierres_creados'], 0)
        self.assertEqual(Medicion.objects.filter(indicador=kpi).count(), 3)
        self.assertEqual(primero['errores'], [])

    def test_respeta_el_plazo_configurado(self):
        configuracion = ConfiguracionMediciones.obtener()
        configuracion.dias_plazo_registro = 10
        configuracion.save()
        kpi = self.crear_kpi('KPI plazo 10')

        # Enero cierra el 31/01; con 10 días el plazo vence el 10/02.
        self.assertEqual(cerrar_mediciones_vencidas(fecha_referencia=date(2027, 2, 10))['cierres_creados'], 0)
        self.assertTrue(obtener_info_siguiente_periodo(kpi, fecha_referencia=date(2027, 2, 10))['disponible'])
        self.assertEqual(cerrar_mediciones_vencidas(fecha_referencia=date(2027, 2, 11))['cierres_creados'], 1)

    def test_conserva_las_mediciones_historicas(self):
        kpi = self.crear_kpi('KPI con historia')
        enero = self.registrar_manual(kpi, 1, '92')
        febrero = self.registrar_manual(kpi, 2, '71')
        antes = list(Medicion.objects.filter(indicador=kpi).values_list('id', 'valor_resultado', 'estado_cumplimiento_id'))

        cerrar_mediciones_vencidas(fecha_referencia=date(2027, 5, 10))

        despues = list(
            Medicion.objects.filter(id__in=[enero.id, febrero.id]).values_list('id', 'valor_resultado', 'estado_cumplimiento_id')
        )
        self.assertEqual(despues, antes)
        # Al 10/05 vencieron marzo (05/04) y abril (05/05); mayo sigue abierto.
        self.assertEqual(self.periodos_cerrados(kpi), [3, 4])

    def test_no_toca_kpi_de_plan_anual_cerrado(self):
        kpi = self.crear_kpi('KPI plan cerrado')
        self.plan_anual.estado = PlanAnual.ESTADO_CERRADO
        self.plan_anual.save(update_fields=['estado'])

        resultado = cerrar_mediciones_vencidas(fecha_referencia=date(2027, 6, 10))

        self.assertEqual(resultado['cierres_creados'], 0)
        self.assertFalse(Medicion.objects.filter(indicador=kpi).exists())


class ComandoSimulacionTests(CierresBase):
    def test_simular_no_guarda_nada(self):
        kpi = self.crear_kpi('KPI simulado')
        periodos = PeriodoMedicion.objects.count()
        salida = StringIO()

        with mock.patch('apps.indicadores.services.hoy', return_value=date(2027, 4, 10)):
            call_command('cerrar_mediciones_vencidas', '--simular', stdout=salida)

        self.assertIn('SIMULACIÓN', salida.getvalue())
        self.assertIn('Cierres automáticos creados: 3', salida.getvalue())
        self.assertFalse(Medicion.objects.filter(indicador=kpi).exists())
        self.assertEqual(PeriodoMedicion.objects.count(), periodos)
        self.assertFalse(Alerta.objects.filter(indicador=kpi).exists())

    def test_sin_simular_guarda_los_cierres(self):
        kpi = self.crear_kpi('KPI real de prueba')

        with mock.patch('apps.indicadores.services.hoy', return_value=date(2027, 4, 10)):
            call_command('cerrar_mediciones_vencidas', stdout=StringIO())

        self.assertEqual(self.periodos_cerrados(kpi), [1, 2, 3])


# ------------------------------------------------------------------- C2

class IncorporacionDelKpiTests(CierresBase):
    def test_kpi_creado_al_inicio_del_anio_empieza_en_enero(self):
        kpi = self.crear_kpi('KPI de enero', creado=timezone.make_aware(timezone.datetime(2027, 1, 2)))

        info = obtener_info_siguiente_periodo(kpi, fecha_referencia=date(2027, 1, 31))

        self.assertTrue(info['disponible'])
        self.assertEqual(info['periodo_nombre'], 'enero 2027')

    def test_kpi_creado_a_mitad_de_anio_no_recibe_omisiones_anteriores(self):
        """C2 resuelto: un KPI incorporado en julio se mide desde julio
        (respuesta de Hernán). Antes de C2 este mismo caso recibía
        omisiones de enero a mayo."""
        kpi = self.crear_kpi(
            'KPI de julio',
            creado=timezone.make_aware(timezone.datetime(2027, 7, 1)),
            autorizado=timezone.make_aware(timezone.datetime(2027, 7, 1)),
        )

        resultado = cerrar_mediciones_vencidas(fecha_referencia=date(2027, 7, 1))

        self.assertEqual(resultado['cierres_creados'], 0)
        self.assertEqual(self.periodos_cerrados(kpi), [])
        self.assertEqual(contar_omisiones_kpi(kpi), 0)
        self.assertEqual(obtener_info_siguiente_periodo(kpi, fecha_referencia=date(2027, 7, 1))['periodo_nombre'], 'julio 2027')

    def test_la_fecha_de_autorizacion_define_el_primer_periodo(self):
        """C2 resuelto: creado en marzo y autorizado el 15/07 — el primer
        periodo exigible es julio (parcial, desde el 15/07)."""
        kpi = self.crear_kpi(
            'KPI autorizado tarde',
            creado=timezone.make_aware(timezone.datetime(2027, 3, 1)),
            autorizado=timezone.make_aware(timezone.datetime(2027, 7, 15)),
        )

        info = obtener_info_siguiente_periodo(kpi, fecha_referencia=date(2027, 7, 15))

        self.assertEqual(info['periodo_nombre'], 'julio 2027')
        self.assertEqual(info['inicio_seguimiento'], date(2027, 7, 15))
        self.assertTrue(info['periodo_parcial'])
        self.assertFalse(info['disponible'])

    def test_un_kpi_autorizado_puede_no_tener_fecha_de_autorizacion(self):
        """Dato para C2: el modelo admite fecha_autorizacion NULL en un KPI
        autorizado (en la base de desarrollo, los KPI 9 y 10). Una regla
        basada en esa fecha necesita un respaldo explícito."""
        kpi = self.crear_kpi('KPI sin fecha de autorización')

        self.assertEqual(kpi.estado, 'autorizado')
        self.assertIsNone(kpi.fecha_autorizacion)

    def test_periodos_trimestrales_se_alinean_al_inicio_de_la_vigencia(self):
        """Dato para C2: los periodos forman una grilla desde el mes de
        inicio de la vigencia (ene-mar, abr-jun...). Una regla de
        incorporación debe decidir qué periodo de esa grilla es el primero,
        no crear una grilla nueva desde la fecha del KPI."""
        kpi = self.crear_kpi('KPI trimestral', frecuencia=self.trimestral)

        resultado = cerrar_mediciones_vencidas(fecha_referencia=date(2027, 10, 10))

        inicios = [
            m.periodo.fecha_inicio for m in Medicion.objects.filter(indicador=kpi).order_by('periodo__fecha_inicio')
        ]
        self.assertEqual(resultado['cierres_creados'], 3)
        self.assertEqual(inicios, [date(2027, 1, 1), date(2027, 4, 1), date(2027, 7, 1)])


# ------------------------------------------------------------------- C3

class OmisionSinRegistroTests(CierresBase):
    """C3 implementado: una omisión es "Sin registro" (valor_resultado NULL),
    no un resultado. Sustituye el criterio anterior de cerrar en 0.00 (que
    en un KPI inverso quedaba Favorable). Ajuste funcional adoptado durante
    la revisión del sistema."""

    def serializar_kpi(self, kpi):
        self.client.force_authenticate(user=self.admin)
        return self.client.get(f'/api/indicadores-kpi/{kpi.id}/').data

    # --- Resultados reales en cero: sin cambios ---------------------------

    def test_cero_real_en_kpi_directo_se_clasifica_con_sus_rangos(self):
        kpi = self.crear_kpi('KPI directo cero real')

        response = self.registrar_por_api(kpi, '0', date(2027, 1, 31))

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        medicion = Medicion.objects.get(indicador=kpi)
        self.assertEqual(medicion.valor_resultado, Decimal('0'))
        self.assertFalse(medicion.sin_registro)
        self.assertEqual(medicion.estado_cumplimiento.nombre, 'Incumplido')
        self.assertEqual(calcular_promedio_acumulado_kpi(kpi), Decimal('0.00'))

    def test_cero_real_en_kpi_inverso_sigue_siendo_favorable(self):
        kpi = self.crear_kpi_inverso()

        self.assertEqual(self.registrar_por_api(kpi, '0', date(2027, 1, 31)).status_code, status.HTTP_201_CREATED)

        medicion = Medicion.objects.get(indicador=kpi)
        self.assertEqual(medicion.estado_cumplimiento.nombre, 'Favorable')
        self.assertEqual(calcular_promedio_acumulado_kpi(kpi), Decimal('0.00'))
        self.assertEqual(contar_mediciones_kpi(kpi), 1)
        self.assertEqual(contar_omisiones_kpi(kpi), 0)

    # --- Omisiones ----------------------------------------------------------

    def assertEsOmision(self, medicion, fecha_cierre):
        self.assertIsNone(medicion.valor_resultado)
        self.assertTrue(medicion.sin_registro)
        self.assertTrue(medicion.cierre_automatico)
        self.assertIsNone(medicion.registrado_por)
        self.assertEqual(medicion.estado_cumplimiento.nombre, 'Sin registro')
        self.assertEqual(medicion.fecha_medicion, fecha_cierre)
        self.assertIsNone(medicion.calcular_cumplimiento())

    def test_omision_en_kpi_directo_queda_sin_registro(self):
        kpi = self.crear_kpi('KPI directo omitido')

        cerrar_mediciones_vencidas(fecha_referencia=date(2027, 2, 6))

        self.assertEsOmision(Medicion.objects.get(indicador=kpi), date(2027, 1, 31))

    def test_omision_en_kpi_inverso_ya_no_es_favorable(self):
        kpi = self.crear_kpi_inverso()

        cerrar_mediciones_vencidas(fecha_referencia=date(2027, 2, 6))

        omision = Medicion.objects.get(indicador=kpi)
        self.assertEsOmision(omision, date(2027, 1, 31))
        self.assertNotEqual(omision.estado_cumplimiento.nombre, 'Favorable')

    def test_promedio_excluye_omisiones_en_kpi_inverso(self):
        """Mismo caso que el KPI 10 de la base de desarrollo: 5, 4 y 6 días
        más 6 omisiones. Antes quedaba en 1.67 (Favorable); ahora el
        promedio sigue en 5.00 (En riesgo) y las 6 omisiones se cuentan."""
        kpi = self.crear_kpi_inverso()
        for mes, valor in ((1, '5'), (2, '4'), (3, '6')):
            self.registrar_manual(kpi, mes, valor)

        cerrar_mediciones_vencidas(fecha_referencia=date(2027, 10, 10))

        promedio = calcular_promedio_acumulado_kpi(kpi)
        self.assertEqual(promedio, Decimal('5.00'))
        self.assertEqual(obtener_estado_acumulado_kpi(kpi, promedio).nombre, 'En riesgo')
        self.assertEqual(contar_mediciones_kpi(kpi), 3)
        self.assertEqual(contar_omisiones_kpi(kpi), 6)

    def test_promedio_excluye_omisiones_en_kpi_directo(self):
        kpi = self.crear_kpi('KPI directo mixto')
        self.registrar_manual(kpi, 1, '90')
        self.registrar_manual(kpi, 2, '86')

        cerrar_mediciones_vencidas(fecha_referencia=date(2027, 6, 10))

        self.assertEqual(calcular_promedio_acumulado_kpi(kpi), Decimal('88.00'))
        self.assertEqual(contar_omisiones_kpi(kpi), 3)

    # --- Serializers: KPI sin datos, solo omisiones, mixto ------------------

    def test_kpi_sin_ninguna_medicion(self):
        data = self.serializar_kpi(self.crear_kpi('KPI vacío'))

        self.assertEqual(data['cantidad_mediciones'], 0)
        self.assertEqual(data['cantidad_omisiones'], 0)
        self.assertIsNone(data['promedio_acumulado'])
        self.assertIsNone(data['estado_acumulado_nombre'])

    def test_kpi_con_unicamente_omisiones(self):
        kpi = self.crear_kpi('KPI solo omisiones')
        cerrar_mediciones_vencidas(fecha_referencia=date(2027, 4, 10))

        data = self.serializar_kpi(kpi)

        self.assertEqual(data['cantidad_mediciones'], 0)
        self.assertEqual(data['cantidad_omisiones'], 3)
        self.assertIsNone(data['promedio_acumulado'])
        self.assertIsNone(data['estado_acumulado_nombre'])

    def test_kpi_favorable_con_omisiones_muestra_ambas_cosas(self):
        kpi = self.crear_kpi('KPI favorable con huecos')
        self.registrar_manual(kpi, 1, '95')
        cerrar_mediciones_vencidas(fecha_referencia=date(2027, 4, 10))

        data = self.serializar_kpi(kpi)

        self.assertEqual(Decimal(str(data['promedio_acumulado'])), Decimal('95.00'))
        self.assertEqual(data['estado_acumulado_nombre'], 'Favorable')
        self.assertEqual(data['cantidad_mediciones'], 1)
        self.assertEqual(data['cantidad_omisiones'], 2)

    def test_detalle_de_medicion_omitida(self):
        kpi = self.crear_kpi('KPI detalle omisión')
        self.registrar_manual(kpi, 1, '80')
        cerrar_mediciones_vencidas(fecha_referencia=date(2027, 3, 10))
        omision = Medicion.objects.get(indicador=kpi, cierre_automatico=True)

        self.client.force_authenticate(user=self.admin)
        data = self.client.get(f'/api/mediciones/{omision.id}/').data

        self.assertTrue(data['sin_registro'])
        self.assertIsNone(data['valor_resultado'])
        self.assertIsNone(data['porcentaje_cumplimiento'])
        self.assertEqual(data['estado_cumplimiento_nombre'], 'Sin registro')
        self.assertTrue(data['cierre_automatico'])
        self.assertIsNone(data['registrado_por_username'])
        self.assertEqual(data['fecha_medicion'], '2027-02-28')
        self.assertEqual(data['periodo_nombre'], 'Febrero 2027')
        # El acumulado hasta ese periodo es el de los resultados reales.
        self.assertEqual(Decimal(str(data['promedio_acumulado_hasta_medicion'])), Decimal('80.00'))
        self.assertFalse(data['puede_modificarse'])

    def test_detalle_de_medicion_real_sigue_igual(self):
        kpi = self.crear_kpi('KPI detalle real')
        medicion = self.registrar_manual(kpi, 1, '42.5')

        self.client.force_authenticate(user=self.admin)
        data = self.client.get(f'/api/mediciones/{medicion.id}/').data

        self.assertFalse(data['sin_registro'])
        self.assertEqual(Decimal(str(data['valor_resultado'])), Decimal('42.5'))
        self.assertEqual(Decimal(str(data['porcentaje_cumplimiento'])), Decimal('50.00'))

    # --- Integridad: una medición manual siempre tiene resultado -----------

    def test_rechaza_medicion_manual_sin_resultado_por_api(self):
        kpi = self.crear_kpi('KPI sin resultado')
        self.client.force_authenticate(user=self.ejecutor)

        with mock.patch('apps.indicadores.services.hoy', return_value=date(2027, 1, 31)):
            sin_campo = self.client.post('/api/mediciones/', {'indicador': kpi.id})
            vacio = self.client.post('/api/mediciones/', {'indicador': kpi.id, 'valor_resultado': ''})
            nulo = self.client.post('/api/mediciones/', {'indicador': kpi.id, 'valor_resultado': None}, format='json')

        for response in (sin_campo, vacio, nulo):
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn('valor_resultado', response.data)

        self.assertFalse(Medicion.objects.filter(indicador=kpi).exists())

    def test_rechaza_vaciar_el_resultado_de_una_medicion_manual(self):
        kpi = self.crear_kpi('KPI vaciar resultado')
        medicion = self.registrar_manual(kpi, 1, '70')
        self.client.force_authenticate(user=self.ejecutor)

        response = self.client.patch(f'/api/mediciones/{medicion.id}/', {'valor_resultado': None}, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        medicion.refresh_from_db()
        self.assertEqual(medicion.valor_resultado, Decimal('70'))

    def test_la_base_de_datos_impide_una_medicion_manual_sin_resultado(self):
        from django.db import IntegrityError, transaction

        kpi = self.crear_kpi('KPI restricción')
        periodo = obtener_o_crear_periodo(kpi, date(2027, 1, 1))

        with self.assertRaises(IntegrityError), transaction.atomic():
            Medicion.objects.create(
                indicador=kpi, meta=obtener_o_crear_meta_vigente(kpi), periodo=periodo,
                estado_cumplimiento=EstadoCumplimiento.objects.get(nombre='Favorable'),
                registrado_por=self.ejecutor, fecha_medicion=periodo.fecha_fin,
                valor_resultado=None, cierre_automatico=False,
            )

    # --- Clasificación y cálculos existentes --------------------------------

    def test_sin_registro_nunca_sale_de_la_clasificacion_por_rangos(self):
        kpi = self.crear_kpi_inverso()

        for valor in ('0', '2.5', '3', '5.99', '6', '1000'):
            self.assertNotEqual(obtener_estado_por_cumplimiento(kpi, Decimal(valor)).nombre, 'Sin registro')

    def test_sin_registro_no_puede_configurarse_como_rango(self):
        kpi = self.crear_kpi('KPI rango prohibido')
        sin_registro = EstadoCumplimiento.objects.get(nombre='Sin registro')
        self.client.force_authenticate(user=self.admin)

        response = self.client.post('/api/rangos-kpi/', {
            'indicador': kpi.id,
            'estado_cumplimiento': sin_registro.id,
            'valor_minimo': '0',
            'valor_maximo': '10',
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('estado_cumplimiento', response.data)
        self.assertFalse(RangoKPI.objects.filter(estado_cumplimiento=sin_registro).exists())

    def test_recalcular_pendientes_no_toca_omisiones(self):
        kpi = self.crear_kpi('KPI recalcular')
        cerrar_mediciones_vencidas(fecha_referencia=date(2027, 2, 6))

        resultado = recalcular_mediciones_pendientes()

        self.assertEqual(resultado['recalculadas'], 0)
        self.assertEqual(Medicion.objects.get(indicador=kpi).estado_cumplimiento.nombre, 'Sin registro')

    # --- Alertas ------------------------------------------------------------

    def test_cada_omision_deja_una_alerta_sin_registro(self):
        kpi = self.crear_kpi('KPI alertas sin registro')

        cerrar_mediciones_vencidas(fecha_referencia=date(2027, 4, 10))
        cerrar_mediciones_vencidas(fecha_referencia=date(2027, 4, 10))

        alertas = Alerta.objects.filter(indicador=kpi, tipo_alerta=TIPO_ALERTA_PERIODO_SIN_REGISTRO)
        self.assertEqual(alertas.count(), 3)
        self.assertEqual(
            sorted(a.medicion.periodo.fecha_inicio.month for a in alertas),
            [1, 2, 3],
        )
        self.assertTrue(all(a.estado_alerta == 'pendiente' for a in alertas))
        self.assertIn('enero 2027', alertas.get(medicion__periodo__fecha_inicio=date(2027, 1, 1)).mensaje)

    def test_la_alerta_de_periodo_vencido_se_conserva_como_historial(self):
        kpi = self.crear_kpi('KPI vencido a sin registro')

        # 02/02: enero cerró y está en plazo -> alerta de periodo vencido.
        generar_alertas_periodos_vencidos(fecha_referencia=date(2027, 2, 2))
        vencida = Alerta.objects.get(indicador=kpi, tipo_alerta=TIPO_ALERTA_PERIODO_VENCIDO)

        cerrar_mediciones_vencidas(fecha_referencia=date(2027, 2, 6))

        vencida.refresh_from_db()
        self.assertEqual(vencida.estado_alerta, 'descartada')
        self.assertEqual(vencida.tipo_alerta, TIPO_ALERTA_PERIODO_VENCIDO)
        self.assertTrue(
            Alerta.objects.filter(
                indicador=kpi, tipo_alerta=TIPO_ALERTA_PERIODO_SIN_REGISTRO, estado_alerta='pendiente',
            ).exists()
        )

    def test_omision_no_toca_la_alerta_de_cumplimiento_existente(self):
        kpi = self.crear_kpi('KPI con alerta de cumplimiento')
        self.registrar_por_api(kpi, '60', date(2027, 1, 31))
        cumplimiento = Alerta.objects.exclude(
            tipo_alerta__in=(TIPO_ALERTA_PERIODO_VENCIDO, TIPO_ALERTA_PERIODO_SIN_REGISTRO),
        ).get(indicador=kpi)
        antes = (cumplimiento.tipo_alerta, cumplimiento.mensaje, cumplimiento.estado_alerta, cumplimiento.medicion_id)

        cerrar_mediciones_vencidas(fecha_referencia=date(2027, 3, 10))

        cumplimiento.refresh_from_db()
        self.assertEqual(
            (cumplimiento.tipo_alerta, cumplimiento.mensaje, cumplimiento.estado_alerta, cumplimiento.medicion_id),
            antes,
        )

    def test_marcar_revisada_funciona_con_alertas_sin_registro(self):
        kpi = self.crear_kpi('KPI revisar sin registro')
        cerrar_mediciones_vencidas(fecha_referencia=date(2027, 2, 6))
        alerta = Alerta.objects.get(indicador=kpi, tipo_alerta=TIPO_ALERTA_PERIODO_SIN_REGISTRO)

        self.client.force_authenticate(user=self.admin)
        response = self.client.post(f'/api/alertas/{alerta.id}/marcar-revisada/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        alerta.refresh_from_db()
        self.assertEqual(alerta.estado_alerta, 'revisada')

    # --- Historial -----------------------------------------------------------

    def test_cierre_automatico_anterior_en_cero_se_conserva_sin_reinterpretar(self):
        """Un cierre automático guardado con 0.00 antes de este cambio (no
        existe ninguno en la base de desarrollo, pero podría existir en
        otra) se conserva tal cual y sigue contando como antes."""
        kpi = self.crear_kpi('KPI con cierre anterior')
        periodo = obtener_o_crear_periodo(kpi, date(2027, 1, 1))
        anterior = Medicion.objects.create(
            indicador=kpi, meta=obtener_o_crear_meta_vigente(kpi), periodo=periodo,
            estado_cumplimiento=EstadoCumplimiento.objects.get(nombre='Incumplido'),
            registrado_por=None, fecha_medicion=periodo.fecha_fin,
            valor_resultado=Decimal('0'), cierre_automatico=True,
        )
        self.registrar_manual(kpi, 2, '80')

        cerrar_mediciones_vencidas(fecha_referencia=date(2027, 4, 10))

        anterior.refresh_from_db()
        self.assertEqual(anterior.valor_resultado, Decimal('0'))
        self.assertEqual(anterior.estado_cumplimiento.nombre, 'Incumplido')
        self.assertEqual(calcular_promedio_acumulado_kpi(kpi), Decimal('40.00'))
        self.assertEqual(contar_omisiones_kpi(kpi), 1)  # solo marzo, la nueva

    def test_mediciones_reales_no_cambian_al_cerrar_omisiones(self):
        kpi = self.crear_kpi_inverso()
        reales = [self.registrar_manual(kpi, mes, valor) for mes, valor in ((1, '2'), (2, '7'))]
        antes = list(Medicion.objects.filter(id__in=[m.id for m in reales]).values())

        cerrar_mediciones_vencidas(fecha_referencia=date(2027, 6, 10))

        self.assertEqual(list(Medicion.objects.filter(id__in=[m.id for m in reales]).values()), antes)


# ------------------------------------------------------------ C1 (tarea)

class EjecutarTareasMedicionesTests(CierresBase):
    """Comando ejecutar_tareas_mediciones (preparación de C1, sin activar)."""

    def ejecutar(self, fecha, *argumentos):
        salida = StringIO()

        with mock.patch('apps.indicadores.services.hoy', return_value=fecha):
            call_command('ejecutar_tareas_mediciones', *argumentos, stdout=salida)

        return salida.getvalue()

    def test_simular_no_guarda_cierres_ni_alertas(self):
        kpi = self.crear_kpi('KPI simulación completa')
        periodos = PeriodoMedicion.objects.count()

        salida = self.ejecutar(date(2027, 4, 3), '--simular')

        self.assertIn('SIMULACIÓN', salida)
        self.assertIn('Cierres automáticos: 2', salida)
        self.assertIn('Alertas creadas: 1', salida)
        self.assertFalse(Medicion.objects.filter(indicador=kpi).exists())
        self.assertFalse(Alerta.objects.filter(indicador=kpi).exists())
        self.assertEqual(PeriodoMedicion.objects.count(), periodos)

    def test_ejecuta_cierre_y_luego_alertas_en_orden(self):
        kpi = self.crear_kpi('KPI tarea diaria')

        # 03/04: enero y febrero vencieron (05/02 y 05/03) -> se cierran;
        # marzo cerró el 31/03 y está en plazo -> solo recibe su alerta.
        salida = self.ejecutar(date(2027, 4, 3))

        self.assertEqual(self.periodos_cerrados(kpi), [1, 2])
        alertas = Alerta.objects.filter(indicador=kpi, tipo_alerta=TIPO_ALERTA_PERIODO_VENCIDO)
        self.assertEqual(alertas.count(), 1)
        self.assertIn('marzo 2027', alertas.get().mensaje)
        # Enero y febrero quedaron con su alerta "Periodo sin registro".
        self.assertEqual(
            Alerta.objects.filter(indicador=kpi, tipo_alerta=TIPO_ALERTA_PERIODO_SIN_REGISTRO).count(), 2,
        )
        self.assertIn('Cierres automáticos: 2', salida)

    def test_ejecucion_repetida_no_duplica_cierres_ni_alertas(self):
        kpi = self.crear_kpi('KPI tarea repetida')

        self.ejecutar(date(2027, 4, 3))
        salida = self.ejecutar(date(2027, 4, 3))

        self.assertIn('Cierres automáticos: 0', salida)
        self.assertIn('Alertas creadas: 0', salida)
        self.assertEqual(Medicion.objects.filter(indicador=kpi).count(), 2)
        self.assertEqual(Alerta.objects.filter(indicador=kpi, tipo_alerta=TIPO_ALERTA_PERIODO_VENCIDO).count(), 1)

    def test_errores_de_cierre_terminan_con_codigo_de_fallo(self):
        from django.core.management.base import CommandError

        resultado_con_error = {
            'kpi_revisados': 1, 'cierres_creados': 0, 'kpi_bloqueados': 0, 'detalle': [],
            'errores': [{'indicador_id': 1, 'indicador': 'KPI', 'periodo': 'enero 2027', 'error': 'falla'}],
        }

        with mock.patch(
            'apps.indicadores.management.commands.ejecutar_tareas_mediciones.cerrar_mediciones_vencidas',
            return_value=resultado_con_error,
        ):
            with self.assertRaises(CommandError):
                call_command('ejecutar_tareas_mediciones', stdout=StringIO())

    def test_si_otra_ejecucion_esta_en_curso_no_hace_nada(self):
        from contextlib import contextmanager

        from django.core.management.base import CommandError

        kpi = self.crear_kpi('KPI con bloqueo')

        @contextmanager
        def bloqueo_ocupado():
            yield False

        with mock.patch(
            'apps.indicadores.management.commands.ejecutar_tareas_mediciones.bloqueo_exclusivo',
            bloqueo_ocupado,
        ), mock.patch('apps.indicadores.services.hoy', return_value=date(2027, 4, 3)):
            with self.assertRaises(CommandError):
                call_command('ejecutar_tareas_mediciones', stdout=StringIO())

        self.assertFalse(Medicion.objects.filter(indicador=kpi).exists())
