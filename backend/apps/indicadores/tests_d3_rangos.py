"""D3: rangos de evaluación de KPI (criterio de Hernán del 06/10/2026).

- KPI nuevos en %: Incumplido de 0 a 60 inclusive, En riesgo de más de 60 a
  75 inclusive, Favorable más de 75 (límites técnicos 60,01 y 75,01).
- KPI en otra unidad: sin rangos automáticos; se configuran según su unidad
  antes de autorizar.
- Los rangos guardados (personalizados, invertidos o 70/85) no se tocan."""

from datetime import date
from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from rest_framework import status
from rest_framework.test import APITestCase

from apps.auditoria.models import Bitacora
from apps.estrategia.models import ObjetivoEspecifico, ObjetivoGeneral, PlanAnual, PlanEstrategico
from apps.usuarios.models import Rol, Usuario

from .models import EstadoCumplimiento, Frecuencia, IndicadorKPI, Medicion, RangoKPI
from .services import (
    calcular_promedio_acumulado_kpi,
    crear_rangos_provisionales,
    obtener_estado_acumulado_kpi,
    obtener_estado_para_medicion,
    obtener_o_crear_meta_vigente,
    obtener_o_crear_periodo,
)

URL = '/api/indicadores-kpi/'


def crear_usuario(username, rol_nombre):
    rol, _ = Rol.objects.get_or_create(nombre=rol_nombre, defaults={'descripcion': 'Rol de prueba', 'estado': True})
    usuario = Usuario.objects.create_user(username=username, password='clave-prueba-123')
    usuario.rol = rol
    usuario.correo = f'{username}@sniff.test'
    usuario.save()
    return usuario


class RangosBase(APITestCase):
    def setUp(self):
        self.admin = crear_usuario('admin_d3', 'Administrador de planificación')
        self.client.force_authenticate(user=self.admin)

        for nombre, color in [('Incumplido', 'rojo'), ('En riesgo', 'amarillo'), ('Favorable', 'verde')]:
            EstadoCumplimiento.objects.get_or_create(nombre=nombre, defaults={'color': color, 'estado': True})

        self.estados = {e.nombre: e for e in EstadoCumplimiento.objects.all()}
        self.frecuencia = Frecuencia.objects.create(nombre='Mensual', estado=True)
        plan = PlanEstrategico.objects.create(
            titulo='Plan D3', fecha_inicio=date(2027, 1, 1), fecha_fin=date(2030, 12, 31),
            estado=PlanEstrategico.ESTADO_EN_USO, creado_por=self.admin,
        )
        self.objetivo_general = ObjetivoGeneral.objects.create(plan_estrategico=plan, texto_objetivo='OG', creado_por=self.admin)
        self.plan_anual = PlanAnual.objects.create(
            plan_estrategico=plan, anio=2027, estado=PlanAnual.ESTADO_EN_USO,
            fecha_inicio=date(2027, 1, 1), fecha_fin=date(2027, 12, 31), creado_por=self.admin,
        )
        self.objetivo_especifico = ObjetivoEspecifico.objects.create(
            plan_anual=self.plan_anual, objetivo_general=self.objetivo_general, texto_objetivo='OE', creado_por=self.admin,
        )

    def crear_por_api(self, nombre, unidad='%'):
        response = self.client.post(URL, {
            'plan_anual': self.plan_anual.id, 'objetivo_general': self.objetivo_general.id,
            'objetivo_especifico': None, 'frecuencia': self.frecuencia.id, 'nombre': nombre,
            'descripcion': '', 'formula_medicion': 'R', 'unidad_medida': unidad, 'valor_meta': '5', 'ponderacion': '',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        return IndicadorKPI.objects.get(pk=response.data['id'])

    def kpi_orm(self, nombre, unidad='%', estado='autorizado'):
        return IndicadorKPI.objects.create(
            objetivo_especifico=self.objetivo_especifico, frecuencia=self.frecuencia, nombre=nombre,
            formula_medicion='R', unidad_medida=unidad, valor_meta=Decimal('85'), estado=estado, creado_por=self.admin,
        )

    def rangos(self, kpi):
        return sorted(
            (r.estado_cumplimiento.nombre, r.valor_minimo, r.valor_maximo, r.estado)
            for r in RangoKPI.objects.filter(indicador=kpi).select_related('estado_cumplimiento')
        )

    def poner_rangos(self, kpi, tramos):
        for nombre, minimo, maximo in tramos:
            RangoKPI.objects.create(
                indicador=kpi, estado_cumplimiento=self.estados[nombre],
                valor_minimo=Decimal(minimo), valor_maximo=Decimal(maximo) if maximo is not None else None, estado=True,
            )

    def configurar(self, kpi, tramos, usuario=None):
        self.client.force_authenticate(user=usuario or self.admin)
        return self.client.post(f'{URL}{kpi.id}/configurar-rangos/', {'rangos': [
            {'estado_cumplimiento': self.estados[nombre].id, 'valor_minimo': minimo, 'valor_maximo': maximo}
            for nombre, minimo, maximo in tramos
        ]}, format='json')

    def autorizar(self, kpi):
        self.client.force_authenticate(user=self.admin)
        return self.client.post(f'{URL}{kpi.id}/autorizar/')


PLANTILLA = [
    ('En riesgo', Decimal('60.0100'), Decimal('75.0100'), True),
    ('Favorable', Decimal('75.0100'), None, True),
    ('Incumplido', Decimal('0.0000'), Decimal('60.0100'), True),
]
INVERTIDOS_DIAS = [('Favorable', '0', '3'), ('En riesgo', '3', '6'), ('Incumplido', '6', None)]
PERSONALIZADOS_9 = [('Incumplido', '0', '49.99'), ('En riesgo', '49.99', '79.99'), ('Favorable', '79.99', None)]


class PlantillaPorcentualTests(RangosBase):
    def test_kpi_porcentual_nuevo_recibe_la_plantilla_60_75(self):
        kpi = self.crear_por_api('KPI cobertura')

        self.assertEqual(self.rangos(kpi), PLANTILLA)

    def test_limites_exactos_y_decimales(self):
        kpi = self.crear_por_api('KPI límites')
        meta = obtener_o_crear_meta_vigente(kpi)

        for valor, esperado in (
            ('0', 'Incumplido'), ('59.99', 'Incumplido'), ('60.00', 'Incumplido'),
            ('60.004', 'Incumplido'), ('60.01', 'En riesgo'), ('75.00', 'En riesgo'),
            ('75.01', 'Favorable'), ('100', 'Favorable'), ('120', 'Favorable'),
        ):
            estado = obtener_estado_para_medicion(kpi, meta, Decimal(valor))
            self.assertEqual(estado.nombre, esperado, valor)

    def test_el_promedio_se_clasifica_con_los_mismos_limites(self):
        kpi = self.crear_por_api('KPI promedio')
        meta = obtener_o_crear_meta_vigente(kpi)

        def promedio_de(*valores):
            Medicion.objects.filter(indicador=kpi).delete()
            for mes, valor in enumerate(valores, start=1):
                Medicion.objects.create(
                    indicador=kpi, meta=meta, periodo=obtener_o_crear_periodo(kpi, date(2027, mes, 1)),
                    estado_cumplimiento=self.estados['Favorable'], fecha_medicion=date(2027, mes, 28),
                    valor_resultado=Decimal(valor),
                )
            promedio = calcular_promedio_acumulado_kpi(kpi)
            return promedio, obtener_estado_acumulado_kpi(kpi, promedio).nombre

        self.assertEqual(promedio_de('50', '70'), (Decimal('60.00'), 'Incumplido'))
        self.assertEqual(promedio_de('60', '60.02'), (Decimal('60.01'), 'En riesgo'))
        self.assertEqual(promedio_de('70', '80'), (Decimal('75.00'), 'En riesgo'))
        self.assertEqual(promedio_de('75', '75.02'), (Decimal('75.01'), 'Favorable'))

    def test_kpi_porcentual_se_autoriza_con_la_plantilla(self):
        kpi = self.crear_por_api('KPI autorizable')

        self.assertEqual(self.autorizar(kpi).status_code, status.HTTP_200_OK)


class KpiNoPorcentualTests(RangosBase):
    def test_kpi_en_dias_se_crea_sin_rangos(self):
        kpi = self.crear_por_api('KPI tiempo de respuesta', unidad='días')

        self.assertEqual(self.rangos(kpi), [])

    def test_no_se_autoriza_sin_rangos_y_si_con_rangos_propios(self):
        kpi = self.crear_por_api('KPI tiempo', unidad='días')

        rechazo = self.autorizar(kpi)
        self.assertEqual(rechazo.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('no tiene rangos de evaluación', rechazo.data['detail'])
        kpi.refresh_from_db()
        self.assertEqual(kpi.estado, 'borrador')

        configurado = self.configurar(kpi, INVERTIDOS_DIAS)
        self.assertEqual(configurado.status_code, status.HTTP_200_OK, configurado.data)
        self.assertEqual(self.autorizar(kpi).status_code, status.HTTP_200_OK)

        # Menor es mejor: 2 días Favorable, 7 días Incumplido.
        meta = obtener_o_crear_meta_vigente(kpi)
        self.assertEqual(obtener_estado_para_medicion(kpi, meta, Decimal('2')).nombre, 'Favorable')
        self.assertEqual(obtener_estado_para_medicion(kpi, meta, Decimal('7')).nombre, 'Incumplido')
        self.assertTrue(Bitacora.objects.filter(modulo='Rangos KPI', descripcion__startswith='Configuró los rangos').exists())

    def test_kpi_no_porcentual_con_la_plantilla_porcentual_no_se_autoriza(self):
        # Creado en % y luego cambiado a días: conserva la plantilla.
        kpi = self.crear_por_api('KPI cambiado')
        self.client.patch(f'{URL}{kpi.id}/', {'unidad_medida': 'días'}, format='json')

        respuesta = self.autorizar(kpi)

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('conserva los rangos porcentuales', respuesta.data['detail'])

    def test_pasar_a_porcentaje_sin_rangos_recibe_la_plantilla(self):
        kpi = self.crear_por_api('KPI que pasa a %', unidad='días')

        self.client.patch(f'{URL}{kpi.id}/', {'unidad_medida': '%'}, format='json')

        self.assertEqual(self.rangos(kpi), PLANTILLA)


class ConfigurarRangosTests(RangosBase):
    def setUp(self):
        super().setUp()
        self.kpi = self.crear_por_api('KPI en días', unidad='días')

    def test_reemplaza_la_plantilla_por_rangos_invertidos_en_una_sola_operacion(self):
        porcentual = self.crear_por_api('KPI en %')

        respuesta = self.configurar(porcentual, INVERTIDOS_DIAS)

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK, respuesta.data)
        self.assertEqual(self.rangos(porcentual), sorted([
            ('Favorable', Decimal('0.0000'), Decimal('3.0000'), True),
            ('En riesgo', Decimal('3.0000'), Decimal('6.0000'), True),
            ('Incumplido', Decimal('6.0000'), None, True),
        ]))

    def test_rechaza_conjuntos_invalidos_sin_guardar_nada(self):
        casos = (
            ([('Favorable', '0', '5'), ('En riesgo', '3', '6')], 'se superponen'),
            ([('Favorable', '5', '3')], 'mayor que su mínimo'),
            ([('Favorable', '-1', '3')], 'negativo'),
            ([('Favorable', '', '3')], 'Indicá el mínimo'),
            ([('Favorable', 'x', '3')], 'deben ser números'),
            ([], 'al menos un rango'),
        )

        for tramos, mensaje in casos:
            respuesta = self.configurar(self.kpi, tramos)
            self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST, tramos)
            self.assertIn(mensaje, respuesta.data['detail'], tramos)

        repetido = self.client.post(f'{URL}{self.kpi.id}/configurar-rangos/', {'rangos': [
            {'estado_cumplimiento': self.estados['Favorable'].id, 'valor_minimo': '0', 'valor_maximo': '3'},
            {'estado_cumplimiento': self.estados['Favorable'].id, 'valor_minimo': '3', 'valor_maximo': '6'},
        ]}, format='json')
        self.assertIn('repetido', repetido.data['detail'])
        self.assertEqual(self.rangos(self.kpi), [])

    def test_solo_en_borrador_y_solo_el_administrador_de_planificacion(self):
        autorizado = self.kpi_orm('KPI autorizado', unidad='días')
        self.poner_rangos(autorizado, INVERTIDOS_DIAS)

        respuesta = self.configurar(autorizado, [('Favorable', '0', '10')])
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Borrador', respuesta.data['detail'])

        for rol in ('Ejecutor operativo', 'Usuario de consulta', 'Administrador del sistema'):
            otro = crear_usuario(f'sin_rangos_{rol[:5]}', rol)
            self.assertEqual(self.configurar(self.kpi, INVERTIDOS_DIAS, usuario=otro).status_code, status.HTTP_403_FORBIDDEN)

        self.assertEqual(self.rangos(self.kpi), [])

    def test_la_api_de_rangos_rechaza_superposiciones_y_maximos_invalidos(self):
        self.poner_rangos(self.kpi, INVERTIDOS_DIAS)
        self.client.force_authenticate(user=self.admin)

        superpuesto = self.client.post('/api/rangos-kpi/', {
            'indicador': self.kpi.id, 'estado_cumplimiento': self.estados['Favorable'].id,
            'valor_minimo': '1', 'valor_maximo': '4', 'estado': True,
        }, format='json')
        self.assertEqual(superpuesto.status_code, status.HTTP_400_BAD_REQUEST)

        rango = RangoKPI.objects.get(indicador=self.kpi, estado_cumplimiento=self.estados['Favorable'])
        invertido = self.client.patch(f'/api/rangos-kpi/{rango.id}/', {'valor_maximo': '0'}, format='json')
        self.assertEqual(invertido.status_code, status.HTTP_400_BAD_REQUEST)


class ComandoYKpiHistoricosTests(RangosBase):
    def test_el_comando_no_sobrescribe_rangos_existentes(self):
        kpi9 = self.kpi_orm('Como el KPI #9')
        self.poner_rangos(kpi9, PERSONALIZADOS_9)
        kpi10 = self.kpi_orm('Como el KPI #10', unidad='días')
        self.poner_rangos(kpi10, INVERTIDOS_DIAS)
        anterior = self.kpi_orm('Con la plantilla 70/85')
        self.poner_rangos(anterior, [('Incumplido', '0', '70'), ('En riesgo', '70', '85'), ('Favorable', '85', None)])
        porcentual_sin_rangos = self.kpi_orm('En % sin rangos')
        dias_sin_rangos = self.kpi_orm('En días sin rangos', unidad='días')

        antes = {kpi.id: self.rangos(kpi) for kpi in (kpi9, kpi10, anterior)}

        for _ in range(2):
            salida = StringIO()
            call_command('configurar_rangos_provisionales', stdout=salida)

        for kpi in (kpi9, kpi10, anterior):
            self.assertEqual(self.rangos(kpi), antes[kpi.id], kpi.nombre)

        self.assertEqual(self.rangos(porcentual_sin_rangos), PLANTILLA)
        self.assertEqual(self.rangos(dias_sin_rangos), [])
        self.assertIn('Rangos existentes modificados: 0', salida.getvalue())
        self.assertIn('Rangos creados: 0', salida.getvalue())

    def test_crear_rangos_no_modifica_un_kpi_que_ya_los_tiene(self):
        kpi = self.kpi_orm('Histórico 70/85')
        self.poner_rangos(kpi, [('Incumplido', '0', '70'), ('En riesgo', '70', '85'), ('Favorable', '85', None)])
        antes = self.rangos(kpi)

        self.assertEqual(crear_rangos_provisionales(kpi), 0)
        self.assertEqual(self.rangos(kpi), antes)

    def test_kpi_historicos_conservan_su_estado_y_el_de_sus_mediciones(self):
        """Un KPI con 70/85 y mediciones guardadas sigue igual (84,13 En riesgo,
        como el KPI #12): la plantilla nueva no se aplica a lo existente."""
        kpi = self.kpi_orm('Como el KPI #12')
        self.poner_rangos(kpi, [('Incumplido', '0', '70'), ('En riesgo', '70', '85'), ('Favorable', '85', None)])
        meta = obtener_o_crear_meta_vigente(kpi)
        medicion = Medicion.objects.create(
            indicador=kpi, meta=meta, periodo=obtener_o_crear_periodo(kpi, date(2027, 1, 1)),
            estado_cumplimiento=self.estados['En riesgo'], fecha_medicion=date(2027, 1, 31),
            valor_resultado=Decimal('84.13'),
        )

        datos = self.client.get(f'{URL}{kpi.id}/').data

        self.assertEqual(datos['estado_acumulado_nombre'], 'En riesgo')
        medicion.refresh_from_db()
        self.assertEqual(medicion.estado_cumplimiento.nombre, 'En riesgo')
        # El Dashboard sigue recibiendo el estado guardado en el listado.
        listado = {k['id']: k for k in self.client.get(URL).data}
        self.assertEqual(listado[kpi.id]['estado_acumulado_nombre'], 'En riesgo')
