"""Entrega a Hernán, Bloque A (alcance de la reunión del 06/10/2026): los
objetivos específicos están deshabilitados en la interfaz. El formulario de
KPI ya no tiene su selector y envía:
  - KPI nuevo: plan_anual + objetivo_general, objetivo_especifico=None.
  - KPI existente: además, el objetivo_especifico que ya tenía.
Se comprueba que el backend resuelve ambos casos sin que el usuario gestione
objetivos específicos, y que los vínculos existentes se conservan."""

from datetime import date
from decimal import Decimal

from rest_framework import status
from rest_framework.test import APITestCase

from apps.estrategia.models import ObjetivoEspecifico, ObjetivoGeneral, PlanAnual, PlanEstrategico
from apps.usuarios.models import Rol, Usuario

from .models import EstadoCumplimiento, Frecuencia, IndicadorKPI

URL = '/api/indicadores-kpi/'


def crear_usuario(username, rol_nombre):
    rol, _ = Rol.objects.get_or_create(nombre=rol_nombre, defaults={'descripcion': 'Rol de prueba', 'estado': True})
    usuario = Usuario.objects.create_user(username=username, password='clave-prueba-123')
    usuario.rol = rol
    usuario.correo = f'{username}@sniff.test'
    usuario.save()
    return usuario


class KpiSinGestionarObjetivosEspecificosTests(APITestCase):
    def setUp(self):
        self.admin = crear_usuario('admin_bloque_a', 'Administrador de planificación')
        self.client.force_authenticate(user=self.admin)

        for nombre, color in [('Incumplido', 'rojo'), ('En riesgo', 'amarillo'), ('Favorable', 'verde')]:
            EstadoCumplimiento.objects.get_or_create(nombre=nombre, defaults={'color': color, 'estado': True})

        self.frecuencia = Frecuencia.objects.create(nombre='Mensual', estado=True)
        plan = PlanEstrategico.objects.create(
            titulo='Plan bloque A', fecha_inicio=date(2027, 1, 1), fecha_fin=date(2030, 12, 31),
            estado=PlanEstrategico.ESTADO_EN_USO, creado_por=self.admin,
        )
        self.objetivo_general = ObjetivoGeneral.objects.create(
            plan_estrategico=plan, texto_objetivo='Mejorar la cartera', creado_por=self.admin,
        )
        self.plan_anual = PlanAnual.objects.create(
            plan_estrategico=plan, anio=2027, estado=PlanAnual.ESTADO_EN_USO,
            fecha_inicio=date(2027, 1, 1), fecha_fin=date(2027, 12, 31), creado_por=self.admin,
        )

    def datos(self, nombre, **extra):
        return {
            'plan_anual': self.plan_anual.id,
            'objetivo_general': self.objetivo_general.id,
            'objetivo_especifico': None,
            'frecuencia': self.frecuencia.id,
            'nombre': nombre,
            'descripcion': '',
            'formula_medicion': 'Cobros / cartera * 100',
            'unidad_medida': '%',
            'valor_meta': '85',
            'ponderacion': '',
            **extra,
        }

    def test_crear_kpi_sin_objetivo_especifico_usa_el_implicito(self):
        response = self.client.post(URL, self.datos('KPI sin objetivo específico'), format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        kpi = IndicadorKPI.objects.get(pk=response.data['id'])
        self.assertTrue(kpi.objetivo_especifico.es_generado_automaticamente)
        self.assertEqual(kpi.plan_anual, self.plan_anual)
        self.assertEqual(kpi.objetivo_general, self.objetivo_general)
        self.assertTrue(response.data['es_directo'])
        self.assertEqual(response.data['objetivo_general_texto'], 'Mejorar la cartera')

        # Un segundo KPI reutiliza el mismo objetivo implícito.
        otro = self.client.post(URL, self.datos('Otro KPI'), format='json')
        self.assertEqual(IndicadorKPI.objects.get(pk=otro.data['id']).objetivo_especifico, kpi.objetivo_especifico)
        self.assertEqual(ObjetivoEspecifico.objects.filter(es_generado_automaticamente=True).count(), 1)

    def test_editar_un_kpi_con_objetivo_especifico_real_conserva_el_vinculo(self):
        real = ObjetivoEspecifico.objects.create(
            plan_anual=self.plan_anual, objetivo_general=self.objetivo_general,
            texto_objetivo='Objetivo específico registrado antes', creado_por=self.admin,
        )
        kpi = IndicadorKPI.objects.create(
            objetivo_especifico=real, frecuencia=self.frecuencia, nombre='KPI histórico',
            formula_medicion='R', unidad_medida='%', valor_meta=Decimal('85'), estado='borrador',
            creado_por=self.admin,
        )

        # Lo que envía el formulario sin selector: el objetivo que ya tenía.
        response = self.client.patch(
            f'{URL}{kpi.id}/', self.datos('KPI histórico editado', objetivo_especifico=real.id), format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        kpi.refresh_from_db()
        self.assertEqual(kpi.objetivo_especifico, real)
        self.assertEqual(kpi.nombre, 'KPI histórico editado')
        self.assertFalse(response.data['es_directo'])
        self.assertEqual(response.data['objetivo_especifico_texto'], 'Objetivo específico registrado antes')

    def test_consultar_kpi_expone_su_objetivo(self):
        creado = self.client.post(URL, self.datos('KPI consultado'), format='json')

        detalle = self.client.get(f'{URL}{creado.data["id"]}/').data
        listado = self.client.get(URL).data

        self.assertEqual(detalle['objetivo_general_texto'], 'Mejorar la cartera')
        self.assertEqual([k['id'] for k in listado], [creado.data['id']])

    def test_la_api_de_objetivos_especificos_se_conserva(self):
        self.assertEqual(self.client.get('/api/objetivos-especificos/').status_code, status.HTTP_200_OK)
