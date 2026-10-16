from rest_framework import status
from rest_framework.test import APITestCase

from apps.usuarios.models import Rol, Usuario

from .models import (
    ObjetivoEspecifico,
    ObjetivoGeneral,
    PlanAnual,
    PlanEstrategico,
    PonderacionAnualObjetivoGeneral,
)


def crear_usuario_admin(username):
    # Bloque 2: estas pruebas ejercitan CRUD de Plan/Objetivo (vía API) —
    # dominio exclusivo de Administrador de planificación bajo los 4 roles
    # definitivos (Administrador del sistema ya no gestiona planificación).
    rol, _ = Rol.objects.get_or_create(
        nombre='Administrador de planificación',
        defaults={'descripcion': 'Rol de prueba', 'estado': True},
    )

    usuario = Usuario.objects.create_user(username=username, password='clave-prueba-123')
    usuario.rol = rol
    usuario.correo = f'{username}@sniff.test'
    usuario.save()

    return usuario


class PlanAnualTests(APITestCase):
    """Bloque 2 - casos 1 a 12 del plan de pruebas."""

    def setUp(self):
        self.usuario = crear_usuario_admin('admin_plan_anual')
        self.client.force_authenticate(user=self.usuario)

        self.plan_borrador = PlanEstrategico.objects.create(
            titulo='Plan Borrador',
            fecha_inicio='2027-01-01',
            fecha_fin='2030-12-31',
            creado_por=self.usuario,
        )

        self.plan_en_uso = PlanEstrategico.objects.create(
            titulo='Plan En Uso',
            fecha_inicio='2027-01-01',
            fecha_fin='2030-12-31',
            estado=PlanEstrategico.ESTADO_EN_USO,
            creado_por=self.usuario,
        )

        self.plan_cerrado = PlanEstrategico.objects.create(
            titulo='Plan Cerrado',
            fecha_inicio='2027-01-01',
            fecha_fin='2030-12-31',
            estado=PlanEstrategico.ESTADO_CERRADO,
            creado_por=self.usuario,
        )

    # 1. Plan nuevo nace Borrador.
    def test_plan_anual_nace_borrador(self):
        response = self.client.post('/api/planes-anuales/', {
            'plan_estrategico': self.plan_en_uso.id,
            'anio': 2027,
            'fecha_inicio': '2027-01-01',
            'fecha_fin': '2027-12-31',
        })

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['estado'], PlanAnual.ESTADO_BORRADOR)

    # 2. Solo puede crearse sobre PlanEstrategico En uso.
    def test_no_se_crea_sobre_plan_estrategico_borrador(self):
        response = self.client.post('/api/planes-anuales/', {
            'plan_estrategico': self.plan_borrador.id,
            'anio': 2027,
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_no_se_crea_sobre_plan_estrategico_cerrado(self):
        response = self.client.post('/api/planes-anuales/', {
            'plan_estrategico': self.plan_cerrado.id,
            'anio': 2027,
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # 3. Año dentro de rango → permitido.
    def test_anio_dentro_de_rango_permitido(self):
        response = self.client.post('/api/planes-anuales/', {
            'plan_estrategico': self.plan_en_uso.id,
            'anio': 2029,
            'fecha_inicio': '2029-01-01',
            'fecha_fin': '2029-12-31',
        })

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    # 4. Año fuera de rango → rechazado.
    def test_anio_fuera_de_rango_rechazado(self):
        response = self.client.post('/api/planes-anuales/', {
            'plan_estrategico': self.plan_en_uso.id,
            'anio': 2031,
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # 5. Año duplicado mismo Plan → rechazado.
    def test_anio_duplicado_mismo_plan_rechazado(self):
        primera = self.client.post('/api/planes-anuales/', {
            'plan_estrategico': self.plan_en_uso.id,
            'anio': 2027,
            'fecha_inicio': '2027-01-01',
            'fecha_fin': '2027-12-31',
        })
        self.assertEqual(primera.status_code, status.HTTP_201_CREATED)

        response = self.client.post('/api/planes-anuales/', {
            'plan_estrategico': self.plan_en_uso.id,
            'anio': 2027,
            'fecha_inicio': '2027-01-01',
            'fecha_fin': '2027-12-31',
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # 6. Mismo año en diferente Plan → permitido.
    def test_mismo_anio_en_diferente_plan_permitido(self):
        plan_en_uso_b = PlanEstrategico.objects.create(
            titulo='Plan En Uso B',
            fecha_inicio='2027-01-01',
            fecha_fin='2030-12-31',
            estado=PlanEstrategico.ESTADO_EN_USO,
            creado_por=self.usuario,
        )

        self.client.post('/api/planes-anuales/', {
            'plan_estrategico': self.plan_en_uso.id,
            'anio': 2027,
            'fecha_inicio': '2027-01-01',
            'fecha_fin': '2027-12-31',
        })

        response = self.client.post('/api/planes-anuales/', {
            'plan_estrategico': plan_en_uso_b.id,
            'anio': 2027,
            'fecha_inicio': '2027-01-01',
            'fecha_fin': '2027-12-31',
        })

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    # 7. Borrador → En uso.
    def test_transicion_borrador_a_en_uso(self):
        plan_anual = PlanAnual.objects.create(
            plan_estrategico=self.plan_en_uso, anio=2027, creado_por=self.usuario,
        )

        response = self.client.post(f'/api/planes-anuales/{plan_anual.id}/poner-en-uso/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        plan_anual.refresh_from_db()
        self.assertEqual(plan_anual.estado, PlanAnual.ESTADO_EN_USO)

    # 8. En uso → Cerrado.
    def test_transicion_en_uso_a_cerrado(self):
        plan_anual = PlanAnual.objects.create(
            plan_estrategico=self.plan_en_uso,
            anio=2027,
            estado=PlanAnual.ESTADO_EN_USO,
            creado_por=self.usuario,
        )

        response = self.client.post(f'/api/planes-anuales/{plan_anual.id}/cerrar/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        plan_anual.refresh_from_db()
        self.assertEqual(plan_anual.estado, PlanAnual.ESTADO_CERRADO)

    # 9. Borrador → Cerrado directo rechazado.
    def test_borrador_a_cerrado_directo_rechazado(self):
        plan_anual = PlanAnual.objects.create(
            plan_estrategico=self.plan_en_uso, anio=2027, creado_por=self.usuario,
        )

        response = self.client.post(f'/api/planes-anuales/{plan_anual.id}/cerrar/')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        plan_anual.refresh_from_db()
        self.assertEqual(plan_anual.estado, PlanAnual.ESTADO_BORRADOR)

    # 10. Cerrado no retorna (ni a en_uso, ni editable).
    def test_cerrado_no_retorna(self):
        plan_anual = PlanAnual.objects.create(
            plan_estrategico=self.plan_en_uso,
            anio=2027,
            estado=PlanAnual.ESTADO_CERRADO,
            creado_por=self.usuario,
        )

        response_en_uso = self.client.post(f'/api/planes-anuales/{plan_anual.id}/poner-en-uso/')
        self.assertEqual(response_en_uso.status_code, status.HTTP_400_BAD_REQUEST)

        response_patch = self.client.patch(f'/api/planes-anuales/{plan_anual.id}/', {'anio': 2028})
        self.assertEqual(response_patch.status_code, status.HTTP_400_BAD_REQUEST)

    # 11. DELETE rechazado.
    def test_delete_rechazado(self):
        plan_anual = PlanAnual.objects.create(
            plan_estrategico=self.plan_en_uso, anio=2027, creado_por=self.usuario,
        )

        response = self.client.delete(f'/api/planes-anuales/{plan_anual.id}/')

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    # 12. Plan estratégico Cerrado bloquea su Plan anual.
    def test_plan_estrategico_cerrado_bloquea_plan_anual(self):
        plan_anual = PlanAnual.objects.create(
            plan_estrategico=self.plan_en_uso,
            anio=2027,
            estado=PlanAnual.ESTADO_EN_USO,
            creado_por=self.usuario,
        )

        self.plan_en_uso.estado = PlanEstrategico.ESTADO_CERRADO
        self.plan_en_uso.save(update_fields=['estado'])

        response_cerrar = self.client.post(f'/api/planes-anuales/{plan_anual.id}/cerrar/')
        self.assertEqual(response_cerrar.status_code, status.HTTP_400_BAD_REQUEST)

        response_patch = self.client.patch(f'/api/planes-anuales/{plan_anual.id}/', {'anio': 2028})
        self.assertEqual(response_patch.status_code, status.HTTP_400_BAD_REQUEST)

    # --- Corrección Hernán bloque 1: fechas de vigencia ---

    # 13. Crear un plan anual con fechas válidas.
    def test_crear_plan_anual_con_fechas_validas(self):
        response = self.client.post('/api/planes-anuales/', {
            'plan_estrategico': self.plan_en_uso.id,
            'anio': 2028,
            'fecha_inicio': '2028-01-01',
            'fecha_fin': '2028-12-31',
        })

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['fecha_inicio'], '2028-01-01')
        self.assertEqual(response.data['fecha_fin'], '2028-12-31')

    # 14. Fechas obligatorias en creación.
    def test_fechas_obligatorias_en_creacion(self):
        response = self.client.post('/api/planes-anuales/', {
            'plan_estrategico': self.plan_en_uso.id,
            'anio': 2028,
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('fecha_inicio', response.data)

    # 15. Fecha de inicio posterior a la de finalización → rechazada.
    def test_fecha_inicio_posterior_a_fin_rechazada(self):
        response = self.client.post('/api/planes-anuales/', {
            'plan_estrategico': self.plan_en_uso.id,
            'anio': 2028,
            'fecha_inicio': '2028-12-31',
            'fecha_fin': '2028-01-01',
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('fecha_fin', response.data)

    # 16. Fechas fuera de la vigencia del Plan estratégico → rechazadas.
    def test_fechas_fuera_de_vigencia_plan_estrategico_rechazadas(self):
        # self.plan_en_uso tiene vigencia 2027-01-01 a 2030-12-31.
        response = self.client.post('/api/planes-anuales/', {
            'plan_estrategico': self.plan_en_uso.id,
            'anio': 2027,
            'fecha_inicio': '2026-06-01',
            'fecha_fin': '2027-12-31',
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('fecha_inicio', response.data)

    # 17. Fechas que no corresponden al año seleccionado → rechazadas.
    def test_fechas_no_coherentes_con_anio_rechazadas(self):
        response = self.client.post('/api/planes-anuales/', {
            'plan_estrategico': self.plan_en_uso.id,
            'anio': 2028,
            'fecha_inicio': '2027-01-01',
            'fecha_fin': '2027-12-31',
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('fecha_inicio', response.data)

    # 18. Un registro existente sin fechas sigue disponible (transición segura).
    def test_plan_anual_existente_sin_fechas_sigue_disponible(self):
        plan_sin_fechas = PlanAnual.objects.create(
            plan_estrategico=self.plan_en_uso, anio=2027, creado_por=self.usuario,
        )

        response = self.client.get(f'/api/planes-anuales/{plan_sin_fechas.id}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data['fecha_inicio'])
        self.assertIsNone(response.data['fecha_fin'])

    # --- Corrección Hernán bloque 1: un solo Plan anual En uso ---

    # 19. Activar un plan anual cuando no existe otro En uso.
    def test_activar_plan_anual_sin_otro_en_uso(self):
        plan_anual = PlanAnual.objects.create(
            plan_estrategico=self.plan_en_uso,
            anio=2027,
            fecha_inicio='2027-01-01',
            fecha_fin='2027-12-31',
            creado_por=self.usuario,
        )

        response = self.client.post(f'/api/planes-anuales/{plan_anual.id}/poner-en-uso/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        plan_anual.refresh_from_db()
        self.assertEqual(plan_anual.estado, PlanAnual.ESTADO_EN_USO)

    # 20a. Dos Planes estratégicos DIFERENTES SÍ pueden tener, cada uno,
    #      su propio Plan anual En uso al mismo tiempo (corrección: la
    #      regla es POR plan estratégico, no global).
    def test_dos_estrategias_diferentes_permiten_plan_anual_en_uso_simultaneo(self):
        otro_plan_estrategico = PlanEstrategico.objects.create(
            titulo='Otro Plan En Uso',
            fecha_inicio='2027-01-01',
            fecha_fin='2030-12-31',
            estado=PlanEstrategico.ESTADO_EN_USO,
            creado_por=self.usuario,
        )

        PlanAnual.objects.create(
            plan_estrategico=self.plan_en_uso,
            anio=2027,
            fecha_inicio='2027-01-01',
            fecha_fin='2027-12-31',
            estado=PlanAnual.ESTADO_EN_USO,
            creado_por=self.usuario,
        )

        plan_candidato = PlanAnual.objects.create(
            plan_estrategico=otro_plan_estrategico,
            anio=2027,
            fecha_inicio='2027-01-01',
            fecha_fin='2027-12-31',
            creado_por=self.usuario,
        )

        response = self.client.post(f'/api/planes-anuales/{plan_candidato.id}/poner-en-uso/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        plan_candidato.refresh_from_db()
        self.assertEqual(plan_candidato.estado, PlanAnual.ESTADO_EN_USO)

    # 20b. Impedir activar un segundo Plan anual si otro ya está En uso
    #      DENTRO DE LA MISMA estrategia.
    def test_impedir_segundo_plan_anual_en_uso_misma_estrategia(self):
        plan_activo = PlanAnual.objects.create(
            plan_estrategico=self.plan_en_uso,
            anio=2027,
            fecha_inicio='2027-01-01',
            fecha_fin='2027-12-31',
            estado=PlanAnual.ESTADO_EN_USO,
            creado_por=self.usuario,
        )

        plan_candidato = PlanAnual.objects.create(
            plan_estrategico=self.plan_en_uso,
            anio=2028,
            fecha_inicio='2028-01-01',
            fecha_fin='2028-12-31',
            creado_por=self.usuario,
        )

        response = self.client.post(f'/api/planes-anuales/{plan_candidato.id}/poner-en-uso/')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(plan_activo.nombre, response.data['detail'])
        plan_candidato.refresh_from_db()
        self.assertEqual(plan_candidato.estado, PlanAnual.ESTADO_BORRADOR)

    # 21. Cerrar el Plan anual activo y luego activar otro.
    def test_cerrar_activo_y_luego_activar_otro(self):
        plan_activo = PlanAnual.objects.create(
            plan_estrategico=self.plan_en_uso,
            anio=2027,
            fecha_inicio='2027-01-01',
            fecha_fin='2027-12-31',
            estado=PlanAnual.ESTADO_EN_USO,
            creado_por=self.usuario,
        )

        plan_candidato = PlanAnual.objects.create(
            plan_estrategico=self.plan_en_uso,
            anio=2028,
            fecha_inicio='2028-01-01',
            fecha_fin='2028-12-31',
            creado_por=self.usuario,
        )

        respuesta_bloqueada = self.client.post(f'/api/planes-anuales/{plan_candidato.id}/poner-en-uso/')
        self.assertEqual(respuesta_bloqueada.status_code, status.HTTP_400_BAD_REQUEST)

        respuesta_cerrar = self.client.post(f'/api/planes-anuales/{plan_activo.id}/cerrar/')
        self.assertEqual(respuesta_cerrar.status_code, status.HTTP_200_OK)

        respuesta_activar = self.client.post(f'/api/planes-anuales/{plan_candidato.id}/poner-en-uso/')
        self.assertEqual(respuesta_activar.status_code, status.HTTP_200_OK)
        plan_candidato.refresh_from_db()
        self.assertEqual(plan_candidato.estado, PlanAnual.ESTADO_EN_USO)


class ObjetivoEspecificoTests(APITestCase):
    """Bloque 2 - casos 13 a 20 del plan de pruebas."""

    def setUp(self):
        self.usuario = crear_usuario_admin('admin_objetivo_especifico')
        self.client.force_authenticate(user=self.usuario)

        self.plan_a = PlanEstrategico.objects.create(
            titulo='Plan A',
            fecha_inicio='2027-01-01',
            fecha_fin='2030-12-31',
            estado=PlanEstrategico.ESTADO_EN_USO,
            creado_por=self.usuario,
        )

        self.plan_b = PlanEstrategico.objects.create(
            titulo='Plan B',
            fecha_inicio='2027-01-01',
            fecha_fin='2030-12-31',
            estado=PlanEstrategico.ESTADO_EN_USO,
            creado_por=self.usuario,
        )

        self.objetivo_general_a = ObjetivoGeneral.objects.create(
            plan_estrategico=self.plan_a, texto_objetivo='Objetivo general A', creado_por=self.usuario,
        )

        self.objetivo_general_b = ObjetivoGeneral.objects.create(
            plan_estrategico=self.plan_b, texto_objetivo='Objetivo general B', creado_por=self.usuario,
        )

        self.plan_anual_en_uso = PlanAnual.objects.create(
            plan_estrategico=self.plan_a, anio=2027, estado=PlanAnual.ESTADO_EN_USO, creado_por=self.usuario,
        )

        self.plan_anual_borrador = PlanAnual.objects.create(
            plan_estrategico=self.plan_a, anio=2028, creado_por=self.usuario,
        )

        self.plan_anual_cerrado = PlanAnual.objects.create(
            plan_estrategico=self.plan_a, anio=2029, estado=PlanAnual.ESTADO_CERRADO, creado_por=self.usuario,
        )

    # 13. Solo puede crearse en PlanAnual En uso.
    def test_se_crea_en_plan_anual_en_uso(self):
        response = self.client.post('/api/objetivos-especificos/', {
            'plan_anual': self.plan_anual_en_uso.id,
            'objetivo_general': self.objetivo_general_a.id,
            'texto_objetivo': 'Aumentar la recuperación de cartera en 2027.',
        })

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    # 14. PlanAnual Borrador → rechazado.
    def test_plan_anual_borrador_rechazado(self):
        response = self.client.post('/api/objetivos-especificos/', {
            'plan_anual': self.plan_anual_borrador.id,
            'objetivo_general': self.objetivo_general_a.id,
            'texto_objetivo': 'Texto sobre plan en borrador.',
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # 15. PlanAnual Cerrado → rechazado.
    def test_plan_anual_cerrado_rechazado(self):
        response = self.client.post('/api/objetivos-especificos/', {
            'plan_anual': self.plan_anual_cerrado.id,
            'objetivo_general': self.objetivo_general_a.id,
            'texto_objetivo': 'Texto sobre plan cerrado.',
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # 16. ObjetivoGeneral debe pertenecer al mismo PlanEstrategico.
    def test_objetivo_general_de_otro_plan_estrategico_rechazado(self):
        response = self.client.post('/api/objetivos-especificos/', {
            'plan_anual': self.plan_anual_en_uso.id,
            'objetivo_general': self.objetivo_general_b.id,
            'texto_objetivo': 'Texto cruzado entre planes.',
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # 17. Texto editable mientras PlanAnual En uso.
    def test_texto_editable_mientras_plan_anual_en_uso(self):
        objetivo = ObjetivoEspecifico.objects.create(
            plan_anual=self.plan_anual_en_uso,
            objetivo_general=self.objetivo_general_a,
            texto_objetivo='Texto original.',
            creado_por=self.usuario,
        )

        response = self.client.patch(
            f'/api/objetivos-especificos/{objetivo.id}/', {'texto_objetivo': 'Texto editado.'}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        objetivo.refresh_from_db()
        self.assertEqual(objetivo.texto_objetivo, 'Texto editado.')

    # 18. Bloqueado si PlanAnual Cerrado.
    def test_bloqueado_si_plan_anual_cerrado(self):
        objetivo = ObjetivoEspecifico.objects.create(
            plan_anual=self.plan_anual_cerrado,
            objetivo_general=self.objetivo_general_a,
            texto_objetivo='Texto original.',
            creado_por=self.usuario,
        )

        response = self.client.patch(
            f'/api/objetivos-especificos/{objetivo.id}/', {'texto_objetivo': 'Intento de edición.'}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # 19. Bloqueado si PlanEstrategico Cerrado.
    def test_bloqueado_si_plan_estrategico_cerrado(self):
        objetivo = ObjetivoEspecifico.objects.create(
            plan_anual=self.plan_anual_en_uso,
            objetivo_general=self.objetivo_general_a,
            texto_objetivo='Texto original.',
            creado_por=self.usuario,
        )

        self.plan_a.estado = PlanEstrategico.ESTADO_CERRADO
        self.plan_a.save(update_fields=['estado'])

        response = self.client.patch(
            f'/api/objetivos-especificos/{objetivo.id}/', {'texto_objetivo': 'Intento de edición.'}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # 20. DELETE rechazado.
    def test_delete_rechazado(self):
        objetivo = ObjetivoEspecifico.objects.create(
            plan_anual=self.plan_anual_en_uso,
            objetivo_general=self.objetivo_general_a,
            texto_objetivo='Texto original.',
            creado_por=self.usuario,
        )

        response = self.client.delete(f'/api/objetivos-especificos/{objetivo.id}/')

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


def crear_usuario_ejecutor(username):
    rol, _ = Rol.objects.get_or_create(
        nombre='Ejecutor operativo',
        defaults={'descripcion': 'Rol de prueba', 'estado': True},
    )

    usuario = Usuario.objects.create_user(username=username, password='clave-prueba-123')
    usuario.rol = rol
    usuario.correo = f'{username}@sniff.test'
    usuario.save()

    return usuario


class PonderacionAnualObjetivoGeneralTests(APITestCase):
    """Bloque 3, segunda parte: ponderación anual de un objetivo general
    (reglas 1/2/3 confirmadas por Hernán, reunión del 6/10/2026)."""

    def setUp(self):
        self.usuario = crear_usuario_admin('admin_ponderacion_anual')
        self.client.force_authenticate(user=self.usuario)

        self.plan_estrategico = PlanEstrategico.objects.create(
            titulo='Plan estratégico ponderación',
            fecha_inicio='2027-01-01',
            fecha_fin='2031-12-31',
            estado=PlanEstrategico.ESTADO_EN_USO,
            creado_por=self.usuario,
        )

        self.objetivo_general = ObjetivoGeneral.objects.create(
            plan_estrategico=self.plan_estrategico,
            texto_objetivo='Objetivo general ponderación',
            creado_por=self.usuario,
        )

        self.anios = {}
        for anio in (2027, 2028, 2029, 2030, 2031):
            self.anios[anio] = PlanAnual.objects.create(
                plan_estrategico=self.plan_estrategico,
                anio=anio,
                creado_por=self.usuario,
            )

    def crear_ponderacion(self, anio, porcentaje, objetivo_general=None):
        return self.client.post('/api/ponderaciones-anuales/', {
            'objetivo_general': (objetivo_general or self.objetivo_general).id,
            'plan_anual': self.anios[anio].id,
            'porcentaje': porcentaje,
        })

    # 1. Registro de porcentajes válidos.
    def test_registra_porcentaje_valido(self):
        response = self.crear_ponderacion(2027, '10.00')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(str(response.data['porcentaje']), '10.00')

    # 2. Rechazo de valores negativos o superiores a 100.
    def test_rechaza_porcentaje_negativo(self):
        response = self.crear_ponderacion(2027, '-5.00')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rechaza_porcentaje_mayor_a_100(self):
        response = self.crear_ponderacion(2027, '150.00')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # 3. Rechazo de distribuciones que superen el 100%.
    def test_rechaza_distribucion_que_supera_100(self):
        self.crear_ponderacion(2027, '60.00')
        response = self.crear_ponderacion(2028, '50.00')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # 4. Aceptación de distribuciones parciales durante su preparación.
    def test_acepta_distribucion_parcial_en_preparacion(self):
        response = self.crear_ponderacion(2027, '10.00')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(str(response.data['total_asignado_objetivo_general']), '10.00')
        self.assertEqual(str(response.data['pendiente_objetivo_general']), '90.00')

    # 5. Identificación de una distribución que alcance exactamente el 100%.
    def test_identifica_distribucion_completa_al_100(self):
        self.crear_ponderacion(2027, '10.00')
        self.crear_ponderacion(2028, '30.00')
        self.crear_ponderacion(2029, '20.00')
        self.crear_ponderacion(2030, '30.00')
        respuesta_final = self.crear_ponderacion(2031, '10.00')

        self.assertEqual(respuesta_final.status_code, status.HTTP_201_CREATED)
        self.assertEqual(str(respuesta_final.data['total_asignado_objetivo_general']), '100.00')
        self.assertEqual(str(respuesta_final.data['pendiente_objetivo_general']), '0.00')

        from apps.estrategia.services import resumen_ponderacion_anual
        resumen = resumen_ponderacion_anual(self.objetivo_general)
        self.assertTrue(resumen['completo'])

    # 6. Independencia entre planes estratégicos distintos.
    def test_independencia_entre_planes_estrategicos_distintos(self):
        otro_plan_estrategico = PlanEstrategico.objects.create(
            titulo='Otro plan estratégico ponderación',
            fecha_inicio='2027-01-01',
            fecha_fin='2027-12-31',
            estado=PlanEstrategico.ESTADO_EN_USO,
            creado_por=self.usuario,
        )
        otro_objetivo_general = ObjetivoGeneral.objects.create(
            plan_estrategico=otro_plan_estrategico,
            texto_objetivo='Objetivo general de otro plan',
            creado_por=self.usuario,
        )
        otro_plan_anual = PlanAnual.objects.create(
            plan_estrategico=otro_plan_estrategico,
            anio=2027,
            creado_por=self.usuario,
        )

        self.crear_ponderacion(2027, '90.00')

        respuesta_otro = self.client.post('/api/ponderaciones-anuales/', {
            'objetivo_general': otro_objetivo_general.id,
            'plan_anual': otro_plan_anual.id,
            'porcentaje': '90.00',
        })

        self.assertEqual(respuesta_otro.status_code, status.HTTP_201_CREATED)

    # Validación de pertenencia: el plan anual debe ser del mismo plan
    # estratégico que el objetivo general.
    def test_rechaza_plan_anual_de_otro_plan_estrategico(self):
        otro_plan_estrategico = PlanEstrategico.objects.create(
            titulo='Plan estratégico ajeno',
            fecha_inicio='2027-01-01',
            fecha_fin='2027-12-31',
            estado=PlanEstrategico.ESTADO_EN_USO,
            creado_por=self.usuario,
        )
        plan_anual_ajeno = PlanAnual.objects.create(
            plan_estrategico=otro_plan_estrategico,
            anio=2027,
            creado_por=self.usuario,
        )

        response = self.client.post('/api/ponderaciones-anuales/', {
            'objetivo_general': self.objetivo_general.id,
            'plan_anual': plan_anual_ajeno.id,
            'porcentaje': '10.00',
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # No se duplica una fila para el mismo (objetivo_general, plan_anual).
    def test_rechaza_fila_duplicada_para_mismo_objetivo_y_anio(self):
        self.crear_ponderacion(2027, '10.00')
        response = self.crear_ponderacion(2027, '20.00')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # Bloqueado si el Plan anual (o su Plan estratégico) está Cerrado —
    # funcionamiento de las reglas del Bloque 1.
    def test_bloqueado_si_plan_anual_cerrado(self):
        self.anios[2027].estado = PlanAnual.ESTADO_CERRADO
        self.anios[2027].save(update_fields=['estado'])

        response = self.crear_ponderacion(2027, '10.00')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # 9. Restricción de edición al Administrador de planificación —
    # funcionamiento de los permisos del Bloque 2.
    def test_restringido_a_administrador_de_planificacion(self):
        ejecutor = crear_usuario_ejecutor('ejecutor_ponderacion_anual')
        self.client.force_authenticate(user=ejecutor)

        response = self.crear_ponderacion(2027, '10.00')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # Consulta libre para cualquier autenticado (Bloque 2: PermisoEstrategiaObjetivo).
    def test_consulta_libre_para_cualquier_autenticado(self):
        self.crear_ponderacion(2027, '10.00')
        ejecutor = crear_usuario_ejecutor('ejecutor_consulta_ponderacion')
        self.client.force_authenticate(user=ejecutor)

        response = self.client.get('/api/ponderaciones-anuales/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
