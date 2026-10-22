"""D2: evidencias múltiples por medición.

Cada archivo es un EvidenciaMedicion independiente que se conserva; uno
nuevo nunca reemplaza ni borra a los anteriores. Usa un MEDIA_ROOT temporal
fuera del proyecto (no toca backend/media)."""

import importlib
import shutil
import tempfile
from datetime import date
from unittest import mock

from django.apps import apps as apps_actuales
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import override_settings
from django.test.utils import CaptureQueriesContext
from rest_framework import status
from rest_framework.test import APITransactionTestCase

from apps.auditoria.models import Bitacora
from apps.estrategia.models import PlanAnual

from .models import EvidenciaMedicion, Medicion
from .services import cerrar_mediciones_vencidas
from .tests import MedicionTestsBase, crear_usuario_admin

_MEDIA_ROOT_D2 = tempfile.mkdtemp(prefix='sniff_d2_evidencias_')

PDF = b'%PDF-1.4 contenido de prueba'
ENERO = date(2027, 1, 31)
FEBRERO = date(2027, 2, 28)

migracion_0018 = importlib.import_module('apps.indicadores.migrations.0018_migrar_evidencias_heredadas')


def pdf(nombre='respaldo.pdf', contenido=PDF):
    return SimpleUploadedFile(nombre, contenido, content_type='application/pdf')


class EvidenciasBase(MedicionTestsBase):
    NOMBRE_USUARIO = 'ejecutor_d2'

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(_MEDIA_ROOT_D2, ignore_errors=True)

    def registrar(self, kpi, fecha=ENERO, **extra):
        datos = {'indicador': kpi.id, 'valor_resultado': '50', **extra}

        with mock.patch('apps.indicadores.services.hoy', return_value=fecha):
            return self.client.post('/api/mediciones/', datos, format='multipart')

    def agregar(self, medicion_id, archivos):
        return self.client.post(
            f'/api/mediciones/{medicion_id}/evidencias/',
            {'archivos': archivos},
            format='multipart',
        )


@override_settings(MEDIA_ROOT=_MEDIA_ROOT_D2)
class CargaDeEvidenciasTests(EvidenciasBase):

    def test_registrar_con_un_archivo(self):
        response = self.registrar(self.crear_kpi(), archivos_evidencia=[pdf()])

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data['cantidad_evidencias'], 1)
        self.assertEqual(response.data['evidencias'][0]['nombre_original'], 'respaldo.pdf')
        self.assertEqual(response.data['evidencias'][0]['subido_por_username'], self.usuario.username)
        self.assertTrue(response.data['tiene_evidencia'])

    def test_registrar_con_varios_archivos(self):
        archivos = [pdf('a.pdf'), pdf('b.pdf'), SimpleUploadedFile('c.jpg', b'img', content_type='image/jpeg')]
        response = self.registrar(self.crear_kpi(), archivos_evidencia=archivos)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        medicion = Medicion.objects.get(id=response.data['id'])
        self.assertEqual(
            list(medicion.evidencias.values_list('nombre_original', flat=True)),
            ['a.pdf', 'b.pdf', 'c.jpg'],
        )
        # El campo heredado ya no se escribe.
        self.assertFalse(medicion.evidencia)

    def test_campo_evidencia_unico_sigue_admitido(self):
        response = self.registrar(self.crear_kpi(), evidencia=pdf('unico.pdf'))

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data['cantidad_evidencias'], 1)
        self.assertFalse(Medicion.objects.get(id=response.data['id']).evidencia)

    def test_registrar_sin_evidencia_sigue_permitido(self):
        response = self.registrar(self.crear_kpi())

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['cantidad_evidencias'], 0)
        self.assertFalse(response.data['tiene_evidencia'])

    def test_agregar_posteriormente_conserva_las_anteriores(self):
        medicion_id = self.registrar(self.crear_kpi(), archivos_evidencia=[pdf('primera.pdf')]).data['id']
        primera = EvidenciaMedicion.objects.get(medicion_id=medicion_id)
        ruta_primera = primera.archivo.name

        response = self.agregar(medicion_id, [pdf('segunda.pdf'), pdf('tercera.pdf')])

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(len(response.data), 2)
        primera.refresh_from_db()
        self.assertEqual(primera.archivo.name, ruta_primera)
        self.assertTrue(default_storage.exists(ruta_primera))
        self.assertEqual(EvidenciaMedicion.objects.filter(medicion_id=medicion_id).count(), 3)

    def test_patch_con_archivos_agrega_y_no_reemplaza(self):
        medicion_id = self.registrar(self.crear_kpi(), archivos_evidencia=[pdf('primera.pdf')]).data['id']

        response = self.client.patch(
            f'/api/mediciones/{medicion_id}/',
            {'archivos_evidencia': [pdf('otra.pdf')]},
            format='multipart',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(
            [e['nombre_original'] for e in response.data['evidencias']],
            ['primera.pdf', 'otra.pdf'],
        )

    def test_tipos_no_permitidos_rechazados(self):
        medicion_id = self.registrar(self.crear_kpi()).data['id']

        for nombre, tipo in [
            ('informe.docx', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'),
            ('datos.xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
            ('imagen.png', 'image/png'),
            ('falso.pdf', 'text/html'),
        ]:
            response = self.agregar(medicion_id, [SimpleUploadedFile(nombre, b'x', content_type=tipo)])
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, nombre)

        self.assertEqual(EvidenciaMedicion.objects.count(), 0)

    def test_archivo_mayor_a_10_mb_rechazado(self):
        medicion_id = self.registrar(self.crear_kpi()).data['id']

        response = self.agregar(medicion_id, [pdf('grande.pdf', b'0' * (10 * 1024 * 1024 + 1))])

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(EvidenciaMedicion.objects.count(), 0)

    def test_un_archivo_invalido_rechaza_toda_la_carga(self):
        medicion_id = self.registrar(self.crear_kpi()).data['id']

        response = self.agregar(medicion_id, [pdf('bueno.pdf'), SimpleUploadedFile('malo.exe', b'x')])

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(EvidenciaMedicion.objects.count(), 0)

    def test_maximo_10_archivos_por_operacion(self):
        kpi = self.crear_kpi()
        response = self.registrar(kpi, archivos_evidencia=[pdf(f'{i}.pdf') for i in range(11)])
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Medicion.objects.filter(indicador=kpi).count(), 0)

        medicion_id = self.registrar(kpi, archivos_evidencia=[pdf(f'{i}.pdf') for i in range(10)]).data['id']
        self.assertEqual(EvidenciaMedicion.objects.filter(medicion_id=medicion_id).count(), 10)

        response = self.agregar(medicion_id, [pdf(f'extra{i}.pdf') for i in range(11)])
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Sin límite acumulado: otra carga de 10 se suma.
        response = self.agregar(medicion_id, [pdf(f'extra{i}.pdf') for i in range(10)])
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(EvidenciaMedicion.objects.filter(medicion_id=medicion_id).count(), 20)

    def test_agregar_sin_archivos_rechazado(self):
        medicion_id = self.registrar(self.crear_kpi()).data['id']

        response = self.client.post(f'/api/mediciones/{medicion_id}/evidencias/', {}, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_nombres_peligrosos_y_colisiones(self):
        medicion_id = self.registrar(self.crear_kpi()).data['id']

        response = self.agregar(medicion_id, [
            pdf('../../../settings.pdf'),
            pdf('informe final <script>.pdf'),
            pdf('mismo.pdf', b'%PDF uno'),
            pdf('mismo.pdf', b'%PDF dos'),
        ])

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        evidencias = list(EvidenciaMedicion.objects.filter(medicion_id=medicion_id))
        rutas = [e.archivo.name for e in evidencias]

        self.assertEqual(len(set(rutas)), 4)

        for ruta in rutas:
            self.assertTrue(ruta.startswith('evidencias/mediciones/'), ruta)
            self.assertNotIn('..', ruta)
            self.assertNotIn('<', ruta)
            self.assertTrue(default_storage.exists(ruta))

        mismos = [e for e in evidencias if e.nombre_original == 'mismo.pdf']
        self.assertEqual(
            sorted(e.archivo.read() for e in mismos),
            [b'%PDF dos', b'%PDF uno'],
        )


@override_settings(MEDIA_ROOT=_MEDIA_ROOT_D2)
class ConsultaYPermisosTests(EvidenciasBase):

    def setUp(self):
        super().setUp()
        self.admin_sistema = crear_usuario_admin('d2_admin_sistema', rol_nombre='Administrador del sistema')
        self.admin_planificacion = crear_usuario_admin('d2_admin_plan', rol_nombre='Administrador de planificación')
        self.consulta = crear_usuario_admin('d2_consulta', rol_nombre='Usuario de consulta')

        response = self.registrar(self.crear_kpi(), archivos_evidencia=[pdf('informe mensual.pdf')])
        self.medicion_id = response.data['id']
        self.evidencia = EvidenciaMedicion.objects.get(medicion_id=self.medicion_id)

    def url(self, modo):
        return f'/api/mediciones/{self.medicion_id}/evidencias/{self.evidencia.id}/{modo}/'

    def test_los_cuatro_roles_consultan_ven_y_descargan(self):
        for usuario in (self.usuario, self.admin_sistema, self.admin_planificacion, self.consulta):
            self.client.force_authenticate(user=usuario)

            listado = self.client.get(f'/api/mediciones/{self.medicion_id}/evidencias/')
            self.assertEqual(listado.status_code, status.HTTP_200_OK, usuario.username)
            self.assertEqual(listado.data[0]['nombre_original'], 'informe mensual.pdf')

            ver = self.client.get(self.url('ver'))
            self.assertEqual(ver.status_code, status.HTTP_200_OK, usuario.username)
            self.assertTrue(ver['Content-Disposition'].startswith('inline'))
            self.assertEqual(b''.join(ver.streaming_content), PDF)

            descargar = self.client.get(self.url('descargar'))
            self.assertEqual(descargar.status_code, status.HTTP_200_OK, usuario.username)
            self.assertTrue(descargar['Content-Disposition'].startswith('attachment'))
            self.assertIn('informe', descargar['Content-Disposition'])

    def test_anonimo_no_accede(self):
        self.client.force_authenticate(user=None)

        for url in (f'/api/mediciones/{self.medicion_id}/evidencias/', self.url('ver'), self.url('descargar')):
            self.assertIn(
                self.client.get(url).status_code,
                (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
            )

    def test_solo_ejecutor_adjunta(self):
        for usuario in (self.admin_sistema, self.admin_planificacion, self.consulta):
            self.client.force_authenticate(user=usuario)
            response = self.agregar(self.medicion_id, [pdf('intento.pdf')])
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, usuario.username)

        self.client.force_authenticate(user=self.usuario)
        self.assertEqual(self.agregar(self.medicion_id, [pdf('ok.pdf')]).status_code, status.HTTP_201_CREATED)
        self.assertEqual(EvidenciaMedicion.objects.filter(medicion_id=self.medicion_id).count(), 2)

    def test_evidencia_de_otra_medicion_da_404(self):
        with mock.patch('apps.indicadores.services.hoy', return_value=FEBRERO):
            otra_id = self.client.post(
                '/api/mediciones/', {'indicador': self.evidencia.medicion.indicador_id, 'valor_resultado': '60'},
            ).data['id']

        response = self.client.get(f'/api/mediciones/{otra_id}/evidencias/{self.evidencia.id}/ver/')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_ruta_heredada_sirve_la_mas_reciente(self):
        self.agregar(self.medicion_id, [pdf('nueva.pdf', b'%PDF nueva')])

        response = self.client.get(f'/api/mediciones/{self.medicion_id}/evidencia/descargar/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(b''.join(response.streaming_content), b'%PDF nueva')

    def test_no_se_eliminan_ni_reemplazan(self):
        ruta = self.evidencia.archivo.name

        with self.assertRaises(ValidationError):
            self.evidencia.delete()

        # DELETE lo frena primero PermisoMedicion (403); PUT/PATCH no existen (405).
        bloqueado = (status.HTTP_403_FORBIDDEN, status.HTTP_405_METHOD_NOT_ALLOWED)

        for metodo in (self.client.delete, self.client.put, self.client.patch):
            response = metodo(f'/api/mediciones/{self.medicion_id}/evidencias/')
            self.assertIn(response.status_code, bloqueado)

        self.assertIn(self.client.delete(self.url('ver')).status_code, bloqueado)
        self.assertTrue(EvidenciaMedicion.objects.filter(id=self.evidencia.id).exists())
        self.assertTrue(default_storage.exists(ruta))

    def test_bitacora_por_archivo(self):
        antes = Bitacora.objects.filter(modulo='Evidencias').count()

        self.agregar(self.medicion_id, [pdf('uno.pdf'), pdf('dos.pdf')])

        registros = Bitacora.objects.filter(modulo='Evidencias').order_by('id')
        self.assertEqual(registros.count(), antes + 2)
        ultimo = registros.last()
        self.assertEqual(ultimo.usuario, self.usuario)
        self.assertIn('dos.pdf', ultimo.descripcion)
        self.assertIn(f'#{self.medicion_id}', ultimo.descripcion)


@override_settings(MEDIA_ROOT=_MEDIA_ROOT_D2)
class RestriccionesTests(EvidenciasBase):

    def test_plan_cerrado_no_admite_evidencias(self):
        medicion_id = self.registrar(self.crear_kpi()).data['id']

        self.plan_anual.estado = PlanAnual.ESTADO_CERRADO
        self.plan_anual.save(update_fields=['estado'])

        response = self.agregar(medicion_id, [pdf()])
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Cerrados', str(response.data))

        response = self.client.patch(
            f'/api/mediciones/{medicion_id}/', {'archivos_evidencia': [pdf()]}, format='multipart',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(EvidenciaMedicion.objects.count(), 0)

        # La consulta sigue disponible.
        self.assertEqual(
            self.client.get(f'/api/mediciones/{medicion_id}/evidencias/').status_code, status.HTTP_200_OK,
        )

    def test_cierre_automatico_no_admite_evidencias(self):
        kpi = self.crear_kpi()

        with mock.patch('apps.indicadores.services.hoy', return_value=date(2027, 2, 6)):
            cerrar_mediciones_vencidas()

        omision = Medicion.objects.get(indicador=kpi, cierre_automatico=True)

        response = self.agregar(omision.id, [pdf()])

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('cerrado automáticamente', str(response.data))
        self.assertEqual(EvidenciaMedicion.objects.count(), 0)


@override_settings(MEDIA_ROOT=_MEDIA_ROOT_D2)
class RendimientoListadoTests(EvidenciasBase):

    def contar_consultas_listado(self):
        with CaptureQueriesContext(connection) as contexto:
            response = self.client.get('/api/mediciones/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return len(contexto.captured_queries)

    def test_consultas_no_crecen_con_las_evidencias(self):
        kpi = self.crear_kpi()
        enero = self.registrar(kpi).data['id']
        febrero = self.registrar(kpi, fecha=FEBRERO).data['id']

        sin_evidencias = self.contar_consultas_listado()

        for medicion_id in (enero, febrero):
            self.agregar(medicion_id, [pdf(f'{i}.pdf') for i in range(4)])

        self.assertEqual(self.contar_consultas_listado(), sin_evidencias)


@override_settings(MEDIA_ROOT=_MEDIA_ROOT_D2)
class MigracionEvidenciasHeredadasTests(EvidenciasBase):
    """0018 sobre datos de prueba: misma ruta, sin duplicar, reversible y
    sin tocar los archivos."""

    def crear_medicion_heredada(self, fecha=ENERO, contenido=b'%PDF heredada'):
        medicion = Medicion.objects.get(id=self.registrar(self.crear_kpi(nombre=f'KPI {fecha}'), fecha=fecha).data['id'])
        ruta = default_storage.save('evidencias/mediciones/2026/09/heredada.pdf', ContentFile(contenido))
        Medicion.objects.filter(id=medicion.id).update(evidencia=ruta)
        medicion.refresh_from_db()
        return medicion, ruta

    def test_migra_referencias_sin_copiar_ni_duplicar(self):
        medicion, ruta = self.crear_medicion_heredada()
        sin_evidencia = Medicion.objects.get(id=self.registrar(self.crear_kpi(nombre='KPI sin')).data['id'])
        archivos_antes = sorted(default_storage.listdir('evidencias/mediciones/2026/09')[1])

        migracion_0018.migrar_evidencias(apps_actuales, None)
        migracion_0018.migrar_evidencias(apps_actuales, None)

        evidencia = EvidenciaMedicion.objects.get(medicion=medicion)
        self.assertEqual(evidencia.archivo.name, ruta)
        self.assertEqual(evidencia.nombre_original, 'heredada.pdf')
        self.assertEqual(evidencia.tamano, len(b'%PDF heredada'))
        self.assertEqual(evidencia.tipo_contenido, 'application/pdf')
        self.assertEqual(evidencia.subido_por_id, medicion.registrado_por_id)
        self.assertEqual(evidencia.fecha_subida, medicion.fecha_registro)
        self.assertFalse(sin_evidencia.evidencias.exists())
        self.assertEqual(sorted(default_storage.listdir('evidencias/mediciones/2026/09')[1]), archivos_antes)

        # La medición migrada se ve y descarga por las rutas nuevas.
        response = self.client.get(f'/api/mediciones/{medicion.id}/evidencias/{evidencia.id}/descargar/')
        self.assertEqual(b''.join(response.streaming_content), b'%PDF heredada')
        self.assertEqual(self.client.get(f'/api/mediciones/{medicion.id}/').data['cantidad_evidencias'], 1)

    def test_revertir_quita_solo_las_filas_migradas_y_conserva_archivos(self):
        medicion, ruta = self.crear_medicion_heredada()
        migracion_0018.migrar_evidencias(apps_actuales, None)
        self.agregar(medicion.id, [pdf('nueva.pdf')])
        nueva = EvidenciaMedicion.objects.get(medicion=medicion, nombre_original='nueva.pdf')

        migracion_0018.revertir(apps_actuales, None)

        self.assertEqual(list(EvidenciaMedicion.objects.filter(medicion=medicion)), [nueva])
        self.assertTrue(default_storage.exists(ruta))
        self.assertTrue(default_storage.exists(nueva.archivo.name))
        medicion.refresh_from_db()
        self.assertEqual(medicion.evidencia.name, ruta)


@override_settings(MEDIA_ROOT=_MEDIA_ROOT_D2)
class MigracionIdaYVueltaTests(APITransactionTestCase):
    """0017/0018 aplicadas de verdad sobre la base de pruebas: se revierten
    hasta 0016 y se vuelven a aplicar, con una medición heredada."""

    NOMBRE_USUARIO = 'ejecutor_d2_migracion'
    setUp = MedicionTestsBase.setUp
    crear_kpi = MedicionTestsBase.crear_kpi

    def migrar(self, destino):
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate([('indicadores', destino)])

    def test_revertir_y_reaplicar(self):
        with mock.patch('apps.indicadores.services.hoy', return_value=ENERO):
            medicion_id = self.client.post(
                '/api/mediciones/', {'indicador': self.crear_kpi().id, 'valor_resultado': '50'},
            ).data['id']

        ruta = default_storage.save('evidencias/mediciones/2026/09/ida_vuelta.pdf', ContentFile(b'%PDF ida'))
        Medicion.objects.filter(id=medicion_id).update(evidencia=ruta)

        try:
            self.migrar('0016_solicitud_ampliacion_plazo')
            self.assertNotIn('evidencia_medicion', connection.introspection.table_names())
            self.assertTrue(default_storage.exists(ruta))

            self.migrar('0018_migrar_evidencias_heredadas')
        finally:
            self.migrar('0018_migrar_evidencias_heredadas')

        evidencias = list(EvidenciaMedicion.objects.filter(medicion_id=medicion_id))
        self.assertEqual([e.archivo.name for e in evidencias], [ruta])
        self.assertEqual(Medicion.objects.get(id=medicion_id).evidencia.name, ruta)
        self.assertTrue(default_storage.exists(ruta))
