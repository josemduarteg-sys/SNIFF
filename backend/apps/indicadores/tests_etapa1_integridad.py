"""Etapa 1 de correcciones post-auditoría (20/10/2026): ponderación de KPI
anulados (M1), transiciones de estado del KPI (M2) y eliminación de
mediciones, evidencias, alertas y catálogos (M3)."""

import shutil
import tempfile
from datetime import date
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from apps.auditoria.models import Bitacora, Notificacion
from apps.estrategia.models import Area, ObjetivoEspecifico, ObjetivoGeneral, PlanAnual, PlanEstrategico
from apps.integraciones.models import ArchivoImportado
from apps.usuarios.models import Rol, Usuario

from .models import (
    Alerta,
    EstadoCumplimiento,
    Frecuencia,
    IndicadorKPI,
    Medicion,
    MetaKPI,
    PeriodoMedicion,
    RangoKPI,
    ResponsableKPI,
)
from .services import (
    crear_rangos_provisionales,
    obtener_estado_para_medicion,
    obtener_o_crear_meta_vigente,
    obtener_o_crear_periodo,
    resumen_ponderacion_kpi_ambito,
)

_MEDIA_ROOT_PRUEBAS = tempfile.mkdtemp(prefix='sniff_etapa1_tests_')


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


class Etapa1Base(APITestCase):
    def setUp(self):
        self.admin_planificacion = crear_usuario('admin_planif_e1', 'Administrador de planificación')
        self.ejecutor = crear_usuario('ejecutor_e1', 'Ejecutor operativo')
        self.consulta = crear_usuario('consulta_e1', 'Usuario de consulta')
        self.admin_sistema = crear_usuario('admin_sistema_e1', 'Administrador del sistema')
        self.client.force_authenticate(user=self.admin_planificacion)

        for nombre, color in [('Incumplido', 'rojo'), ('En riesgo', 'amarillo'), ('Favorable', 'verde')]:
            EstadoCumplimiento.objects.get_or_create(nombre=nombre, defaults={'color': color, 'estado': True})

        self.frecuencia = Frecuencia.objects.create(nombre='Mensual', estado=True)

        self.plan_estrategico = PlanEstrategico.objects.create(
            titulo='Plan etapa 1',
            fecha_inicio=date(2027, 1, 1),
            fecha_fin=date(2030, 12, 31),
            estado=PlanEstrategico.ESTADO_EN_USO,
            creado_por=self.admin_planificacion,
        )
        self.objetivo_general = ObjetivoGeneral.objects.create(
            plan_estrategico=self.plan_estrategico,
            texto_objetivo='Objetivo general etapa 1',
            creado_por=self.admin_planificacion,
        )
        self.plan_anual = PlanAnual.objects.create(
            plan_estrategico=self.plan_estrategico,
            anio=2027,
            estado=PlanAnual.ESTADO_EN_USO,
            creado_por=self.admin_planificacion,
        )
        self.objetivo_especifico = ObjetivoEspecifico.objects.create(
            plan_anual=self.plan_anual,
            objetivo_general=self.objetivo_general,
            texto_objetivo='Objetivo específico etapa 1',
            creado_por=self.admin_planificacion,
        )

    def crear_kpi(self, nombre, estado='autorizado', ponderacion=None):
        kpi = IndicadorKPI.objects.create(
            objetivo_especifico=self.objetivo_especifico,
            frecuencia=self.frecuencia,
            nombre=nombre,
            formula_medicion='Resultado / Meta x 100',
            unidad_medida='%',
            valor_meta=Decimal('85'),
            ponderacion=ponderacion,
            estado=estado,
            creado_por=self.admin_planificacion,
        )
        crear_rangos_provisionales(kpi)
        return kpi

    def crear_medicion(self, kpi, valor='80', evidencia=None):
        periodo = obtener_o_crear_periodo(kpi, date(2027, 1, 1))
        meta = obtener_o_crear_meta_vigente(kpi)

        return Medicion.objects.create(
            indicador=kpi,
            meta=meta,
            periodo=periodo,
            estado_cumplimiento=obtener_estado_para_medicion(kpi, meta, Decimal(valor)),
            registrado_por=self.ejecutor,
            fecha_medicion=periodo.fecha_fin,
            valor_resultado=Decimal(valor),
            evidencia=evidencia,
        )


class PonderacionKpiAnuladoTests(Etapa1Base):
    """M1: un KPI anulado conserva su ponderación histórica pero no consume
    porcentaje de la distribución vigente."""

    def url(self, kpi):
        return f'/api/indicadores-kpi/{kpi.id}/'

    def test_resumen_excluye_kpi_anulado(self):
        self.crear_kpi('KPI vigente', ponderacion=Decimal('30'))
        self.crear_kpi('KPI anulado', estado='anulado', ponderacion=Decimal('60'))

        resumen = resumen_ponderacion_kpi_ambito(self.plan_anual, self.objetivo_general)

        self.assertEqual(resumen['total_asignado'], Decimal('30'))
        self.assertEqual(resumen['pendiente'], Decimal('70'))

    def test_anular_libera_porcentaje_sin_borrar_la_ponderacion_historica(self):
        kpi_a = self.crear_kpi('KPI A', ponderacion=Decimal('60'))
        self.crear_kpi('KPI B', ponderacion=Decimal('30'))
        kpi_c = self.crear_kpi('KPI C')

        antes = self.client.patch(self.url(kpi_c), {'ponderacion': '70.00'})
        self.assertEqual(antes.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertEqual(self.client.post(f'{self.url(kpi_a)}anular/').status_code, status.HTTP_200_OK)

        despues = self.client.patch(self.url(kpi_c), {'ponderacion': '70.00'})
        self.assertEqual(despues.status_code, status.HTTP_200_OK)

        kpi_a.refresh_from_db()
        self.assertEqual(kpi_a.estado, 'anulado')
        self.assertEqual(kpi_a.ponderacion, Decimal('60'))

    def test_serializer_de_kpi_anulado_no_suma_su_propia_ponderacion(self):
        self.crear_kpi('KPI vigente', ponderacion=Decimal('30'))
        anulado = self.crear_kpi('KPI anulado', estado='anulado', ponderacion=Decimal('60'))

        data = self.client.get(self.url(anulado)).data

        self.assertEqual(Decimal(str(data['ponderacion'])), Decimal('60'))
        self.assertEqual(Decimal(str(data['ponderacion_total_ambito'])), Decimal('30'))
        self.assertEqual(Decimal(str(data['ponderacion_pendiente_ambito'])), Decimal('70'))

    def test_ponderacion_de_kpi_anulado_no_puede_modificarse(self):
        anulado = self.crear_kpi('KPI anulado', estado='anulado', ponderacion=Decimal('60'))

        response = self.client.patch(self.url(anulado), {'ponderacion': '10.00'})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('ponderacion', response.data)
        anulado.refresh_from_db()
        self.assertEqual(anulado.ponderacion, Decimal('60'))

    def test_reenviar_la_misma_ponderacion_de_kpi_anulado_no_es_error(self):
        anulado = self.crear_kpi('KPI anulado', estado='anulado', ponderacion=Decimal('60'))

        response = self.client.patch(self.url(anulado), {'ponderacion': '60.00'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_kpi_borrador_sigue_consumiendo_porcentaje(self):
        self.crear_kpi('KPI borrador', estado='borrador', ponderacion=Decimal('50'))
        nuevo = self.crear_kpi('KPI nuevo')

        response = self.client.patch(self.url(nuevo), {'ponderacion': '60.00'})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class TransicionesKpiTests(Etapa1Base):
    """M2: Borrador -> Autorizado | Anulado; Autorizado -> Anulado; Anulado es terminal."""

    def test_no_se_puede_autorizar_un_kpi_anulado(self):
        kpi = self.crear_kpi('KPI anulado', estado='anulado')

        response = self.client.post(f'/api/indicadores-kpi/{kpi.id}/autorizar/')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        kpi.refresh_from_db()
        self.assertEqual(kpi.estado, 'anulado')
        self.assertIsNone(kpi.fecha_autorizacion)
        self.assertIsNone(kpi.autorizado_por)

    def test_anular_un_kpi_ya_anulado_responde_400_sin_duplicar_bitacora_ni_notificacion(self):
        kpi = self.crear_kpi('KPI anulado', estado='anulado')
        bitacoras = Bitacora.objects.count()
        notificaciones = Notificacion.objects.count()

        response = self.client.post(f'/api/indicadores-kpi/{kpi.id}/anular/')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Bitacora.objects.count(), bitacoras)
        self.assertEqual(Notificacion.objects.count(), notificaciones)

    def test_borrador_puede_autorizarse(self):
        kpi = self.crear_kpi('KPI borrador', estado='borrador')

        response = self.client.post(f'/api/indicadores-kpi/{kpi.id}/autorizar/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        kpi.refresh_from_db()
        self.assertEqual(kpi.estado, 'autorizado')

    def test_borrador_y_autorizado_pueden_anularse(self):
        for estado in ('borrador', 'autorizado'):
            kpi = self.crear_kpi(f'KPI {estado}', estado=estado)

            response = self.client.post(f'/api/indicadores-kpi/{kpi.id}/anular/')

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            kpi.refresh_from_db()
            self.assertEqual(kpi.estado, 'anulado')

    def test_anular_conserva_mediciones_historicas(self):
        kpi = self.crear_kpi('KPI con historia')
        medicion = self.crear_medicion(kpi)

        self.client.post(f'/api/indicadores-kpi/{kpi.id}/anular/')

        medicion.refresh_from_db()
        self.assertEqual(medicion.indicador_id, kpi.id)
        self.assertEqual(medicion.valor_resultado, Decimal('80'))

    def test_otros_roles_no_pueden_autorizar_ni_anular(self):
        kpi = self.crear_kpi('KPI borrador', estado='borrador')

        for usuario in (self.ejecutor, self.consulta, self.admin_sistema):
            self.client.force_authenticate(user=usuario)

            for accion in ('autorizar', 'anular'):
                response = self.client.post(f'/api/indicadores-kpi/{kpi.id}/{accion}/')
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        kpi.refresh_from_db()
        self.assertEqual(kpi.estado, 'borrador')


@override_settings(MEDIA_ROOT=_MEDIA_ROOT_PRUEBAS)
class EliminacionProtegidaTests(Etapa1Base):
    """M3: sin borrado físico de historial; respuestas controladas."""

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(_MEDIA_ROOT_PRUEBAS, ignore_errors=True)

    def setUp(self):
        super().setUp()
        self.kpi = self.crear_kpi('KPI con mediciones')
        evidencia = SimpleUploadedFile('respaldo.pdf', b'%PDF-1.4 prueba', content_type='application/pdf')
        self.medicion = self.crear_medicion(self.kpi, evidencia=evidencia)

    def test_ningun_rol_puede_eliminar_una_medicion(self):
        esperado = {
            self.admin_planificacion: status.HTTP_405_METHOD_NOT_ALLOWED,
            self.ejecutor: status.HTTP_403_FORBIDDEN,
            self.consulta: status.HTTP_403_FORBIDDEN,
            self.admin_sistema: status.HTTP_403_FORBIDDEN,
        }

        for usuario, codigo in esperado.items():
            self.client.force_authenticate(user=usuario)
            response = self.client.delete(f'/api/mediciones/{self.medicion.id}/')
            self.assertEqual(response.status_code, codigo, usuario.username)

        self.assertTrue(Medicion.objects.filter(id=self.medicion.id).exists())

    def test_la_evidencia_se_conserva(self):
        self.client.delete(f'/api/mediciones/{self.medicion.id}/')

        self.medicion.refresh_from_db()
        self.assertTrue(self.medicion.evidencia)
        self.assertTrue(self.medicion.evidencia.storage.exists(self.medicion.evidencia.name))

        self.client.force_authenticate(user=self.consulta)
        response = self.client.get(f'/api/mediciones/{self.medicion.id}/evidencia/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_la_edicion_de_mediciones_sigue_funcionando(self):
        self.client.force_authenticate(user=self.ejecutor)

        response = self.client.patch(f'/api/mediciones/{self.medicion.id}/', {'observacion': 'Ajuste'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_alerta_no_puede_eliminarse(self):
        alerta = Alerta.objects.create(
            indicador=self.kpi, medicion=self.medicion, tipo_alerta='KPI En riesgo', mensaje='Prueba',
        )

        response = self.client.delete(f'/api/alertas/{alerta.id}/')

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertTrue(Alerta.objects.filter(id=alerta.id).exists())

    def test_marcar_alerta_revisada_sigue_funcionando(self):
        alerta = Alerta.objects.create(indicador=self.kpi, tipo_alerta='KPI En riesgo', mensaje='Prueba')

        response = self.client.post(f'/api/alertas/{alerta.id}/marcar-revisada/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        alerta.refresh_from_db()
        self.assertEqual(alerta.estado_alerta, 'revisada')

    def test_catalogos_relacionados_no_admiten_delete(self):
        estado = EstadoCumplimiento.objects.get(nombre='Favorable')
        responsable = ResponsableKPI.objects.create(indicador=self.kpi, usuario=self.ejecutor)
        area = Area.objects.create(nombre='Área etapa 1')

        recursos = [
            ('rangos-kpi', RangoKPI, RangoKPI.objects.filter(indicador=self.kpi).first().id),
            ('metas-kpi', MetaKPI, self.medicion.meta_id),
            ('periodos-medicion', PeriodoMedicion, self.medicion.periodo_id),
            ('frecuencias', Frecuencia, self.frecuencia.id),
            ('estados-cumplimiento', EstadoCumplimiento, estado.id),
            ('responsables-kpi', ResponsableKPI, responsable.id),
            ('areas', Area, area.id),
        ]

        for ruta, modelo, pk in recursos:
            response = self.client.delete(f'/api/{ruta}/{pk}/')
            self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED, ruta)
            self.assertTrue(modelo.objects.filter(pk=pk).exists(), ruta)

    def test_catalogos_siguen_permitiendo_desactivacion_logica(self):
        area = Area.objects.create(nombre='Área a inactivar')

        response = self.client.patch(f'/api/areas/{area.id}/', {'estado': False})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        area.refresh_from_db()
        self.assertFalse(area.estado)

    def test_borrado_bloqueado_por_protect_responde_400_controlado(self):
        # Desde la Etapa 2 (A4) ningún endpoint expone ya un DELETE que
        # choque con PROTECT, así que el manejador global se prueba con el
        # ProtectedError real que Django lanza al intentar el borrado.
        from django.db.models import ProtectedError

        from config.exception_handler import manejador_excepciones

        archivo = ArchivoImportado.objects.create(
            nombre_archivo='carga.csv', importado_por=self.admin_planificacion,
        )
        Medicion.objects.filter(id=self.medicion.id).update(archivo_importado=archivo)

        from django.db import transaction

        with self.assertRaises(ProtectedError) as contexto:
            archivo.delete()

        # Etapa 4: el manejador revierte la transacción de la petición
        # (ATOMIC_REQUESTS); fuera de una petición se le da un bloque propio
        # para no revertir la transacción de esta prueba.
        with transaction.atomic():
            response = manejador_excepciones(contexto.exception, {})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('detail', response.data)
        self.assertTrue(ArchivoImportado.objects.filter(id=archivo.id).exists())
        self.assertTrue(Medicion.objects.filter(id=self.medicion.id).exists())

        # Y por la API ese borrado ya ni siquiera se ofrece.
        respuesta_api = self.client.delete(f'/api/archivos-importados/{archivo.id}/')
        self.assertIn(respuesta_api.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_405_METHOD_NOT_ALLOWED))
        self.assertTrue(ArchivoImportado.objects.filter(id=archivo.id).exists())
