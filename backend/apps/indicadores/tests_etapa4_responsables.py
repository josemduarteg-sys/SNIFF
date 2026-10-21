"""Etapa 4 (cierre): responsables de KPI (ResponsableKPI) y avisos
individuales de periodos pendientes y sin registro. Hallazgo M6."""

from datetime import date
from decimal import Decimal
from unittest import mock

from rest_framework import status
from rest_framework.test import APITestCase

from apps.auditoria.models import Bitacora, Notificacion
from apps.estrategia.models import ObjetivoEspecifico, ObjetivoGeneral, PlanAnual, PlanEstrategico
from apps.usuarios.models import Rol, Usuario

from .models import Alerta, EstadoCumplimiento, Frecuencia, IndicadorKPI, Medicion, ResponsableKPI
from .services import (
    TIPO_ALERTA_PERIODO_SIN_REGISTRO,
    TIPO_ALERTA_PERIODO_VENCIDO,
    cerrar_mediciones_vencidas,
    crear_rangos_provisionales,
    generar_alertas_periodos_vencidos,
)

URL = '/api/responsables-kpi/'


def crear_usuario(username, rol_nombre, **extra):
    rol, _ = Rol.objects.get_or_create(nombre=rol_nombre, defaults={'descripcion': 'Rol de prueba', 'estado': True})
    usuario = Usuario.objects.create_user(username=username, password='clave-prueba-123', **extra)
    usuario.rol = rol
    usuario.correo = f'{username}@sniff.test'
    usuario.save()
    return usuario


class ResponsablesBase(APITestCase):
    def setUp(self):
        self.admin = crear_usuario('admin_resp', 'Administrador de planificación')
        self.admin_sistema = crear_usuario('sistema_resp', 'Administrador del sistema')
        self.consulta = crear_usuario('consulta_resp', 'Usuario de consulta')
        self.ana = crear_usuario('ana_ejecutora', 'Ejecutor operativo', first_name='Ana', last_name='López')
        self.beto = crear_usuario('beto_ejecutor', 'Ejecutor operativo')
        self.otro = crear_usuario('otro_ejecutor', 'Ejecutor operativo')
        self.client.force_authenticate(user=self.admin)

        for nombre, color in [('Incumplido', 'rojo'), ('En riesgo', 'amarillo'), ('Favorable', 'verde')]:
            EstadoCumplimiento.objects.get_or_create(nombre=nombre, defaults={'color': color, 'estado': True})

        self.frecuencia = Frecuencia.objects.create(nombre='Mensual', estado=True)
        self.plan = PlanEstrategico.objects.create(
            titulo='Plan responsables', fecha_inicio=date(2027, 1, 1), fecha_fin=date(2030, 12, 31),
            estado=PlanEstrategico.ESTADO_EN_USO, creado_por=self.admin,
        )
        objetivo_general = ObjetivoGeneral.objects.create(plan_estrategico=self.plan, texto_objetivo='OG', creado_por=self.admin)
        self.plan_anual = PlanAnual.objects.create(
            plan_estrategico=self.plan, anio=2027, estado=PlanAnual.ESTADO_EN_USO,
            fecha_inicio=date(2027, 1, 1), fecha_fin=date(2027, 12, 31), creado_por=self.admin,
        )
        self.objetivo_especifico = ObjetivoEspecifico.objects.create(
            plan_anual=self.plan_anual, objetivo_general=objetivo_general, texto_objetivo='OE', creado_por=self.admin,
        )
        self.kpi = self.crear_kpi('KPI cartera')
        self.kpi2 = self.crear_kpi('KPI cobros')

    def crear_kpi(self, nombre, estado='autorizado'):
        kpi = IndicadorKPI.objects.create(
            objetivo_especifico=self.objetivo_especifico, frecuencia=self.frecuencia, nombre=nombre,
            formula_medicion='Resultado', unidad_medida='%', valor_meta=Decimal('85'),
            estado=estado, creado_por=self.admin,
        )
        crear_rangos_provisionales(kpi)
        return kpi

    def asignar(self, kpi, usuario):
        return self.client.post(URL, {'indicador': kpi.id, 'usuario': usuario.id}, format='json')

    def bitacoras(self):
        return list(Bitacora.objects.filter(modulo='Responsables KPI').order_by('id').values_list('accion', 'descripcion'))


class AsignacionResponsablesTests(ResponsablesBase):
    def test_asignar_responsable_y_registrar_en_bitacora(self):
        response = self.asignar(self.kpi, self.ana)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['estado'])
        self.assertEqual(response.data['usuario_nombre'], 'Ana López')
        self.assertEqual(self.bitacoras(), [('crear', 'Asignó a ana_ejecutora como responsable del KPI KPI cartera.')])
        self.assertEqual(Bitacora.objects.get(modulo='Responsables KPI').usuario, self.admin)

    def test_un_kpi_con_varios_responsables(self):
        self.asignar(self.kpi, self.ana)
        self.asignar(self.kpi, self.beto)

        listado = self.client.get(URL, {'indicador': self.kpi.id}).data
        kpi = self.client.get(f'/api/indicadores-kpi/{self.kpi.id}/').data

        self.assertEqual({r['usuario_username'] for r in listado}, {'ana_ejecutora', 'beto_ejecutor'})
        self.assertEqual(kpi['cantidad_responsables'], 2)

    def test_un_ejecutor_responsable_de_varios_kpi(self):
        self.assertEqual(self.asignar(self.kpi, self.ana).status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.asignar(self.kpi2, self.ana).status_code, status.HTTP_201_CREATED)

        self.assertEqual(ResponsableKPI.objects.filter(usuario=self.ana, estado=True).count(), 2)

    def test_no_duplica_una_asignacion_activa(self):
        self.asignar(self.kpi, self.ana)

        response = self.asignar(self.kpi, self.ana)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('ya es responsable', response.data['detail'])
        self.assertEqual(ResponsableKPI.objects.filter(indicador=self.kpi, usuario=self.ana).count(), 1)

    def test_desactivar_y_reactivar_sin_duplicar(self):
        asignacion_id = self.asignar(self.kpi, self.ana).data['id']

        desactivar = self.client.patch(f'{URL}{asignacion_id}/', {'estado': False}, format='json')
        reactivar = self.asignar(self.kpi, self.ana)

        self.assertEqual(desactivar.status_code, status.HTTP_200_OK)
        self.assertEqual(reactivar.status_code, status.HTTP_200_OK)
        self.assertEqual(reactivar.data['id'], asignacion_id)
        self.assertEqual(ResponsableKPI.objects.filter(indicador=self.kpi, usuario=self.ana).count(), 1)
        self.assertEqual([accion for accion, _ in self.bitacoras()], ['crear', 'eliminar', 'actualizar'])
        self.assertIn('Desactivó', self.bitacoras()[1][1])
        self.assertIn('Reactivó', self.bitacoras()[2][1])

    def test_reactivar_por_patch_tambien_valida(self):
        asignacion_id = self.asignar(self.kpi, self.ana).data['id']
        self.client.patch(f'{URL}{asignacion_id}/', {'estado': False}, format='json')
        Usuario.objects.filter(pk=self.ana.pk).update(is_active=False)

        response = self.client.patch(f'{URL}{asignacion_id}/', {'estado': True}, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(ResponsableKPI.objects.get(pk=asignacion_id).estado)

    def test_una_asignacion_no_cambia_de_kpi_ni_de_usuario(self):
        asignacion_id = self.asignar(self.kpi, self.ana).data['id']

        for payload in ({'usuario': self.beto.id}, {'indicador': self.kpi2.id}):
            response = self.client.patch(f'{URL}{asignacion_id}/', payload, format='json')
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        asignacion = ResponsableKPI.objects.get(pk=asignacion_id)
        self.assertEqual((asignacion.indicador_id, asignacion.usuario_id), (self.kpi.id, self.ana.id))

    def test_rechaza_usuarios_inactivos(self):
        inactivo = crear_usuario('ejecutor_inactivo', 'Ejecutor operativo', is_active=False)
        sin_estado = crear_usuario('ejecutor_sin_estado', 'Ejecutor operativo')
        Usuario.objects.filter(pk=sin_estado.pk).update(estado=False)

        for usuario in (inactivo, sin_estado):
            response = self.asignar(self.kpi, usuario)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, usuario.username)
            self.assertIn('usuario', response.data)

    def test_rechaza_roles_que_no_son_ejecutor_operativo(self):
        for usuario in (self.admin, self.admin_sistema, self.consulta):
            response = self.asignar(self.kpi, usuario)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, usuario.username)

        self.assertFalse(ResponsableKPI.objects.exists())

    def test_rechaza_kpi_anulado_y_planes_cerrados(self):
        anulado = self.crear_kpi('KPI anulado', estado='anulado')
        self.assertEqual(self.asignar(anulado, self.ana).status_code, status.HTTP_400_BAD_REQUEST)

        self.plan_anual.estado = PlanAnual.ESTADO_CERRADO
        self.plan_anual.save(update_fields=['estado'])
        self.assertEqual(self.asignar(self.kpi, self.ana).status_code, status.HTTP_400_BAD_REQUEST)

        self.plan_anual.estado = PlanAnual.ESTADO_EN_USO
        self.plan_anual.save(update_fields=['estado'])
        self.plan.estado = PlanEstrategico.ESTADO_CERRADO
        self.plan.save(update_fields=['estado'])
        self.assertEqual(self.asignar(self.kpi, self.ana).status_code, status.HTTP_400_BAD_REQUEST)

        self.assertFalse(ResponsableKPI.objects.exists())

    def test_se_puede_desactivar_en_un_kpi_que_luego_se_anulo(self):
        asignacion_id = self.asignar(self.kpi, self.ana).data['id']
        IndicadorKPI.objects.filter(pk=self.kpi.pk).update(estado='anulado')

        response = self.client.patch(f'{URL}{asignacion_id}/', {'estado': False}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_solo_admin_planificacion_gestiona_y_ve_candidatos(self):
        asignacion_id = self.asignar(self.kpi, self.ana).data['id']

        for usuario in (self.admin_sistema, self.consulta, self.ana):
            self.client.force_authenticate(user=usuario)
            self.assertEqual(self.asignar(self.kpi, self.beto).status_code, status.HTTP_403_FORBIDDEN)
            self.assertEqual(
                self.client.patch(f'{URL}{asignacion_id}/', {'estado': False}, format='json').status_code,
                status.HTTP_403_FORBIDDEN,
            )
            self.assertEqual(self.client.get(f'{URL}candidatos/').status_code, status.HTTP_403_FORBIDDEN)
            self.assertEqual(self.client.get(URL, {'indicador': self.kpi.id}).status_code, status.HTTP_200_OK)

        self.assertTrue(ResponsableKPI.objects.get(pk=asignacion_id).estado)

    def test_candidatos_son_solo_ejecutores_activos(self):
        crear_usuario('ejecutor_baja', 'Ejecutor operativo', is_active=False)

        nombres = {c['username'] for c in self.client.get(f'{URL}candidatos/').data}

        self.assertEqual(nombres, {'ana_ejecutora', 'beto_ejecutor', 'otro_ejecutor'})

    def test_kpi_sin_responsable(self):
        data = self.client.get(f'/api/indicadores-kpi/{self.kpi.id}/').data

        self.assertEqual(data['cantidad_responsables'], 0)

    def test_responsable_inactivado_deja_de_contar(self):
        self.asignar(self.kpi, self.ana)
        Usuario.objects.filter(pk=self.ana.pk).update(is_active=False)

        self.assertEqual(self.client.get(f'/api/indicadores-kpi/{self.kpi.id}/').data['cantidad_responsables'], 0)
        self.assertTrue(ResponsableKPI.objects.get(indicador=self.kpi, usuario=self.ana).estado)

    def test_fallo_de_bitacora_revierte_la_asignacion(self):
        with mock.patch('apps.auditoria.services.registrar_bitacora', side_effect=RuntimeError('BD caída')):
            response = self.asignar(self.kpi, self.ana)

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertFalse(ResponsableKPI.objects.exists())

    def test_las_restricciones_de_registro_de_mediciones_no_cambian(self):
        """Un Ejecutor sin asignación sigue pudiendo registrar mediciones."""
        self.asignar(self.kpi, self.ana)
        self.client.force_authenticate(user=self.otro)

        with mock.patch('apps.indicadores.services.hoy', return_value=date(2027, 1, 31)):
            response = self.client.post('/api/mediciones/', {'indicador': self.kpi.id, 'valor_resultado': '90'})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class NotificacionesResponsablesTests(ResponsablesBase):
    """Bloque A de la entrega (alcance del 06/10/2026): los avisos
    individuales a responsables de KPI se retiraron del flujo. Aunque existan
    asignaciones (el modelo y la API se conservan), las tareas de periodos ya
    no envían notificaciones por ellas; las alertas se siguen creando igual."""

    def setUp(self):
        super().setUp()
        self.asignar(self.kpi, self.ana)
        self.asignar(self.kpi, self.beto)

    def avisos_de_periodos(self):
        return Notificacion.objects.filter(tipo__in=('periodo_pendiente_registro', 'periodo_sin_registro'))

    def test_periodo_pendiente_crea_la_alerta_sin_avisos_individuales(self):
        generar_alertas_periodos_vencidos(fecha_referencia=date(2027, 2, 2))

        alerta = Alerta.objects.get(indicador=self.kpi, tipo_alerta=TIPO_ALERTA_PERIODO_VENCIDO)
        self.assertIn('hasta el 05/02/2027', alerta.mensaje)
        self.assertEqual(alerta.estado_alerta, 'pendiente')
        self.assertFalse(self.avisos_de_periodos().exists())

    def test_periodo_sin_registro_crea_la_alerta_sin_avisos_individuales(self):
        cerrar_mediciones_vencidas(fecha_referencia=date(2027, 2, 6))

        alerta = Alerta.objects.get(indicador=self.kpi, tipo_alerta=TIPO_ALERTA_PERIODO_SIN_REGISTRO)
        self.assertIn('quedó sin registro', alerta.mensaje)
        self.assertFalse(self.avisos_de_periodos().exists())

    def test_ningun_ejecutor_recibe_avisos_de_periodos(self):
        for _ in range(2):
            generar_alertas_periodos_vencidos(fecha_referencia=date(2027, 2, 2))
            cerrar_mediciones_vencidas(fecha_referencia=date(2027, 2, 6))

        for usuario in (self.ana, self.beto, self.otro):
            self.assertFalse(Notificacion.objects.filter(usuario_destino=usuario).exists())

        # Las alertas no se duplican al repetir los procesos.
        self.assertEqual(Alerta.objects.filter(indicador=self.kpi, tipo_alerta=TIPO_ALERTA_PERIODO_VENCIDO).count(), 1)
        self.assertEqual(Alerta.objects.filter(indicador=self.kpi, tipo_alerta=TIPO_ALERTA_PERIODO_SIN_REGISTRO).count(), 1)

    def test_las_asignaciones_se_conservan(self):
        generar_alertas_periodos_vencidos(fecha_referencia=date(2027, 2, 2))

        self.assertEqual(ResponsableKPI.objects.filter(indicador=self.kpi, estado=True).count(), 2)

    def test_avisos_no_cambian_mediciones_ni_resultados(self):
        cerrar_mediciones_vencidas(fecha_referencia=date(2027, 2, 6))

        omision = Medicion.objects.get(indicador=self.kpi)
        self.assertIsNone(omision.valor_resultado)
        self.assertEqual(omision.estado_cumplimiento.nombre, 'Sin registro')
