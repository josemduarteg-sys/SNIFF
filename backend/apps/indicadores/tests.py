from rest_framework import status
from rest_framework.test import APITestCase

from apps.estrategia.models import ObjetivoEspecifico, ObjetivoGeneral, PlanAnual, PlanEstrategico
from apps.usuarios.models import Rol, Usuario

from .models import EstadoCumplimiento, Frecuencia, IndicadorKPI, RangoKPI


def crear_usuario_admin(username):
    rol, _ = Rol.objects.get_or_create(
        nombre='Administrador',
        defaults={'descripcion': 'Rol de prueba', 'estado': True},
    )

    usuario = Usuario.objects.create_user(username=username, password='clave-prueba-123')
    usuario.rol = rol
    usuario.correo = f'{username}@sniff.test'
    usuario.save()

    return usuario


class IndicadorKPITests(APITestCase):
    """Bloque 3 - casos 1 a 24 del plan de pruebas."""

    def setUp(self):
        self.usuario = crear_usuario_admin('admin_kpi')
        self.client.force_authenticate(user=self.usuario)

        self.frecuencia = Frecuencia.objects.create(nombre='Mensual', estado=True)

        # crear_rangos_provisionales() (disparado en cada creación de KPI)
        # requiere que estos tres EstadoCumplimiento existan en el catálogo.
        for nombre, color in [('Incumplido', 'rojo'), ('En riesgo', 'amarillo'), ('Favorable', 'verde')]:
            EstadoCumplimiento.objects.get_or_create(
                nombre=nombre, defaults={'color': color, 'estado': True}
            )

        self.plan_estrategico = PlanEstrategico.objects.create(
            titulo='Plan estratégico KPI',
            fecha_inicio='2027-01-01',
            fecha_fin='2030-12-31',
            estado=PlanEstrategico.ESTADO_EN_USO,
            creado_por=self.usuario,
        )

        self.objetivo_general = ObjetivoGeneral.objects.create(
            plan_estrategico=self.plan_estrategico,
            texto_objetivo='Objetivo general de prueba',
            creado_por=self.usuario,
        )

        self.plan_anual_en_uso = PlanAnual.objects.create(
            plan_estrategico=self.plan_estrategico,
            anio=2027,
            estado=PlanAnual.ESTADO_EN_USO,
            creado_por=self.usuario,
        )

        self.plan_anual_borrador = PlanAnual.objects.create(
            plan_estrategico=self.plan_estrategico, anio=2028, creado_por=self.usuario,
        )

        self.plan_anual_cerrado = PlanAnual.objects.create(
            plan_estrategico=self.plan_estrategico,
            anio=2029,
            estado=PlanAnual.ESTADO_CERRADO,
            creado_por=self.usuario,
        )

        self.objetivo_especifico_en_uso = ObjetivoEspecifico.objects.create(
            plan_anual=self.plan_anual_en_uso,
            objetivo_general=self.objetivo_general,
            texto_objetivo='Objetivo específico 2027',
            creado_por=self.usuario,
        )

        self.objetivo_especifico_borrador = ObjetivoEspecifico.objects.create(
            plan_anual=self.plan_anual_borrador,
            objetivo_general=self.objetivo_general,
            texto_objetivo='Objetivo específico 2028',
            creado_por=self.usuario,
        )

        self.objetivo_especifico_cerrado = ObjetivoEspecifico.objects.create(
            plan_anual=self.plan_anual_cerrado,
            objetivo_general=self.objetivo_general,
            texto_objetivo='Objetivo específico 2029',
            creado_por=self.usuario,
        )

    def payload_base(self, objetivo_especifico_id, nombre='KPI de prueba'):
        return {
            'objetivo_especifico': objetivo_especifico_id,
            'frecuencia': self.frecuencia.id,
            'nombre': nombre,
            'descripcion': 'Descripción de prueba',
            'formula_medicion': '(Resultado obtenido / Meta) x 100',
            'unidad_medida': '%',
            'valor_meta': '85.00',
        }

    # 1 y 2. KPI nuevo pertenece a ObjetivoEspecifico y nace en Borrador.
    def test_kpi_pertenece_a_objetivo_especifico_y_nace_borrador(self):
        response = self.client.post(
            '/api/indicadores-kpi/', self.payload_base(self.objetivo_especifico_en_uso.id)
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['objetivo_especifico'], self.objetivo_especifico_en_uso.id)
        self.assertEqual(response.data['estado'], 'borrador')

    # 3. Puede crearse sobre ObjetivoEspecifico de PlanAnual En uso.
    def test_creacion_permitida_sobre_plan_anual_en_uso(self):
        response = self.client.post(
            '/api/indicadores-kpi/', self.payload_base(self.objetivo_especifico_en_uso.id)
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    # 4. Rechaza ObjetivoEspecifico cuyo PlanAnual esté Borrador.
    def test_rechaza_plan_anual_borrador(self):
        response = self.client.post(
            '/api/indicadores-kpi/', self.payload_base(self.objetivo_especifico_borrador.id)
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # 5. Rechaza ObjetivoEspecifico cuyo PlanAnual esté Cerrado.
    def test_rechaza_plan_anual_cerrado(self):
        response = self.client.post(
            '/api/indicadores-kpi/', self.payload_base(self.objetivo_especifico_cerrado.id)
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # 6. Rechaza creación/modificación si PlanEstrategico está Cerrado.
    def test_rechaza_creacion_si_plan_estrategico_cerrado(self):
        self.plan_estrategico.estado = PlanEstrategico.ESTADO_CERRADO
        self.plan_estrategico.save(update_fields=['estado'])

        response = self.client.post(
            '/api/indicadores-kpi/', self.payload_base(self.objetivo_especifico_en_uso.id)
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # 7. Fórmula de medición obligatoria.
    def test_formula_medicion_obligatoria(self):
        payload = self.payload_base(self.objetivo_especifico_en_uso.id)
        payload.pop('formula_medicion')

        response = self.client.post('/api/indicadores-kpi/', payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # 8. Fórmula vacía o solo espacios rechazada.
    def test_formula_medicion_vacia_o_espacios_rechazada(self):
        payload = self.payload_base(self.objetivo_especifico_en_uso.id)
        payload['formula_medicion'] = '   '

        response = self.client.post('/api/indicadores-kpi/', payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # 9. Meta obligatoria.
    def test_meta_obligatoria(self):
        payload = self.payload_base(self.objetivo_especifico_en_uso.id)
        payload.pop('valor_meta')

        response = self.client.post('/api/indicadores-kpi/', payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # 10. Frecuencia obligatoria.
    def test_frecuencia_obligatoria(self):
        payload = self.payload_base(self.objetivo_especifico_en_uso.id)
        payload.pop('frecuencia')

        response = self.client.post('/api/indicadores-kpi/', payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # 11. Unidad de medida obligatoria.
    def test_unidad_medida_obligatoria(self):
        payload = self.payload_base(self.objetivo_especifico_en_uso.id)
        payload.pop('unidad_medida')

        response = self.client.post('/api/indicadores-kpi/', payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # 12. Nombre obligatorio.
    def test_nombre_obligatorio(self):
        payload = self.payload_base(self.objetivo_especifico_en_uso.id)
        payload['nombre'] = '   '

        response = self.client.post('/api/indicadores-kpi/', payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # 13. Mismo nombre dentro del mismo ObjetivoEspecifico rechazado.
    def test_mismo_nombre_mismo_objetivo_especifico_rechazado(self):
        self.client.post(
            '/api/indicadores-kpi/',
            self.payload_base(self.objetivo_especifico_en_uso.id, nombre='KPI repetido'),
        )

        response = self.client.post(
            '/api/indicadores-kpi/',
            self.payload_base(self.objetivo_especifico_en_uso.id, nombre='KPI repetido'),
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # 14. Mismo nombre en diferente ObjetivoEspecifico permitido.
    def test_mismo_nombre_diferente_objetivo_especifico_permitido(self):
        plan_anual_b = PlanAnual.objects.create(
            plan_estrategico=self.plan_estrategico,
            anio=2030,
            estado=PlanAnual.ESTADO_EN_USO,
            creado_por=self.usuario,
        )

        objetivo_especifico_b = ObjetivoEspecifico.objects.create(
            plan_anual=plan_anual_b,
            objetivo_general=self.objetivo_general,
            texto_objetivo='Objetivo específico B',
            creado_por=self.usuario,
        )

        self.client.post(
            '/api/indicadores-kpi/',
            self.payload_base(self.objetivo_especifico_en_uso.id, nombre='KPI compartido'),
        )

        response = self.client.post(
            '/api/indicadores-kpi/',
            self.payload_base(objetivo_especifico_b.id, nombre='KPI compartido'),
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    # 15. Mismo nombre en Plan 2027 y Plan 2028 permitido.
    def test_mismo_nombre_plan_2027_y_plan_2028_permitido(self):
        self.plan_anual_borrador.estado = PlanAnual.ESTADO_EN_USO
        self.plan_anual_borrador.save(update_fields=['estado'])

        self.client.post(
            '/api/indicadores-kpi/',
            self.payload_base(self.objetivo_especifico_en_uso.id, nombre='Recuperación de cartera'),
        )

        response = self.client.post(
            '/api/indicadores-kpi/',
            self.payload_base(self.objetivo_especifico_borrador.id, nombre='Recuperación de cartera'),
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    # 16, 17, 18. No existen fecha_inicio/fecha_fin/fuente_dato/tipo_calculo
    # propios en el modelo (fuente de verdad: los campos reales del modelo).
    def test_no_existen_campos_eliminados_en_el_modelo(self):
        nombres_campos = {campo.name for campo in IndicadorKPI._meta.get_fields()}

        self.assertNotIn('fecha_inicio', nombres_campos)
        self.assertNotIn('fecha_fin', nombres_campos)
        self.assertNotIn('fuente_dato', nombres_campos)
        self.assertNotIn('tipo_calculo', nombres_campos)

    # 19. Autorización actual del KPI continúa funcionando.
    def test_autorizacion_funciona(self):
        creado = self.client.post(
            '/api/indicadores-kpi/', self.payload_base(self.objetivo_especifico_en_uso.id)
        )
        kpi_id = creado.data['id']

        response = self.client.post(f'/api/indicadores-kpi/{kpi_id}/autorizar/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['estado'], 'autorizado')

    # 20. Anulación actual continúa funcionando.
    def test_anulacion_funciona(self):
        creado = self.client.post(
            '/api/indicadores-kpi/', self.payload_base(self.objetivo_especifico_en_uso.id)
        )
        kpi_id = creado.data['id']

        response = self.client.post(f'/api/indicadores-kpi/{kpi_id}/anular/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['estado'], 'anulado')

    # 21. Un KPI autorizado conserva las reglas actuales de edición.
    def test_kpi_autorizado_bloquea_edicion_de_campos_principales(self):
        creado = self.client.post(
            '/api/indicadores-kpi/', self.payload_base(self.objetivo_especifico_en_uso.id)
        )
        kpi_id = creado.data['id']
        self.client.post(f'/api/indicadores-kpi/{kpi_id}/autorizar/')

        response = self.client.patch(f'/api/indicadores-kpi/{kpi_id}/', {'nombre': 'Nombre nuevo'})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # 22. Plan estratégico Cerrado congela KPI (edición y transiciones).
    def test_plan_estrategico_cerrado_congela_kpi(self):
        creado = self.client.post(
            '/api/indicadores-kpi/', self.payload_base(self.objetivo_especifico_en_uso.id)
        )
        kpi_id = creado.data['id']

        self.plan_estrategico.estado = PlanEstrategico.ESTADO_CERRADO
        self.plan_estrategico.save(update_fields=['estado'])

        response_patch = self.client.patch(
            f'/api/indicadores-kpi/{kpi_id}/', {'nombre': 'Otro nombre'}
        )
        self.assertEqual(response_patch.status_code, status.HTTP_400_BAD_REQUEST)

        response_autorizar = self.client.post(f'/api/indicadores-kpi/{kpi_id}/autorizar/')
        self.assertEqual(response_autorizar.status_code, status.HTTP_400_BAD_REQUEST)

    # 23. RangoKPI sigue funcionando para el nuevo KPI.
    def test_rango_kpi_se_crea_para_nuevo_kpi(self):
        creado = self.client.post(
            '/api/indicadores-kpi/', self.payload_base(self.objetivo_especifico_en_uso.id)
        )
        kpi_id = creado.data['id']

        rangos = RangoKPI.objects.filter(indicador_id=kpi_id)

        self.assertEqual(rangos.count(), 3)
        nombres = set(rangos.values_list('estado_cumplimiento__nombre', flat=True))
        self.assertEqual(nombres, {'Incumplido', 'En riesgo', 'Favorable'})

    # 24. No quedan referencias backend rotas por el cambio de FK: flujo
    # completo de medición (usa fecha_inicio_vigencia/fecha_fin_vigencia,
    # obtener_siguiente_periodo_esperado, MetaKPI, RangoKPI, Alerta).
    # Bloque 4: el periodo/fecha ya no los elige el cliente, así que se
    # mockea "hoy" dentro de la ventana de registro de enero 2027 (el
    # PlanAnual de este fixture es 2027) en vez de depender de la fecha
    # real del entorno de pruebas.
    def test_flujo_medicion_completo_no_rompe_por_cambio_de_fk(self):
        from datetime import date
        from unittest import mock

        creado = self.client.post(
            '/api/indicadores-kpi/', self.payload_base(self.objetivo_especifico_en_uso.id)
        )
        kpi_id = creado.data['id']
        self.client.post(f'/api/indicadores-kpi/{kpi_id}/autorizar/')

        with mock.patch('apps.indicadores.services.hoy', return_value=date(2027, 1, 31)):
            siguiente = self.client.get(
                '/api/mediciones/siguiente-periodo/', {'indicador': kpi_id}
            )
            self.assertEqual(siguiente.status_code, status.HTTP_200_OK)
            self.assertTrue(siguiente.data['disponible'])

            response_medicion = self.client.post('/api/mediciones/', {
                'indicador': kpi_id,
                'valor_resultado': '90',
                'observacion': '',
            })

        self.assertEqual(response_medicion.status_code, status.HTTP_201_CREATED)


# ============================================================
# BLOQUE 4 - Periodos automaticos, ventana de 5 dias, cierre
# automatico en 0.00, evidencia como archivo.
# ============================================================

import shutil
import tempfile
from datetime import date
from decimal import Decimal
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings

from .models import Medicion
from .services import (
    calcular_fecha_cierre_periodo,
    calcular_fecha_limite_registro,
    cerrar_mediciones_vencidas,
    crear_rangos_provisionales,
    formatear_periodo,
    obtener_info_siguiente_periodo,
    obtener_intervalo_meses,
    obtener_siguiente_periodo_esperado,
)


def crear_catalogos_medicion():
    for nombre, color in [('Incumplido', 'rojo'), ('En riesgo', 'amarillo'), ('Favorable', 'verde')]:
        EstadoCumplimiento.objects.get_or_create(
            nombre=nombre, defaults={'color': color, 'estado': True}
        )

    frecuencias = {}

    for nombre in ('Mensual', 'Bimestral', 'Trimestral', 'Semestral', 'Anual'):
        frecuencias[nombre], _ = Frecuencia.objects.get_or_create(
            nombre=nombre, defaults={'estado': True}
        )

    return frecuencias


class MedicionTestsBase(APITestCase):
    """Fixtures comunes: Plan estrategico En uso 2027-2030, Plan anual 2027
    En uso, un Objetivo especifico, y catalogos de EstadoCumplimiento y
    Frecuencia necesarios para crear KPI autorizados con rangos."""

    NOMBRE_USUARIO = 'admin_mediciones_base'

    def setUp(self):
        self.usuario = crear_usuario_admin(self.NOMBRE_USUARIO)
        self.client.force_authenticate(user=self.usuario)
        self.frecuencias = crear_catalogos_medicion()

        self.plan_estrategico = PlanEstrategico.objects.create(
            titulo='Plan Mediciones',
            # Fechas como objetos date (no strings): estos fixtures pasan la
            # instancia en memoria de plan_estrategico directamente como FK
            # (sin recargar desde la base), así que fecha_inicio/fecha_fin
            # deben quedar ya tipadas para que fecha_inicio_vigencia /
            # fecha_fin_vigencia puedan compararlas con otras fechas.
            fecha_inicio=date(2027, 1, 1),
            fecha_fin=date(2030, 12, 31),
            estado=PlanEstrategico.ESTADO_EN_USO,
            creado_por=self.usuario,
        )

        self.objetivo_general = ObjetivoGeneral.objects.create(
            plan_estrategico=self.plan_estrategico,
            texto_objetivo='Objetivo general de mediciones',
            creado_por=self.usuario,
        )

        self.plan_anual = PlanAnual.objects.create(
            plan_estrategico=self.plan_estrategico,
            anio=2027,
            estado=PlanAnual.ESTADO_EN_USO,
            creado_por=self.usuario,
        )

        self.objetivo_especifico = ObjetivoEspecifico.objects.create(
            plan_anual=self.plan_anual,
            objetivo_general=self.objetivo_general,
            texto_objetivo='Objetivo especifico de mediciones',
            creado_por=self.usuario,
        )

    def crear_kpi(self, frecuencia_nombre='Mensual', nombre='KPI mediciones', valor_meta='100.00', unidad='unidades'):
        kpi = IndicadorKPI.objects.create(
            objetivo_especifico=self.objetivo_especifico,
            frecuencia=self.frecuencias[frecuencia_nombre],
            nombre=nombre,
            formula_medicion='Resultado obtenido / Meta x 100',
            unidad_medida=unidad,
            valor_meta=Decimal(valor_meta),
            estado='autorizado',
            creado_por=self.usuario,
        )
        crear_rangos_provisionales(kpi)
        return kpi


class PeriodosTests(MedicionTestsBase):
    """Bloque 4 - casos 1 a 8: periodos automaticos por frecuencia."""

    NOMBRE_USUARIO = 'admin_periodos'

    # 1. Mensual genera Enero como primer periodo.
    def test_mensual_genera_enero_como_primer_periodo(self):
        kpi = self.crear_kpi('Mensual')
        primer = obtener_siguiente_periodo_esperado(kpi)
        self.assertEqual(primer, date(2027, 1, 1))

    # 2. Bimestral genera Enero-Febrero.
    def test_bimestral_genera_enero_febrero(self):
        kpi = self.crear_kpi('Bimestral')
        primer = obtener_siguiente_periodo_esperado(kpi)
        intervalo = obtener_intervalo_meses(kpi)
        self.assertEqual(intervalo, 2)
        self.assertEqual(formatear_periodo(primer, intervalo), 'enero - febrero 2027')

    # 3. Trimestral genera Enero-Marzo.
    def test_trimestral_genera_enero_marzo(self):
        kpi = self.crear_kpi('Trimestral')
        primer = obtener_siguiente_periodo_esperado(kpi)
        intervalo = obtener_intervalo_meses(kpi)
        self.assertEqual(formatear_periodo(primer, intervalo), 'enero - marzo 2027')

    # 4. Semestral genera Enero-Junio.
    def test_semestral_genera_enero_junio(self):
        kpi = self.crear_kpi('Semestral')
        primer = obtener_siguiente_periodo_esperado(kpi)
        intervalo = obtener_intervalo_meses(kpi)
        self.assertEqual(formatear_periodo(primer, intervalo), 'enero - junio 2027')

    # 5. Anual genera Enero-Diciembre.
    def test_anual_genera_enero_diciembre(self):
        kpi = self.crear_kpi('Anual')
        primer = obtener_siguiente_periodo_esperado(kpi)
        intervalo = obtener_intervalo_meses(kpi)
        self.assertEqual(formatear_periodo(primer, intervalo), 'enero - diciembre 2027')

    # 6. Despues del primer periodo avanza correctamente al siguiente.
    def test_avanza_correctamente_al_siguiente_periodo(self):
        kpi = self.crear_kpi('Mensual')

        with mock.patch('apps.indicadores.services.hoy', return_value=date(2027, 1, 31)):
            response = self.client.post('/api/mediciones/', {
                'indicador': kpi.id,
                'valor_resultado': '50',
            })

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        siguiente = obtener_siguiente_periodo_esperado(kpi)
        self.assertEqual(siguiente, date(2027, 2, 1))

    # 7. No permite saltar periodos.
    def test_no_permite_saltar_periodos(self):
        kpi = self.crear_kpi('Mensual')

        # Sin mediciones todavia, el "siguiente periodo" siempre es enero,
        # sin importar que tan lejos este la fecha de referencia: no hay
        # forma de que la API salte directo a marzo.
        with mock.patch('apps.indicadores.services.hoy', return_value=date(2027, 3, 15)):
            info = obtener_info_siguiente_periodo(kpi)

        self.assertEqual(info['periodo_nombre'], 'enero 2027')

    # 8. No crea periodos fuera del ano del PlanAnual.
    def test_no_crea_periodos_fuera_del_anio_del_plan_anual(self):
        kpi = self.crear_kpi('Anual')

        with mock.patch('apps.indicadores.services.hoy', return_value=date(2027, 12, 31)):
            response = self.client.post('/api/mediciones/', {
                'indicador': kpi.id,
                'valor_resultado': '50',
            })
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

            info = obtener_info_siguiente_periodo(kpi)

        self.assertFalse(info['disponible'])
        self.assertIn('No existen más periodos', info['motivo'])


class VentanaRegistroTests(MedicionTestsBase):
    """Bloque 4 - casos 9 a 13: ventana de 5 dias para registro manual."""

    NOMBRE_USUARIO = 'admin_ventana'

    def _intentar_registrar(self, kpi, fecha):
        with mock.patch('apps.indicadores.services.hoy', return_value=fecha):
            return self.client.post('/api/mediciones/', {
                'indicador': kpi.id,
                'valor_resultado': '50',
            })

    # 9. Antes del cierre -> registro rechazado.
    def test_antes_del_cierre_rechazado(self):
        kpi = self.crear_kpi('Mensual')
        response = self._intentar_registrar(kpi, date(2027, 1, 20))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # 10. Dia de cierre -> permitido.
    def test_dia_de_cierre_permitido(self):
        kpi = self.crear_kpi('Mensual')
        response = self._intentar_registrar(kpi, date(2027, 1, 31))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    # 11. Dia +1 -> permitido.
    def test_dia_mas_1_permitido(self):
        kpi = self.crear_kpi('Mensual')
        response = self._intentar_registrar(kpi, date(2027, 2, 1))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    # 12. Dia +5 -> permitido.
    def test_dia_mas_5_permitido(self):
        kpi = self.crear_kpi('Mensual')
        response = self._intentar_registrar(kpi, date(2027, 2, 5))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    # 13. Dia +6 -> registro manual rechazado.
    def test_dia_mas_6_rechazado(self):
        kpi = self.crear_kpi('Mensual')
        response = self._intentar_registrar(kpi, date(2027, 2, 6))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_calculo_fecha_limite_directo(self):
        fecha_cierre = date(2027, 1, 31)
        self.assertEqual(calcular_fecha_limite_registro(fecha_cierre), date(2027, 2, 5))

    def test_fecha_cierre_ultimo_dia_real_bisiesto(self):
        # Febrero 2028 es bisiesto: el cierre mensual debe caer en 29, no 28.
        self.assertEqual(
            calcular_fecha_cierre_periodo(date(2028, 2, 1), 1),
            date(2028, 2, 29),
        )


class CierreAutomaticoTests(MedicionTestsBase):
    """Bloque 4 - casos 14 a 20: cierre automatico en 0.00."""

    NOMBRE_USUARIO = 'admin_cierre'

    # 14. Dia +6 sin medicion -> crea 0.00.
    def test_dia_mas_6_sin_medicion_crea_cero(self):
        kpi = self.crear_kpi('Mensual')

        with mock.patch('apps.indicadores.services.hoy', return_value=date(2027, 2, 6)):
            resultado = cerrar_mediciones_vencidas()

        self.assertEqual(resultado['cierres_creados'], 1)
        medicion = Medicion.objects.get(indicador=kpi)
        self.assertEqual(medicion.valor_resultado, Decimal('0.0000'))

    # 15. cierre_automatico=True.
    def test_cierre_automatico_true(self):
        kpi = self.crear_kpi('Mensual')

        with mock.patch('apps.indicadores.services.hoy', return_value=date(2027, 2, 6)):
            cerrar_mediciones_vencidas()

        medicion = Medicion.objects.get(indicador=kpi)
        self.assertTrue(medicion.cierre_automatico)

    # 16. registrado_por=NULL.
    def test_registrado_por_null(self):
        kpi = self.crear_kpi('Mensual')

        with mock.patch('apps.indicadores.services.hoy', return_value=date(2027, 2, 6)):
            cerrar_mediciones_vencidas()

        medicion = Medicion.objects.get(indicador=kpi)
        self.assertIsNone(medicion.registrado_por)

    # 17. fecha_medicion = cierre real del periodo.
    def test_fecha_medicion_es_cierre_real_del_periodo(self):
        kpi = self.crear_kpi('Mensual')

        with mock.patch('apps.indicadores.services.hoy', return_value=date(2027, 2, 6)):
            cerrar_mediciones_vencidas()

        medicion = Medicion.objects.get(indicador=kpi)
        self.assertEqual(medicion.fecha_medicion, date(2027, 1, 31))

    # 18. Vuelve a ejecutar comando -> no duplica.
    def test_ejecutar_de_nuevo_no_duplica(self):
        kpi = self.crear_kpi('Mensual')

        with mock.patch('apps.indicadores.services.hoy', return_value=date(2027, 2, 6)):
            resultado1 = cerrar_mediciones_vencidas()
            resultado2 = cerrar_mediciones_vencidas()

        self.assertEqual(resultado1['cierres_creados'], 1)
        self.assertEqual(resultado2['cierres_creados'], 0)
        self.assertEqual(Medicion.objects.filter(indicador=kpi).count(), 1)

    # 19. Varios periodos vencidos -> procesa secuencialmente.
    def test_varios_periodos_vencidos_procesa_secuencialmente(self):
        kpi = self.crear_kpi('Mensual')

        # Al 1/mayo/2027: Enero, Febrero y Marzo ya vencieron su ventana;
        # Abril (cierre 30/04, limite 05/05) todavia no.
        with mock.patch('apps.indicadores.services.hoy', return_value=date(2027, 5, 1)):
            resultado = cerrar_mediciones_vencidas()

        self.assertEqual(resultado['cierres_creados'], 3)
        periodos = list(
            Medicion.objects.filter(indicador=kpi)
            .order_by('periodo__fecha_inicio')
            .values_list('periodo__fecha_inicio', flat=True)
        )
        self.assertEqual(periodos, [date(2027, 1, 1), date(2027, 2, 1), date(2027, 3, 1)])

    # 20. Automatica no admite PATCH/PUT.
    def test_automatica_no_admite_patch_put(self):
        kpi = self.crear_kpi('Mensual')

        with mock.patch('apps.indicadores.services.hoy', return_value=date(2027, 2, 6)):
            cerrar_mediciones_vencidas()

        medicion = Medicion.objects.get(indicador=kpi)
        response = self.client.patch(f'/api/mediciones/{medicion.id}/', {'valor_resultado': '99'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('cerrada automáticamente', str(response.data))


class JerarquiaMedicionTests(MedicionTestsBase):
    """Bloque 4 - casos 21 a 25: KPI autorizado y jerarquia Cerrada."""

    NOMBRE_USUARIO = 'admin_jerarquia_medicion'

    def _intentar_registrar(self, kpi):
        with mock.patch('apps.indicadores.services.hoy', return_value=date(2027, 1, 31)):
            return self.client.post('/api/mediciones/', {
                'indicador': kpi.id,
                'valor_resultado': '50',
            })

    # 21. KPI borrador -> no permite medicion.
    def test_kpi_borrador_no_permite_medicion(self):
        kpi = self.crear_kpi('Mensual')
        kpi.estado = 'borrador'
        kpi.save(update_fields=['estado'])

        response = self._intentar_registrar(kpi)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # 22. KPI anulado -> no permite medicion.
    def test_kpi_anulado_no_permite_medicion(self):
        kpi = self.crear_kpi('Mensual')
        kpi.estado = 'anulado'
        kpi.save(update_fields=['estado'])

        response = self._intentar_registrar(kpi)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # 23. KPI autorizado -> si.
    def test_kpi_autorizado_permite_medicion(self):
        kpi = self.crear_kpi('Mensual')
        response = self._intentar_registrar(kpi)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    # 24. PlanAnual Cerrado -> bloquea.
    def test_plan_anual_cerrado_bloquea(self):
        kpi = self.crear_kpi('Mensual')
        self.plan_anual.estado = PlanAnual.ESTADO_CERRADO
        self.plan_anual.save(update_fields=['estado'])

        response = self._intentar_registrar(kpi)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # 25. PlanEstrategico Cerrado -> bloquea.
    def test_plan_estrategico_cerrado_bloquea(self):
        kpi = self.crear_kpi('Mensual')
        self.plan_estrategico.estado = PlanEstrategico.ESTADO_CERRADO
        self.plan_estrategico.save(update_fields=['estado'])

        response = self._intentar_registrar(kpi)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


_MEDIA_ROOT_PRUEBAS_EVIDENCIA = tempfile.mkdtemp(prefix='sniff_evidencia_tests_')


@override_settings(MEDIA_ROOT=_MEDIA_ROOT_PRUEBAS_EVIDENCIA)
class EvidenciaTests(MedicionTestsBase):
    """Bloque 4 - casos 26 a 33: evidencia como archivo.

    Usa un MEDIA_ROOT temporal (fuera del proyecto) para no dejar archivos
    de prueba reales en backend/media/; se elimina al terminar la clase.
    """

    NOMBRE_USUARIO = 'admin_evidencia'

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(_MEDIA_ROOT_PRUEBAS_EVIDENCIA, ignore_errors=True)

    def _registrar_con_evidencia(self, kpi, contenido, nombre_archivo, content_type):
        archivo = SimpleUploadedFile(nombre_archivo, contenido, content_type=content_type)

        with mock.patch('apps.indicadores.services.hoy', return_value=date(2027, 1, 31)):
            return self.client.post(
                '/api/mediciones/',
                {'indicador': kpi.id, 'valor_resultado': '50', 'evidencia': archivo},
                format='multipart',
            )

    # 26. PDF valido -> permitido.
    def test_pdf_valido_permitido(self):
        kpi = self.crear_kpi('Mensual', nombre='KPI evidencia pdf')
        response = self._registrar_con_evidencia(kpi, b'%PDF-1.4 contenido', 'respaldo.pdf', 'application/pdf')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    # 27. JPG valido -> permitido.
    def test_jpg_valido_permitido(self):
        kpi = self.crear_kpi('Mensual', nombre='KPI evidencia jpg')
        response = self._registrar_con_evidencia(kpi, b'contenido-imagen', 'foto.jpg', 'image/jpeg')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    # 28. JPEG valido -> permitido.
    def test_jpeg_valido_permitido(self):
        kpi = self.crear_kpi('Mensual', nombre='KPI evidencia jpeg')
        response = self._registrar_con_evidencia(kpi, b'contenido-imagen', 'foto.jpeg', 'image/jpeg')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    # 29. DOCX -> rechazado.
    def test_docx_rechazado(self):
        kpi = self.crear_kpi('Mensual', nombre='KPI evidencia docx')
        response = self._registrar_con_evidencia(
            kpi, b'contenido', 'informe.docx',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # 30. XLSX -> rechazado.
    def test_xlsx_rechazado(self):
        kpi = self.crear_kpi('Mensual', nombre='KPI evidencia xlsx')
        response = self._registrar_con_evidencia(
            kpi, b'contenido', 'datos.xlsx',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # 31. Archivo >10 MB -> rechazado.
    def test_archivo_mayor_10mb_rechazado(self):
        kpi = self.crear_kpi('Mensual', nombre='KPI evidencia grande')
        contenido_grande = b'0' * (10 * 1024 * 1024 + 1)
        response = self._registrar_con_evidencia(kpi, contenido_grande, 'grande.pdf', 'application/pdf')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # 32. Evidencia opcional -> medicion sin archivo permitida.
    def test_evidencia_opcional(self):
        kpi = self.crear_kpi('Mensual', nombre='KPI sin evidencia')

        with mock.patch('apps.indicadores.services.hoy', return_value=date(2027, 1, 31)):
            response = self.client.post('/api/mediciones/', {
                'indicador': kpi.id,
                'valor_resultado': '50',
            })

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    # 33. Evidencia accesible solo a usuario autenticado.
    def test_evidencia_accesible_solo_usuario_autenticado(self):
        kpi = self.crear_kpi('Mensual', nombre='KPI evidencia protegida')
        response = self._registrar_con_evidencia(kpi, b'%PDF-1.4', 'respaldo.pdf', 'application/pdf')
        medicion_id = response.data['id']

        response_autenticado = self.client.get(f'/api/mediciones/{medicion_id}/evidencia/')
        self.assertEqual(response_autenticado.status_code, status.HTTP_200_OK)

        self.client.force_authenticate(user=None)
        response_anonimo = self.client.get(f'/api/mediciones/{medicion_id}/evidencia/')
        self.assertIn(response_anonimo.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))


# ============================================================
# BLOQUE 5 - Promedio acumulado, estado acumulado (RangoKPI) y
# alertas de cumplimiento basadas en el promedio del KPI completo.
# ============================================================

from .models import Alerta
from .services import (
    calcular_promedio_acumulado_kpi,
    generar_alertas_periodos_vencidos,
    obtener_estado_acumulado_kpi,
)


def registrar_medicion(client, kpi, valor, fecha):
    """Registra una medición vía la API real (mismo patrón de Bloque 4:
    mockea `hoy()` para caer dentro de la ventana de registro del periodo
    correspondiente a esa fecha)."""
    with mock.patch('apps.indicadores.services.hoy', return_value=fecha):
        return client.post('/api/mediciones/', {
            'indicador': kpi.id,
            'valor_resultado': str(valor),
        })


def alertas_cumplimiento_pendientes(indicador):
    """Alertas 'pendiente' del KPI que NO son de tipo periodo vencido —
    la familia que gestiona `actualizar_alerta_cumplimiento_kpi`."""
    return Alerta.objects.filter(
        indicador=indicador, estado_alerta='pendiente',
    ).exclude(tipo_alerta='Periodo vencido sin medición')


class PromedioAcumuladoTests(MedicionTestsBase):
    """Bloque 5 - casos 1 a 11: REGLA DEFINITIVA del promedio acumulado
    (promedio directo de valor_resultado, nunca de porcentaje_cumplimiento
    ni de valor_resultado/meta)."""

    NOMBRE_USUARIO = 'admin_promedio_acumulado'

    # 1. Sin mediciones -> promedio_acumulado es None (nunca 0.00).
    def test_sin_mediciones_promedio_none(self):
        kpi = self.crear_kpi('Mensual', nombre='KPI sin mediciones')
        self.assertIsNone(calcular_promedio_acumulado_kpi(kpi))

    # 2. Una sola medición 80 -> promedio 80.00.
    def test_una_medicion_80(self):
        kpi = self.crear_kpi('Mensual', nombre='KPI una medicion')
        registrar_medicion(self.client, kpi, '80', date(2027, 1, 31))
        self.assertEqual(calcular_promedio_acumulado_kpi(kpi), Decimal('80.00'))

    # 3. 80 + 60 -> promedio 70.00.
    def test_dos_mediciones_80_60_setenta(self):
        kpi = self.crear_kpi('Mensual', nombre='KPI dos mediciones')
        registrar_medicion(self.client, kpi, '80', date(2027, 1, 31))
        registrar_medicion(self.client, kpi, '60', date(2027, 2, 28))
        self.assertEqual(calcular_promedio_acumulado_kpi(kpi), Decimal('70.00'))

    # 4. 80 + 60 + 40 -> promedio 60.00 (nunca normalizado contra meta).
    def test_tres_mediciones_80_60_40_sesenta(self):
        kpi = self.crear_kpi('Mensual', nombre='KPI tres mediciones', valor_meta='85.00')
        registrar_medicion(self.client, kpi, '80', date(2027, 1, 31))
        registrar_medicion(self.client, kpi, '60', date(2027, 2, 28))
        registrar_medicion(self.client, kpi, '40', date(2027, 3, 31))
        self.assertEqual(calcular_promedio_acumulado_kpi(kpi), Decimal('60.00'))

    # 5. 80 + 60 + 0 (cierre automático) -> promedio 46.67.
    def test_incluye_cierre_automatico_en_cero(self):
        kpi = self.crear_kpi('Mensual', nombre='KPI con cierre 0')
        registrar_medicion(self.client, kpi, '80', date(2027, 1, 31))
        registrar_medicion(self.client, kpi, '60', date(2027, 2, 28))

        with mock.patch('apps.indicadores.services.hoy', return_value=date(2027, 4, 6)):
            resultado = cerrar_mediciones_vencidas()

        self.assertEqual(resultado['cierres_creados'], 1)
        self.assertEqual(calcular_promedio_acumulado_kpi(kpi), Decimal('46.67'))

    # 6. El cierre automático participa exactamente igual que uno manual
    # (mismo resultado que si el usuario hubiera registrado 0 a mano).
    def test_cierre_automatico_participa_igual_que_manual(self):
        kpi_auto = self.crear_kpi('Mensual', nombre='KPI cierre auto')
        registrar_medicion(self.client, kpi_auto, '80', date(2027, 1, 31))
        registrar_medicion(self.client, kpi_auto, '60', date(2027, 2, 28))

        with mock.patch('apps.indicadores.services.hoy', return_value=date(2027, 4, 6)):
            cerrar_mediciones_vencidas()

        kpi_manual = self.crear_kpi('Mensual', nombre='KPI cero manual')
        registrar_medicion(self.client, kpi_manual, '80', date(2027, 1, 31))
        registrar_medicion(self.client, kpi_manual, '60', date(2027, 2, 28))
        registrar_medicion(self.client, kpi_manual, '0', date(2027, 3, 31))

        self.assertEqual(
            calcular_promedio_acumulado_kpi(kpi_auto),
            calcular_promedio_acumulado_kpi(kpi_manual),
        )

    # 7. No mezcla mediciones de otro KPI.
    def test_no_mezcla_con_otro_kpi(self):
        kpi1 = self.crear_kpi('Mensual', nombre='KPI aislado 1')
        kpi2 = self.crear_kpi('Mensual', nombre='KPI aislado 2')

        registrar_medicion(self.client, kpi1, '80', date(2027, 1, 31))
        registrar_medicion(self.client, kpi2, '20', date(2027, 1, 31))

        self.assertEqual(calcular_promedio_acumulado_kpi(kpi1), Decimal('80.00'))
        self.assertEqual(calcular_promedio_acumulado_kpi(kpi2), Decimal('20.00'))

    # 8. No mezcla mediciones de otro año / otro KPI (un KPI pertenece a un
    # único PlanAnual, así que "otro año" implica siempre "otro KPI").
    def test_no_mezcla_con_otro_anio(self):
        kpi_2027 = self.crear_kpi('Mensual', nombre='KPI 2027')
        registrar_medicion(self.client, kpi_2027, '80', date(2027, 1, 31))

        plan_anual_2028 = PlanAnual.objects.create(
            plan_estrategico=self.plan_estrategico,
            anio=2028,
            estado=PlanAnual.ESTADO_EN_USO,
            creado_por=self.usuario,
        )
        objetivo_2028 = ObjetivoEspecifico.objects.create(
            plan_anual=plan_anual_2028,
            objetivo_general=self.objetivo_general,
            texto_objetivo='Objetivo especifico 2028',
            creado_por=self.usuario,
        )
        kpi_2028 = IndicadorKPI.objects.create(
            objetivo_especifico=objetivo_2028,
            frecuencia=self.frecuencias['Mensual'],
            nombre='KPI 2028',
            formula_medicion='Resultado obtenido / Meta x 100',
            unidad_medida='unidades',
            valor_meta=Decimal('100.00'),
            estado='autorizado',
            creado_por=self.usuario,
        )
        crear_rangos_provisionales(kpi_2028)
        registrar_medicion(self.client, kpi_2028, '20', date(2028, 1, 31))

        self.assertEqual(calcular_promedio_acumulado_kpi(kpi_2027), Decimal('80.00'))
        self.assertEqual(calcular_promedio_acumulado_kpi(kpi_2028), Decimal('20.00'))

    # 9, 10 y 11. Acumulado histórico "hasta cierta medición", ordenado por
    # periodo (no por fecha_registro).
    def test_historico_hasta_cada_medicion(self):
        kpi = self.crear_kpi('Mensual', nombre='KPI historico')

        respuesta_enero = registrar_medicion(self.client, kpi, '80', date(2027, 1, 31))
        respuesta_febrero = registrar_medicion(self.client, kpi, '60', date(2027, 2, 28))
        respuesta_marzo = registrar_medicion(self.client, kpi, '40', date(2027, 3, 31))

        self.assertEqual(
            Decimal(str(respuesta_enero.data['promedio_acumulado_hasta_medicion'])),
            Decimal('80.00'),
        )
        self.assertEqual(
            Decimal(str(respuesta_febrero.data['promedio_acumulado_hasta_medicion'])),
            Decimal('70.00'),
        )
        self.assertEqual(
            Decimal(str(respuesta_marzo.data['promedio_acumulado_hasta_medicion'])),
            Decimal('60.00'),
        )


class RangosAcumuladosTests(MedicionTestsBase):
    """Bloque 5 - casos 12 a 16: el estado acumulado se clasifica
    ÚNICAMENTE con los RangoKPI reales del indicador, nunca con umbrales
    hardcodeados en el backend."""

    NOMBRE_USUARIO = 'admin_rangos_acumulado'

    # 12. Promedio >= 85 -> Favorable (rango provisional de la plantilla).
    def test_promedio_favorable(self):
        kpi = self.crear_kpi('Mensual', nombre='KPI favorable')
        registrar_medicion(self.client, kpi, '90', date(2027, 1, 31))

        promedio = calcular_promedio_acumulado_kpi(kpi)
        estado = obtener_estado_acumulado_kpi(kpi, promedio)
        self.assertEqual(estado.nombre, 'Favorable')

    # 13. 70 <= promedio < 85 -> En riesgo.
    def test_promedio_en_riesgo(self):
        kpi = self.crear_kpi('Mensual', nombre='KPI en riesgo')
        registrar_medicion(self.client, kpi, '75', date(2027, 1, 31))

        promedio = calcular_promedio_acumulado_kpi(kpi)
        estado = obtener_estado_acumulado_kpi(kpi, promedio)
        self.assertEqual(estado.nombre, 'En riesgo')

    # 14. Promedio < 70 -> Incumplido.
    def test_promedio_incumplido(self):
        kpi = self.crear_kpi('Mensual', nombre='KPI incumplido')
        registrar_medicion(self.client, kpi, '30', date(2027, 1, 31))

        promedio = calcular_promedio_acumulado_kpi(kpi)
        estado = obtener_estado_acumulado_kpi(kpi, promedio)
        self.assertEqual(estado.nombre, 'Incumplido')

    # 15. Ningún RangoKPI cubre el promedio -> 'Pendiente de actualización'
    # (mismo fallback técnico que ya usan las Mediciones individuales).
    def test_sin_rango_aplicable_pendiente_actualizacion(self):
        EstadoCumplimiento.objects.get_or_create(
            nombre='Pendiente de actualización',
            defaults={'color': 'gris', 'estado': True},
        )
        kpi = self.crear_kpi('Mensual', nombre='KPI sin rango')
        RangoKPI.objects.filter(indicador=kpi).delete()

        estado_favorable = EstadoCumplimiento.objects.get(nombre='Favorable')
        RangoKPI.objects.create(
            indicador=kpi,
            estado_cumplimiento=estado_favorable,
            valor_minimo=Decimal('85'),
            valor_maximo=None,
            estado=True,
        )

        registrar_medicion(self.client, kpi, '50', date(2027, 1, 31))

        promedio = calcular_promedio_acumulado_kpi(kpi)
        estado = obtener_estado_acumulado_kpi(kpi, promedio)

        self.assertEqual(promedio, Decimal('50.00'))
        self.assertEqual(estado.nombre, 'Pendiente de actualización')

    # 16. No usa umbrales hardcodeados (85/70): con un RangoKPI propio
    # distinto de la plantilla, un promedio de 60 puede clasificar como
    # Favorable si así lo define el RangoKPI real del indicador.
    def test_no_usa_umbrales_hardcodeados(self):
        kpi = self.crear_kpi('Mensual', nombre='KPI umbral propio')
        RangoKPI.objects.filter(indicador=kpi).delete()

        estado_incumplido = EstadoCumplimiento.objects.get(nombre='Incumplido')
        estado_favorable = EstadoCumplimiento.objects.get(nombre='Favorable')
        RangoKPI.objects.create(
            indicador=kpi,
            estado_cumplimiento=estado_incumplido,
            valor_minimo=Decimal('0'),
            valor_maximo=Decimal('50'),
            estado=True,
        )
        RangoKPI.objects.create(
            indicador=kpi,
            estado_cumplimiento=estado_favorable,
            valor_minimo=Decimal('50'),
            valor_maximo=None,
            estado=True,
        )

        registrar_medicion(self.client, kpi, '60', date(2027, 1, 31))

        promedio = calcular_promedio_acumulado_kpi(kpi)
        estado = obtener_estado_acumulado_kpi(kpi, promedio)

        self.assertEqual(promedio, Decimal('60.00'))
        self.assertEqual(estado.nombre, 'Favorable')


class AlertasAcumuladasTests(MedicionTestsBase):
    """Bloque 5 - casos 17 a 24: alerta de cumplimiento basada en el
    promedio acumulado, con máximo una alerta 'pendiente' por KPI."""

    NOMBRE_USUARIO = 'admin_alertas_acumuladas'

    # 17. Favorable -> no genera alerta pendiente.
    def test_favorable_no_genera_alerta_pendiente(self):
        kpi = self.crear_kpi('Mensual', nombre='KPI alerta favorable')
        registrar_medicion(self.client, kpi, '90', date(2027, 1, 31))

        self.assertEqual(alertas_cumplimiento_pendientes(kpi).count(), 0)

    # 18. En riesgo -> exactamente una alerta pendiente.
    def test_en_riesgo_genera_una_alerta_pendiente(self):
        kpi = self.crear_kpi('Mensual', nombre='KPI alerta riesgo')
        registrar_medicion(self.client, kpi, '75', date(2027, 1, 31))

        alertas = alertas_cumplimiento_pendientes(kpi)
        self.assertEqual(alertas.count(), 1)
        self.assertEqual(alertas.first().tipo_alerta, 'KPI En riesgo')
        self.assertIn('promedio acumulado', alertas.first().mensaje)

    # 19. Otra medición que mantiene el mismo estado -> se actualiza la
    # misma alerta, nunca se duplica.
    def test_otra_medicion_mismo_estado_mantiene_una_sola_alerta(self):
        kpi = self.crear_kpi('Mensual', nombre='KPI alerta persistente')
        registrar_medicion(self.client, kpi, '75', date(2027, 1, 31))
        registrar_medicion(self.client, kpi, '75', date(2027, 2, 28))

        alertas = alertas_cumplimiento_pendientes(kpi)
        self.assertEqual(alertas.count(), 1)
        self.assertEqual(alertas.first().tipo_alerta, 'KPI En riesgo')

    # 20. En riesgo -> Incumplido: descarta la alerta anterior y crea/deja
    # la correcta para el nuevo estado (sigue habiendo solo una pendiente).
    def test_transicion_en_riesgo_a_incumplido(self):
        kpi = self.crear_kpi('Mensual', nombre='KPI transicion riesgo incumplido')
        registrar_medicion(self.client, kpi, '75', date(2027, 1, 31))
        registrar_medicion(self.client, kpi, '20', date(2027, 2, 28))

        pendientes = alertas_cumplimiento_pendientes(kpi)
        self.assertEqual(pendientes.count(), 1)
        self.assertEqual(pendientes.first().tipo_alerta, 'KPI Incumplido')

        descartadas = Alerta.objects.filter(
            indicador=kpi, estado_alerta='descartada', tipo_alerta='KPI En riesgo',
        )
        self.assertEqual(descartadas.count(), 1)

    # 21. Incumplido -> Favorable: descarta la alerta pendiente sin crear
    # una nueva.
    def test_transicion_incumplido_a_favorable_descarta(self):
        kpi = self.crear_kpi('Mensual', nombre='KPI transicion incumplido favorable')
        respuesta = registrar_medicion(self.client, kpi, '30', date(2027, 1, 31))
        self.assertEqual(alertas_cumplimiento_pendientes(kpi).count(), 1)

        medicion_id = respuesta.data['id']
        respuesta_patch = self.client.patch(
            f'/api/mediciones/{medicion_id}/', {'valor_resultado': '95'}
        )
        self.assertEqual(respuesta_patch.status_code, status.HTTP_200_OK)

        self.assertEqual(alertas_cumplimiento_pendientes(kpi).count(), 0)
        self.assertEqual(calcular_promedio_acumulado_kpi(kpi), Decimal('95.00'))

    # 22. Cierre automático en 0.00 recalcula promedio y alerta igual que
    # una medición manual.
    def test_cierre_automatico_recalcula_promedio_y_alerta(self):
        kpi = self.crear_kpi('Mensual', nombre='KPI cierre auto alerta')
        registrar_medicion(self.client, kpi, '75', date(2027, 1, 31))
        self.assertEqual(alertas_cumplimiento_pendientes(kpi).first().tipo_alerta, 'KPI En riesgo')

        # Solo el periodo de febrero vence su ventana a esta fecha (el de
        # marzo todavía no) para cerrar exactamente UN periodo automático.
        with mock.patch('apps.indicadores.services.hoy', return_value=date(2027, 3, 6)):
            cerrar_mediciones_vencidas()

        self.assertEqual(calcular_promedio_acumulado_kpi(kpi), Decimal('37.50'))
        pendientes = alertas_cumplimiento_pendientes(kpi)
        self.assertEqual(pendientes.count(), 1)
        self.assertEqual(pendientes.first().tipo_alerta, 'KPI Incumplido')

        medicion_automatica = Medicion.objects.get(indicador=kpi, cierre_automatico=True)
        self.assertEqual(pendientes.first().medicion_id, medicion_automatica.id)

    # 23. La alerta de 'Periodo vencido sin medición' sigue siendo
    # independiente de la alerta de cumplimiento acumulado.
    def test_alerta_periodo_vencido_independiente(self):
        kpi = self.crear_kpi('Mensual', nombre='KPI alerta vencido')
        registrar_medicion(self.client, kpi, '75', date(2027, 1, 31))

        with mock.patch('apps.indicadores.services.hoy', return_value=date(2027, 4, 1)):
            generar_alertas_periodos_vencidos()

        alertas_vencido = Alerta.objects.filter(
            indicador=kpi, tipo_alerta='Periodo vencido sin medición', estado_alerta='pendiente',
        )
        pendientes_cumplimiento = alertas_cumplimiento_pendientes(kpi)

        self.assertTrue(alertas_vencido.exists())
        self.assertEqual(pendientes_cumplimiento.count(), 1)
        self.assertEqual(pendientes_cumplimiento.first().tipo_alerta, 'KPI En riesgo')

    # 24. Editar el valor_resultado de una medición manual recalcula el
    # promedio y la alerta de inmediato.
    def test_edicion_medicion_recalcula_promedio_y_alerta(self):
        kpi = self.crear_kpi('Mensual', nombre='KPI edicion recalcula')
        respuesta = registrar_medicion(self.client, kpi, '60', date(2027, 1, 31))
        self.assertEqual(calcular_promedio_acumulado_kpi(kpi), Decimal('60.00'))
        self.assertEqual(alertas_cumplimiento_pendientes(kpi).first().tipo_alerta, 'KPI Incumplido')

        medicion_id = respuesta.data['id']
        respuesta_patch = self.client.patch(
            f'/api/mediciones/{medicion_id}/', {'valor_resultado': '95'}
        )

        self.assertEqual(respuesta_patch.status_code, status.HTTP_200_OK)
        self.assertEqual(calcular_promedio_acumulado_kpi(kpi), Decimal('95.00'))
        self.assertEqual(alertas_cumplimiento_pendientes(kpi).count(), 0)


class SerializersAcumuladosTests(MedicionTestsBase):
    """Bloque 5 - casos 25 a 27: campos calculados expuestos por los
    serializers, de solo lectura."""

    NOMBRE_USUARIO = 'admin_serializers_acumulado'

    # 25. IndicadorKPISerializer expone promedio, cantidad y estado.
    def test_indicador_kpi_serializer_expone_promedio_cantidad_estado(self):
        kpi = self.crear_kpi('Mensual', nombre='KPI serializer acumulado')
        registrar_medicion(self.client, kpi, '80', date(2027, 1, 31))
        registrar_medicion(self.client, kpi, '60', date(2027, 2, 28))

        response = self.client.get(f'/api/indicadores-kpi/{kpi.id}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(str(response.data['promedio_acumulado'])), Decimal('70.00'))
        self.assertEqual(response.data['cantidad_mediciones'], 2)
        self.assertEqual(response.data['estado_acumulado_nombre'], 'En riesgo')
        self.assertIsNotNone(response.data['estado_acumulado_color'])
        self.assertIsNotNone(response.data['estado_acumulado_id'])

    # 26. MedicionSerializer expone el acumulado histórico hasta esa
    # medición (distinto de valor_resultado y de porcentaje_cumplimiento).
    def test_medicion_serializer_expone_acumulado_historico(self):
        kpi = self.crear_kpi('Mensual', nombre='KPI serializer historico')
        r1 = registrar_medicion(self.client, kpi, '80', date(2027, 1, 31))
        r2 = registrar_medicion(self.client, kpi, '60', date(2027, 2, 28))

        self.assertEqual(
            Decimal(str(r1.data['promedio_acumulado_hasta_medicion'])), Decimal('80.00')
        )
        self.assertEqual(
            Decimal(str(r2.data['promedio_acumulado_hasta_medicion'])), Decimal('70.00')
        )
        self.assertEqual(Decimal(str(r1.data['valor_resultado'])), Decimal('80.0000'))
        self.assertIsNotNone(r2.data['estado_acumulado_hasta_medicion_nombre'])

    # 27. Los campos acumulados son de solo lectura: enviarlos en un PATCH
    # no los sobrescribe, siguen siendo el valor calculado.
    def test_campos_acumulados_son_solo_lectura(self):
        kpi = self.crear_kpi('Mensual', nombre='KPI campos solo lectura')
        registrar_medicion(self.client, kpi, '80', date(2027, 1, 31))

        response = self.client.patch(
            f'/api/indicadores-kpi/{kpi.id}/', {'promedio_acumulado': '999.00'}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(str(response.data['promedio_acumulado'])), Decimal('80.00'))


class CasoAisladoOchentaSesentaCuarentaTests(MedicionTestsBase):
    """Bloque 5 - punto 37: caso aislado que el proyecto exige verificar
    exactamente. Mediciones 80, 60, 40 (periodos 1, 2 y 3) NUNCA deben
    producir un promedio "normalizado contra meta" (70.58/68.42/etc.), solo
    el promedio directo de valor_resultado."""

    NOMBRE_USUARIO = 'admin_caso_80_60_40'

    def test_caso_80_60_40(self):
        kpi = self.crear_kpi('Mensual', nombre='KPI caso 80-60-40', valor_meta='85.00')

        r1 = registrar_medicion(self.client, kpi, '80', date(2027, 1, 31))
        r2 = registrar_medicion(self.client, kpi, '60', date(2027, 2, 28))
        r3 = registrar_medicion(self.client, kpi, '40', date(2027, 3, 31))

        self.assertEqual(
            Decimal(str(r1.data['promedio_acumulado_hasta_medicion'])), Decimal('80.00')
        )
        self.assertEqual(
            Decimal(str(r2.data['promedio_acumulado_hasta_medicion'])), Decimal('70.00')
        )
        self.assertEqual(
            Decimal(str(r3.data['promedio_acumulado_hasta_medicion'])), Decimal('60.00')
        )

        promedio_actual = calcular_promedio_acumulado_kpi(kpi)
        self.assertEqual(promedio_actual, Decimal('60.00'))
        self.assertNotEqual(promedio_actual, Decimal('70.58'))
        self.assertNotEqual(promedio_actual, Decimal('68.42'))

        estado = obtener_estado_acumulado_kpi(kpi, promedio_actual)
        self.assertEqual(estado.nombre, 'Incumplido')


class UnidadNoPorcentualTests(MedicionTestsBase):
    """Bloque 5 - punto 38: el promedio acumulado no asume que todos los
    KPI midan un porcentaje. KPI en 'días', resultados 5, 4, 6 -> promedio
    5.00 días (nunca con símbolo de %)."""

    NOMBRE_USUARIO = 'admin_dias'

    def test_promedio_en_dias_no_asume_porcentaje(self):
        kpi = self.crear_kpi('Mensual', nombre='KPI dias', valor_meta='5.00', unidad='días')

        registrar_medicion(self.client, kpi, '5', date(2027, 1, 31))
        registrar_medicion(self.client, kpi, '4', date(2027, 2, 28))
        r3 = registrar_medicion(self.client, kpi, '6', date(2027, 3, 31))

        promedio = calcular_promedio_acumulado_kpi(kpi)
        self.assertEqual(promedio, Decimal('5.00'))
        self.assertEqual(kpi.unidad_medida, 'días')
        self.assertEqual(
            Decimal(str(r3.data['promedio_acumulado_hasta_medicion'])), Decimal('5.00')
        )


# ============================================================
# BLOQUE 5.1 - UX de alertas: marcar una Alerta (cumplimiento o
# periodo vencido) como revisada, individual y en bloque, desde
# el Centro de notificaciones.
# ============================================================

from .services import marcar_alerta_revisada


def crear_usuario_operativo(username):
    rol, _ = Rol.objects.get_or_create(
        nombre='Operativo',
        defaults={'descripcion': 'Rol de prueba', 'estado': True},
    )

    usuario = Usuario.objects.create_user(username=username, password='clave-prueba-123')
    usuario.rol = rol
    usuario.correo = f'{username}@sniff.test'
    usuario.save()

    return usuario


class MarcarAlertaRevisadaTests(MedicionTestsBase):
    """Bloque 5.1 - casos A a D del plan de pruebas de alertas."""

    NOMBRE_USUARIO = 'admin_marcar_revisada'

    # A. Una alerta pendiente -> marcar revisada -> cambia de estado, queda
    # en BD (no se borra), con fecha_revision y revisado_por.
    def test_marcar_alerta_individual_revisada(self):
        kpi = self.crear_kpi('Mensual', nombre='KPI marcar revisada')
        registrar_medicion(self.client, kpi, '75', date(2027, 1, 31))

        alerta = alertas_cumplimiento_pendientes(kpi).first()
        self.assertIsNotNone(alerta)

        response = self.client.post(f'/api/alertas/{alerta.id}/marcar-revisada/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['estado_alerta'], 'revisada')

        alerta.refresh_from_db()
        self.assertEqual(alerta.estado_alerta, 'revisada')
        self.assertIsNotNone(alerta.fecha_revision)
        self.assertEqual(alerta.revisado_por_id, self.usuario.id)

        # Ya no aparece entre las pendientes del centro de notificaciones,
        # pero sigue existiendo en la base para trazabilidad.
        self.assertEqual(alertas_cumplimiento_pendientes(kpi).count(), 0)
        self.assertTrue(Alerta.objects.filter(id=alerta.id).exists())

    # Idempotencia: marcar de nuevo una alerta ya revisada (o descartada)
    # no falla y no cambia nada.
    def test_marcar_revisada_es_idempotente(self):
        kpi = self.crear_kpi('Mensual', nombre='KPI idempotente')
        registrar_medicion(self.client, kpi, '75', date(2027, 1, 31))
        alerta = alertas_cumplimiento_pendientes(kpi).first()

        self.client.post(f'/api/alertas/{alerta.id}/marcar-revisada/')
        alerta.refresh_from_db()
        fecha_revision_original = alerta.fecha_revision

        response = self.client.post(f'/api/alertas/{alerta.id}/marcar-revisada/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        alerta.refresh_from_db()
        self.assertEqual(alerta.estado_alerta, 'revisada')
        self.assertEqual(alerta.fecha_revision, fecha_revision_original)

    # B. Marcar todas las alertas pendientes en bloque.
    def test_marcar_todas_alertas_revisadas(self):
        kpi1 = self.crear_kpi('Mensual', nombre='KPI bloque 1')
        kpi2 = self.crear_kpi('Mensual', nombre='KPI bloque 2')
        registrar_medicion(self.client, kpi1, '75', date(2027, 1, 31))
        registrar_medicion(self.client, kpi2, '30', date(2027, 1, 31))

        self.assertEqual(Alerta.objects.filter(estado_alerta='pendiente').count(), 2)

        response = self.client.post('/api/alertas/marcar-todas-revisadas/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(Alerta.objects.filter(estado_alerta='pendiente').count(), 0)
        self.assertEqual(Alerta.objects.filter(estado_alerta='revisada').count(), 2)

    # "Marcar todas" sin ninguna alerta pendiente no debe producir error.
    def test_marcar_todas_sin_alertas_no_falla(self):
        response = self.client.post('/api/alertas/marcar-todas-revisadas/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # C. Revisar una alerta y luego registrar una nueva medición: si el KPI
    # sigue En riesgo/Incumplido, debe generarse una NUEVA alerta pendiente
    # y la anterior permanece 'revisada' en BD (no se reutiliza).
    def test_nueva_medicion_tras_revisar_genera_nueva_alerta(self):
        kpi = self.crear_kpi('Mensual', nombre='KPI nueva alerta tras revisar')
        registrar_medicion(self.client, kpi, '75', date(2027, 1, 31))

        alerta_original = alertas_cumplimiento_pendientes(kpi).first()
        marcar_alerta_revisada(alerta_original, usuario=self.usuario)

        # Sigue en riesgo/incumplido tras la segunda medición.
        registrar_medicion(self.client, kpi, '20', date(2027, 2, 28))

        pendientes = alertas_cumplimiento_pendientes(kpi)
        self.assertEqual(pendientes.count(), 1)
        self.assertNotEqual(pendientes.first().id, alerta_original.id)

        alerta_original.refresh_from_db()
        self.assertEqual(alerta_original.estado_alerta, 'revisada')

    # D. Si el KPI pasa a Favorable, no debe quedar alerta pendiente de
    # cumplimiento (ni una reutilizada ni una nueva).
    def test_favorable_tras_revisar_no_deja_pendiente(self):
        kpi = self.crear_kpi('Mensual', nombre='KPI favorable tras revisar')
        registrar_medicion(self.client, kpi, '75', date(2027, 1, 31))

        alerta_original = alertas_cumplimiento_pendientes(kpi).first()
        marcar_alerta_revisada(alerta_original, usuario=self.usuario)

        registrar_medicion(self.client, kpi, '95', date(2027, 2, 28))

        self.assertEqual(alertas_cumplimiento_pendientes(kpi).count(), 0)
        alerta_original.refresh_from_db()
        self.assertEqual(alerta_original.estado_alerta, 'revisada')

    # 'Periodo vencido sin medición' también puede marcarse revisada desde
    # el mismo endpoint (no es exclusivo de las alertas de cumplimiento).
    def test_periodo_vencido_tambien_puede_marcarse_revisada(self):
        kpi = self.crear_kpi('Mensual', nombre='KPI periodo vencido revisar')

        with mock.patch('apps.indicadores.services.hoy', return_value=date(2027, 4, 1)):
            generar_alertas_periodos_vencidos()

        alerta = Alerta.objects.filter(
            indicador=kpi, tipo_alerta='Periodo vencido sin medición',
        ).first()
        self.assertIsNotNone(alerta)

        response = self.client.post(f'/api/alertas/{alerta.id}/marcar-revisada/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        alerta.refresh_from_db()
        self.assertEqual(alerta.estado_alerta, 'revisada')

    # No amplía roles: un usuario no administrador sigue sin poder marcar
    # alertas como revisadas (mismo permiso ya existente en AlertaViewSet).
    def test_usuario_no_admin_no_puede_marcar_revisada(self):
        kpi = self.crear_kpi('Mensual', nombre='KPI permiso operativo')
        registrar_medicion(self.client, kpi, '75', date(2027, 1, 31))
        alerta = alertas_cumplimiento_pendientes(kpi).first()

        usuario_operativo = crear_usuario_operativo('operativo_marcar_revisada')
        self.client.force_authenticate(user=usuario_operativo)

        response = self.client.post(f'/api/alertas/{alerta.id}/marcar-revisada/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        alerta.refresh_from_db()
        self.assertEqual(alerta.estado_alerta, 'pendiente')
