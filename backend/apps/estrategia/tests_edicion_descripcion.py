from datetime import date

from rest_framework.test import APITestCase

from .models import PlanEstrategico
from .tests import crear_usuario_admin


class EdicionDescripcionPlanTests(APITestCase):
    def setUp(self):
        self.usuario = crear_usuario_admin('prueba_descripcion')
        self.client.force_authenticate(self.usuario)
        self.plan = PlanEstrategico.objects.create(
            titulo='Plan de prueba', descripcion='Original',
            fecha_inicio=date(2026, 1, 1), fecha_fin=date(2026, 12, 31),
            estado='en_uso', creado_por=self.usuario,
        )
        self.url = f'/api/planes-estrategicos/{self.plan.pk}/'

    def comprobar_inmutables(self):
        self.plan.refresh_from_db()
        self.assertEqual(self.plan.titulo, 'Plan de prueba')
        self.assertEqual(self.plan.fecha_inicio, date(2026, 1, 1))
        self.assertEqual(self.plan.fecha_fin, date(2026, 12, 31))
        self.assertEqual(self.plan.estado, 'en_uso')

    def test_descripcion_persiste_y_se_consulta(self):
        response = self.client.patch(self.url, {'descripcion': 'Actualizada'}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.comprobar_inmutables()
        self.assertEqual(self.plan.descripcion, 'Actualizada')
        self.assertEqual(self.client.get(self.url).data['descripcion'], 'Actualizada')

    def test_descripcion_igual_o_vacia_es_valida(self):
        for valor in ('Original', ''):
            with self.subTest(valor=valor):
                response = self.client.patch(self.url, {'descripcion': valor}, format='json')
                self.assertEqual(response.status_code, 200, response.data)
                self.comprobar_inmutables()
                self.assertEqual(self.plan.descripcion, valor)

    def test_titulo_y_fechas_se_rechazan_sin_guardar_descripcion(self):
        for campo, valor in (('titulo', 'Otro'), ('fecha_inicio', '2026-02-01'),
                             ('fecha_fin', '2026-11-30'), ('fecha_inicio', None),
                             ('fecha_fin', None), ('titulo', 'Plan de prueba')):
            with self.subTest(campo=campo, valor=valor):
                response = self.client.patch(self.url, {campo: valor, 'descripcion': 'Prohibida'}, format='json')
                self.assertEqual(response.status_code, 400, response.data)
                self.comprobar_inmutables()
                self.assertEqual(self.plan.descripcion, 'Original')

    def test_cerrado_rechaza_descripcion(self):
        self.plan.estado = 'cerrado'
        self.plan.save(update_fields=['estado'])
        response = self.client.patch(self.url, {'descripcion': 'Prohibida'}, format='json')
        self.assertEqual(response.status_code, 400)
        self.plan.refresh_from_db()
        self.assertEqual(self.plan.descripcion, 'Original')

    def test_borrador_permite_titulo_y_fechas(self):
        self.plan.estado = 'borrador'
        self.plan.save(update_fields=['estado'])
        response = self.client.patch(self.url, {'titulo': 'Nuevo', 'fecha_inicio': '2026-02-01'}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.plan.refresh_from_db()
        self.assertEqual(self.plan.titulo, 'Nuevo')
        self.assertEqual(self.plan.fecha_inicio, date(2026, 2, 1))
