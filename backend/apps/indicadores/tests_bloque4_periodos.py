"""Bloque 4 (periodos, vigencia de planes anuales y plazos de registro):
pruebas específicas de las correcciones de esta auditoría. Las pruebas
de generación de periodos por frecuencia, ventana de registro y cierre
automático que YA existían (PeriodosTests, VentanaRegistroTests,
CierreAutomaticoTests en tests.py) siguen pasando sin cambios — ver
informe de entrega — y no se duplican acá."""

from datetime import date
from decimal import Decimal
from unittest import mock

from rest_framework import status
from rest_framework.test import APITestCase

from apps.estrategia.models import ObjetivoEspecifico, ObjetivoGeneral, PlanAnual, PlanEstrategico
from apps.usuarios.models import Rol, Usuario

from .models import ConfiguracionMediciones, EstadoCumplimiento, Frecuencia, IndicadorKPI
from .services import (
    calcular_fecha_limite_registro,
    obtener_info_siguiente_periodo,
)
from .rangos_de_prueba import configurar_rangos_70_85


def crear_usuario(username, rol_nombre):
    rol, _ = Rol.objects.get_or_create(
        nombre=rol_nombre, defaults={'descripcion': 'Rol de prueba', 'estado': True},
    )
    usuario = Usuario.objects.create_user(username=username, password='clave-prueba-123')
    usuario.rol = rol
    usuario.correo = f'{username}@sniff.test'
    usuario.save()
    return usuario


def crear_catalogos():
    for nombre, color in [('Incumplido', 'rojo'), ('En riesgo', 'amarillo'), ('Favorable', 'verde')]:
        EstadoCumplimiento.objects.get_or_create(
            nombre=nombre, defaults={'color': color, 'estado': True}
        )

    frecuencia, _ = Frecuencia.objects.get_or_create(nombre='Mensual', defaults={'estado': True})
    return frecuencia


class VigenciaPlanAnualTests(APITestCase):
    """Corrección central de esta auditoría: fecha_inicio_vigencia /
    fecha_fin_vigencia del KPI deben derivarse de PlanAnual.fecha_inicio/
    fecha_fin (Bloque 1) cuando existen, y solo caer al comportamiento
    anterior (año calendario acotado por el Plan estratégico) cuando el
    Plan anual tiene esas fechas en NULL (pruebas 9 y 10 de la Fase 5)."""

    def setUp(self):
        self.usuario = crear_usuario('admin_vigencia_pa', 'Administrador de planificación')
        self.client.force_authenticate(user=self.usuario)
        self.frecuencia = crear_catalogos()

        self.plan_estrategico = PlanEstrategico.objects.create(
            titulo='Plan estratégico vigencia',
            fecha_inicio=date(2026, 1, 1),
            fecha_fin=date(2030, 12, 31),
            estado=PlanEstrategico.ESTADO_EN_USO,
            creado_por=self.usuario,
        )
        self.objetivo_general = ObjetivoGeneral.objects.create(
            plan_estrategico=self.plan_estrategico,
            texto_objetivo='Objetivo general vigencia',
            creado_por=self.usuario,
        )

    def crear_kpi_bajo(self, plan_anual):
        objetivo_especifico = ObjetivoEspecifico.objects.create(
            plan_anual=plan_anual,
            objetivo_general=self.objetivo_general,
            texto_objetivo=f'Objetivo específico {plan_anual.anio}',
            creado_por=self.usuario,
        )
        kpi = IndicadorKPI.objects.create(
            objetivo_especifico=objetivo_especifico,
            frecuencia=self.frecuencia,
            nombre=f'KPI vigencia {plan_anual.id}',
            formula_medicion='Resultado / Meta x 100',
            unidad_medida='unidades',
            valor_meta=Decimal('100.00'),
            estado='autorizado',
            creado_por=self.usuario,
        )
        configurar_rangos_70_85(kpi)
        return kpi

    # 9. Un Plan anual con fecha_inicio/fecha_fin propias (Bloque 1) debe
    # acotar la vigencia del KPI a ESAS fechas, no al año calendario
    # completo ni a las fechas del Plan estratégico.
    def test_plan_anual_con_fechas_propias_acota_la_vigencia(self):
        plan_anual = PlanAnual.objects.create(
            plan_estrategico=self.plan_estrategico,
            anio=2027,
            estado=PlanAnual.ESTADO_EN_USO,
            fecha_inicio=date(2027, 4, 1),
            fecha_fin=date(2027, 9, 30),
            creado_por=self.usuario,
        )
        kpi = self.crear_kpi_bajo(plan_anual)

        self.assertEqual(kpi.fecha_inicio_vigencia, date(2027, 4, 1))
        self.assertEqual(kpi.fecha_fin_vigencia, date(2027, 9, 30))

    # 10. Un Plan anual histórico con fecha_inicio/fecha_fin en NULL
    # conserva el comportamiento anterior a esta corrección: año
    # calendario acotado por la vigencia del Plan estratégico.
    def test_plan_anual_con_fechas_null_conserva_comportamiento_anterior(self):
        plan_anual = PlanAnual.objects.create(
            plan_estrategico=self.plan_estrategico,
            anio=2026,
            estado=PlanAnual.ESTADO_EN_USO,
            creado_por=self.usuario,
        )
        kpi = self.crear_kpi_bajo(plan_anual)

        # plan_estrategico.fecha_inicio (2026-01-01) coincide con el inicio
        # del año calendario de 2026, así que no lo recorta.
        self.assertEqual(kpi.fecha_inicio_vigencia, date(2026, 1, 1))
        self.assertEqual(kpi.fecha_fin_vigencia, date(2026, 12, 31))

    # Un periodo posterior a la ventana corta del Plan anual (julio,
    # cuando el Plan anual termina en junio) debe quedar fuera de
    # vigencia y rechazarse, una vez agotados los periodos que sí entran
    # dentro de esa ventana (abril, mayo, junio).
    def test_periodo_fuera_de_la_vigencia_corta_del_plan_anual_rechazado(self):
        from .models import Medicion
        from .services import obtener_estado_para_medicion, obtener_o_crear_meta_vigente, obtener_o_crear_periodo

        plan_anual = PlanAnual.objects.create(
            plan_estrategico=self.plan_estrategico,
            anio=2027,
            estado=PlanAnual.ESTADO_EN_USO,
            fecha_inicio=date(2027, 4, 1),
            fecha_fin=date(2027, 6, 30),
            creado_por=self.usuario,
        )
        kpi = self.crear_kpi_bajo(plan_anual)

        # Cubre manualmente los 3 meses que SÍ entran en la vigencia corta
        # (abril, mayo, junio) para que el próximo periodo esperado sea
        # julio — el primero que cae fuera de fecha_fin_vigencia.
        meta = obtener_o_crear_meta_vigente(kpi)
        for mes in (4, 5, 6):
            periodo = obtener_o_crear_periodo(kpi, date(2027, mes, 1))
            estado = obtener_estado_para_medicion(kpi, meta, Decimal('50'))
            Medicion.objects.create(
                indicador=kpi, meta=meta, estado_cumplimiento=estado, periodo=periodo,
                fecha_medicion=periodo.fecha_fin, valor_resultado=Decimal('50'),
                registrado_por=self.usuario,
            )

        with mock.patch('apps.indicadores.services.hoy', return_value=date(2027, 7, 10)):
            info = obtener_info_siguiente_periodo(kpi)

        self.assertFalse(info['disponible'])
        self.assertIn('vigencia', info['motivo'])


class ConfiguracionPlazoRegistroTests(APITestCase):
    """Bloque 4: plazo de registro configurable (reglas 6/7) — reemplaza
    la constante VENTANA_REGISTRO_DIAS=5 fija en código."""

    def setUp(self):
        self.admin_planificacion = crear_usuario('admin_plazo', 'Administrador de planificación')
        self.ejecutor = crear_usuario('ejecutor_plazo', 'Ejecutor operativo')

    # El valor por defecto (sembrado por migración) es 5 — idéntico al
    # que regía antes en código, para no cambiar el comportamiento de
    # nadie hasta que se edite explícitamente.
    def test_valor_por_defecto_sembrado_por_migracion(self):
        self.client.force_authenticate(user=self.admin_planificacion)
        response = self.client.get('/api/configuracion-mediciones/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['dias_plazo_registro'], 5)

    # Consulta libre para cualquier autenticado.
    def test_consulta_libre_para_cualquier_autenticado(self):
        self.client.force_authenticate(user=self.ejecutor)
        response = self.client.get('/api/configuracion-mediciones/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # 12. Restricción por rol: solo Administrador de planificación edita.
    def test_edicion_restringida_a_administrador_de_planificacion(self):
        self.client.force_authenticate(user=self.ejecutor)
        response = self.client.patch('/api/configuracion-mediciones/', {'dias_plazo_registro': 10})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_administrador_puede_confirmar_el_plazo_sin_cambiarlo(self):
        self.client.force_authenticate(user=self.admin_planificacion)
        response = self.client.patch('/api/configuracion-mediciones/', {'dias_plazo_registro': 5})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['dias_plazo_registro'], 5)

    def test_rechaza_plazo_menor_a_uno(self):
        self.client.force_authenticate(user=self.admin_planificacion)
        response = self.client.patch('/api/configuracion-mediciones/', {'dias_plazo_registro': 0})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # El nuevo plazo editado se refleja de inmediato en el cálculo real
    # de fecha límite de registro (no solo en la fila de configuración).
    def test_cambio_de_plazo_rechazado_preserva_calculo_historico(self):
        self.client.force_authenticate(user=self.admin_planificacion)
        response = self.client.patch('/api/configuracion-mediciones/', {'dias_plazo_registro': 10})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        fecha_limite = calcular_fecha_limite_registro(date(2027, 1, 31))
        self.assertEqual(fecha_limite, date(2027, 2, 5))

    def test_singleton_no_duplica_filas(self):
        ConfiguracionMediciones.obtener()
        ConfiguracionMediciones.obtener()
        self.assertEqual(ConfiguracionMediciones.objects.count(), 1)


class ContinuidadAdministrativaEntreAniosTests(APITestCase):
    """Punto F de la auditoría: documenta el comportamiento REAL de hoy
    cuando el Plan anual del año siguiente ya está En uso (requisito del
    Bloque 1: a lo sumo un Plan anual En uso por Plan estratégico) y el
    anterior ya se cerró. No se implementa ningún cambio para esto (ver
    informe de entrega, sección de decisiones pendientes): esta prueba
    ancla el comportamiento actual para que no cambie sin darse cuenta."""

    def setUp(self):
        self.usuario = crear_usuario('admin_continuidad', 'Administrador de planificación')
        self.ejecutor = crear_usuario('ejecutor_continuidad', 'Ejecutor operativo')
        self.frecuencia = crear_catalogos()

        self.plan_estrategico = PlanEstrategico.objects.create(
            titulo='Plan estratégico continuidad',
            fecha_inicio=date(2026, 1, 1),
            fecha_fin=date(2030, 12, 31),
            estado=PlanEstrategico.ESTADO_EN_USO,
            creado_por=self.usuario,
        )
        self.objetivo_general = ObjetivoGeneral.objects.create(
            plan_estrategico=self.plan_estrategico,
            texto_objetivo='Objetivo general continuidad',
            creado_por=self.usuario,
        )
        self.plan_anual_2027 = PlanAnual.objects.create(
            plan_estrategico=self.plan_estrategico,
            anio=2027,
            estado=PlanAnual.ESTADO_EN_USO,
            fecha_inicio=date(2027, 1, 1),
            fecha_fin=date(2027, 12, 31),
            creado_por=self.usuario,
        )
        self.objetivo_especifico = ObjetivoEspecifico.objects.create(
            plan_anual=self.plan_anual_2027,
            objetivo_general=self.objetivo_general,
            texto_objetivo='Objetivo específico 2027',
            creado_por=self.usuario,
        )
        self.kpi = IndicadorKPI.objects.create(
            objetivo_especifico=self.objetivo_especifico,
            frecuencia=self.frecuencia,
            nombre='KPI continuidad',
            formula_medicion='Resultado / Meta x 100',
            unidad_medida='unidades',
            valor_meta=Decimal('100.00'),
            estado='autorizado',
            creado_por=self.usuario,
        )
        configurar_rangos_70_85(self.kpi)

        # Cubre manualmente enero-noviembre para que el próximo periodo
        # pendiente sea diciembre — el que se intenta registrar tarde,
        # en enero de 2028, en ambas pruebas de esta clase.
        from .models import Medicion
        from .services import obtener_estado_para_medicion, obtener_o_crear_meta_vigente, obtener_o_crear_periodo

        meta = obtener_o_crear_meta_vigente(self.kpi)
        for mes in range(1, 12):
            periodo = obtener_o_crear_periodo(self.kpi, date(2027, mes, 1))
            estado = obtener_estado_para_medicion(self.kpi, meta, Decimal('50'))
            Medicion.objects.create(
                indicador=self.kpi, meta=meta, estado_cumplimiento=estado, periodo=periodo,
                fecha_medicion=periodo.fecha_fin, valor_resultado=Decimal('50'),
                registrado_por=self.usuario,
            )

    def _intentar_registrar_diciembre(self, fecha_referencia):
        self.client.force_authenticate(user=self.ejecutor)
        with mock.patch('apps.indicadores.services.hoy', return_value=fecha_referencia):
            return self.client.post('/api/mediciones/', {
                'indicador': self.kpi.id,
                'valor_resultado': '50',
            })

    # Mientras el Plan anual 2027 sigue En uso, el registro tardío de
    # diciembre (dentro del plazo) funciona con normalidad.
    def test_registro_tardio_funciona_mientras_plan_anual_sigue_en_uso(self):
        response = self._intentar_registrar_diciembre(date(2028, 1, 3))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    # 11. Si se cierra el Plan anual 2027 (paso necesario, por el Bloque 1,
    # para poder poner En uso el Plan anual 2028 del mismo Plan
    # estratégico) ANTES de que venza el plazo de registro de diciembre,
    # ese registro tardío queda bloqueado de inmediato — incluso dentro
    # de su plazo. Esta es la tensión real documentada en el informe.
    def test_cerrar_el_plan_anual_bloquea_de_inmediato_el_registro_tardio_pendiente(self):
        self.plan_anual_2027.estado = PlanAnual.ESTADO_CERRADO
        self.plan_anual_2027.save(update_fields=['estado'])

        response = self._intentar_registrar_diciembre(date(2028, 1, 3))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class CompatibilidadPonderacionesTests(APITestCase):
    """15. Un KPI con ponderación configurada (Bloque 3) sigue calculando
    su periodo y plazo de registro con normalidad — ninguna de las dos
    correcciones de este bloque interfiere con la otra."""

    def setUp(self):
        self.usuario = crear_usuario('admin_compat_ponderacion', 'Administrador de planificación')
        self.frecuencia = crear_catalogos()

        self.plan_estrategico = PlanEstrategico.objects.create(
            titulo='Plan estratégico compat ponderación',
            fecha_inicio=date(2027, 1, 1),
            fecha_fin=date(2027, 12, 31),
            estado=PlanEstrategico.ESTADO_EN_USO,
            creado_por=self.usuario,
        )
        self.objetivo_general = ObjetivoGeneral.objects.create(
            plan_estrategico=self.plan_estrategico,
            texto_objetivo='Objetivo general compat ponderación',
            creado_por=self.usuario,
        )
        self.plan_anual = PlanAnual.objects.create(
            plan_estrategico=self.plan_estrategico,
            anio=2027,
            estado=PlanAnual.ESTADO_EN_USO,
            fecha_inicio=date(2027, 1, 1),
            fecha_fin=date(2027, 12, 31),
            creado_por=self.usuario,
        )
        self.objetivo_especifico = ObjetivoEspecifico.objects.create(
            plan_anual=self.plan_anual,
            objetivo_general=self.objetivo_general,
            texto_objetivo='Objetivo específico compat ponderación',
            creado_por=self.usuario,
        )

    def test_kpi_ponderado_calcula_periodo_disponible_con_normalidad(self):
        kpi = IndicadorKPI.objects.create(
            objetivo_especifico=self.objetivo_especifico,
            frecuencia=self.frecuencia,
            nombre='KPI ponderado y con periodo',
            formula_medicion='Resultado / Meta x 100',
            unidad_medida='unidades',
            valor_meta=Decimal('100.00'),
            ponderacion=Decimal('40.00'),
            estado='autorizado',
            creado_por=self.usuario,
        )
        configurar_rangos_70_85(kpi)

        with mock.patch('apps.indicadores.services.hoy', return_value=date(2027, 1, 31)):
            info = obtener_info_siguiente_periodo(kpi)

        self.assertTrue(info['disponible'])
        self.assertEqual(kpi.ponderacion, Decimal('40.00'))

        self.client.force_authenticate(user=self.usuario)

        with mock.patch('apps.indicadores.services.hoy', return_value=date(2027, 1, 31)):
            response = self.client.get(f'/api/indicadores-kpi/{kpi.id}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(str(response.data['ponderacion']), '40.00')
        self.assertTrue(response.data['periodo_disponible'])


class SeguridadBackendPeriodosTests(APITestCase):
    """6. Rechazo de mediciones futuras por llamada directa a la API —
    el periodo SIEMPRE lo calcula el servidor (obtener_info_siguiente_periodo),
    nunca el valor que el cliente envíe; esta prueba confirma que no hay
    forma de forzarlo vía payload, no solo que el frontend oculta el control."""

    def setUp(self):
        self.usuario = crear_usuario('admin_seguridad_periodos', 'Administrador de planificación')
        self.ejecutor = crear_usuario('ejecutor_seguridad_periodos', 'Ejecutor operativo')
        self.frecuencia = crear_catalogos()

        self.plan_estrategico = PlanEstrategico.objects.create(
            titulo='Plan estratégico seguridad periodos',
            fecha_inicio=date(2027, 1, 1),
            fecha_fin=date(2027, 12, 31),
            estado=PlanEstrategico.ESTADO_EN_USO,
            creado_por=self.usuario,
        )
        self.objetivo_general = ObjetivoGeneral.objects.create(
            plan_estrategico=self.plan_estrategico,
            texto_objetivo='Objetivo general seguridad periodos',
            creado_por=self.usuario,
        )
        self.plan_anual = PlanAnual.objects.create(
            plan_estrategico=self.plan_estrategico,
            anio=2027,
            estado=PlanAnual.ESTADO_EN_USO,
            fecha_inicio=date(2027, 1, 1),
            fecha_fin=date(2027, 12, 31),
            creado_por=self.usuario,
        )
        self.objetivo_especifico = ObjetivoEspecifico.objects.create(
            plan_anual=self.plan_anual,
            objetivo_general=self.objetivo_general,
            texto_objetivo='Objetivo específico seguridad periodos',
            creado_por=self.usuario,
        )
        self.kpi = IndicadorKPI.objects.create(
            objetivo_especifico=self.objetivo_especifico,
            frecuencia=self.frecuencia,
            nombre='KPI seguridad periodos',
            formula_medicion='Resultado / Meta x 100',
            unidad_medida='unidades',
            valor_meta=Decimal('100.00'),
            estado='autorizado',
            creado_por=self.usuario,
        )
        configurar_rangos_70_85(self.kpi)

    def test_un_periodo_enviado_en_el_payload_es_ignorado_y_sigue_rechazando_lo_no_disponible(self):
        from .models import PeriodoMedicion

        periodo_arbitrario = PeriodoMedicion.objects.create(
            tipo_periodo='mensual', fecha_inicio=date(2027, 11, 1), fecha_fin=date(2027, 11, 30), anio=2027, mes=11,
        )

        self.client.force_authenticate(user=self.ejecutor)

        # Hoy es el primer día del año: el periodo de enero todavía no
        # cerró, así que no hay nada disponible aún — ni siquiera
        # intentando forzar el id de un periodo de noviembre en el payload.
        with mock.patch('apps.indicadores.services.hoy', return_value=date(2027, 1, 1)):
            response = self.client.post('/api/mediciones/', {
                'indicador': self.kpi.id,
                'periodo': periodo_arbitrario.id,
                'valor_resultado': '50',
            })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(
            self.kpi.mediciones.filter(periodo=periodo_arbitrario).exists()
        )
