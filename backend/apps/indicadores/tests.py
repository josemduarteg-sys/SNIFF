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
    def test_flujo_medicion_completo_no_rompe_por_cambio_de_fk(self):
        creado = self.client.post(
            '/api/indicadores-kpi/', self.payload_base(self.objetivo_especifico_en_uso.id)
        )
        kpi_id = creado.data['id']
        self.client.post(f'/api/indicadores-kpi/{kpi_id}/autorizar/')

        siguiente = self.client.get(
            '/api/mediciones/siguiente-periodo/', {'indicador': kpi_id}
        )
        self.assertEqual(siguiente.status_code, status.HTTP_200_OK)
        self.assertTrue(siguiente.data['disponible'])

        response_medicion = self.client.post('/api/mediciones/', {
            'indicador': kpi_id,
            'mes_medicion': siguiente.data['mes_medicion'],
            'valor_resultado': '90',
            'observacion': '',
            'evidencia': '',
        })

        self.assertEqual(response_medicion.status_code, status.HTTP_201_CREATED)
