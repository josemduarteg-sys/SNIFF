"""D2: prueba de punta a punta de evidencias múltiples, por la API y con los
flujos reales del sistema (base de pruebas aislada, MEDIA_ROOT temporal).

1. El Administrador de planificación crea el KPI y lo autoriza.
2. El Ejecutor operativo registra la medición del periodo disponible con
   dos archivos.
3. Se consultan y descargan ambos; luego se agrega un tercero.
4. Los tres siguen disponibles, sin reemplazos; permisos y conteos.

La fecha "de hoy" del sistema se simula solo dentro del proceso de prueba
(mock de services.hoy); no se toca la fecha de Windows."""

import gc
import shutil
import tempfile
from datetime import date
from unittest import mock

from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from apps.estrategia.models import ObjetivoGeneral, PlanAnual, PlanEstrategico

from .models import EstadoCumplimiento, EvidenciaMedicion, Frecuencia, Medicion
from .tests import crear_usuario_admin

_MEDIA_ROOT = tempfile.mkdtemp(prefix='sniff_d2_flujo_')
HOY = date(2027, 1, 31)

PDF_UNO = b'%PDF-1.4 acta de cierre de enero'
JPG_DOS = b'\xff\xd8\xff\xe0 foto de la actividad'
PDF_TRES = b'%PDF-1.4 informe complementario'


@override_settings(MEDIA_ROOT=_MEDIA_ROOT)
class FlujoCompletoEvidenciasTests(APITestCase):

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        # Windows no borra un archivo que un FileResponse aún tiene abierto.
        gc.collect()
        shutil.rmtree(_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.planificacion = crear_usuario_admin('flujo_planificacion', rol_nombre='Administrador de planificación')
        self.ejecutor = crear_usuario_admin('flujo_ejecutor', rol_nombre='Ejecutor operativo')
        self.admin_sistema = crear_usuario_admin('flujo_sistema', rol_nombre='Administrador del sistema')
        self.consulta = crear_usuario_admin('flujo_consulta', rol_nombre='Usuario de consulta')

        for nombre, color in [('Incumplido', 'rojo'), ('En riesgo', 'amarillo'), ('Favorable', 'verde')]:
            EstadoCumplimiento.objects.get_or_create(nombre=nombre, defaults={'color': color, 'estado': True})

        self.frecuencia = Frecuencia.objects.create(nombre='Mensual', estado=True)
        plan = PlanEstrategico.objects.create(
            titulo='Plan flujo D2', fecha_inicio=date(2027, 1, 1), fecha_fin=date(2030, 12, 31),
            estado=PlanEstrategico.ESTADO_EN_USO, creado_por=self.planificacion,
        )
        self.objetivo_general = ObjetivoGeneral.objects.create(
            plan_estrategico=plan, texto_objetivo='Mejorar el seguimiento', creado_por=self.planificacion,
        )
        self.plan_anual = PlanAnual.objects.create(
            plan_estrategico=plan, anio=2027, estado=PlanAnual.ESTADO_EN_USO,
            fecha_inicio=date(2027, 1, 1), fecha_fin=date(2027, 12, 31), creado_por=self.planificacion,
        )

    def como(self, usuario):
        self.client.force_authenticate(user=usuario)

    def test_flujo_completo(self):
        # 1. KPI creado y autorizado por el Administrador de planificación.
        self.como(self.planificacion)

        with mock.patch('apps.indicadores.services.hoy', return_value=date(2027, 1, 5)):
            creado = self.client.post('/api/indicadores-kpi/', {
                'plan_anual': self.plan_anual.id, 'objetivo_general': self.objetivo_general.id,
                'objetivo_especifico': None, 'frecuencia': self.frecuencia.id,
                'nombre': 'Cumplimiento de actividades', 'descripcion': '',
                'formula_medicion': 'Realizadas / programadas x 100', 'unidad_medida': '%',
                'valor_meta': '90', 'ponderacion': '',
            }, format='json')
            self.assertEqual(creado.status_code, status.HTTP_201_CREATED, creado.data)
            kpi_id = creado.data['id']

            autorizado = self.client.post(f'/api/indicadores-kpi/{kpi_id}/autorizar/')
            self.assertEqual(autorizado.status_code, status.HTTP_200_OK, autorizado.data)

        # 2. El Ejecutor registra el periodo disponible con dos archivos.
        self.como(self.ejecutor)

        with mock.patch('apps.indicadores.services.hoy', return_value=HOY):
            periodo = self.client.get('/api/mediciones/siguiente-periodo/', {'indicador': kpi_id})
            self.assertTrue(periodo.data['disponible'], periodo.data)

            registro = self.client.post('/api/mediciones/', {
                'indicador': kpi_id,
                'valor_resultado': '82',
                'observacion': 'Registro con dos respaldos',
                'archivos_evidencia': [
                    SimpleUploadedFile('acta enero.pdf', PDF_UNO, content_type='application/pdf'),
                    SimpleUploadedFile('foto actividad.jpg', JPG_DOS, content_type='image/jpeg'),
                ],
            }, format='multipart')

        self.assertEqual(registro.status_code, status.HTTP_201_CREATED, registro.data)
        medicion_id = registro.data['id']
        # Mismo periodo que ofrecía siguiente-periodo (allí va en minúsculas).
        self.assertEqual(registro.data['periodo_nombre'].lower(), periodo.data['periodo_nombre'].lower())
        self.assertEqual(registro.data['cantidad_evidencias'], 2)

        primeras = {e['nombre_original']: e['id'] for e in registro.data['evidencias']}
        rutas_antes = dict(
            EvidenciaMedicion.objects.filter(medicion_id=medicion_id).values_list('id', 'archivo')
        )

        # 3. Ver y descargar ambos (contenido y nombre original).
        for nombre, contenido in (('acta enero.pdf', PDF_UNO), ('foto actividad.jpg', JPG_DOS)):
            base = f'/api/mediciones/{medicion_id}/evidencias/{primeras[nombre]}'

            ver = self.client.get(f'{base}/ver/')
            self.assertEqual(ver.status_code, status.HTTP_200_OK)
            self.assertTrue(ver['Content-Disposition'].startswith('inline'))
            self.assertEqual(b''.join(ver.streaming_content), contenido)

            descarga = self.client.get(f'{base}/descargar/')
            self.assertTrue(descarga['Content-Disposition'].startswith('attachment'))
            self.assertEqual(b''.join(descarga.streaming_content), contenido)

        # 4. Tercer archivo, después.
        tercero = self.client.post(
            f'/api/mediciones/{medicion_id}/evidencias/',
            {'archivos': [SimpleUploadedFile('informe.pdf', PDF_TRES, content_type='application/pdf')]},
            format='multipart',
        )
        self.assertEqual(tercero.status_code, status.HTTP_201_CREATED, tercero.data)

        # Los tres siguen disponibles; los dos primeros, intactos.
        detalle = self.client.get(f'/api/mediciones/{medicion_id}/')
        self.assertEqual(detalle.data['cantidad_evidencias'], 3)
        self.assertEqual(
            [e['nombre_original'] for e in detalle.data['evidencias']],
            ['acta enero.pdf', 'foto actividad.jpg', 'informe.pdf'],
        )

        for evidencia_id, ruta in rutas_antes.items():
            evidencia = EvidenciaMedicion.objects.get(id=evidencia_id)
            self.assertEqual(evidencia.archivo.name, ruta)
            self.assertTrue(default_storage.exists(ruta))

        self.assertEqual(
            b''.join(self.client.get(
                f'/api/mediciones/{medicion_id}/evidencias/{primeras["acta enero.pdf"]}/descargar/'
            ).streaming_content),
            PDF_UNO,
        )

        # Conteo en el listado (el que usa el Dashboard) y en el historial D5.
        listado = self.client.get('/api/mediciones/', {'indicador': kpi_id}).data
        listado = listado['results'] if isinstance(listado, dict) else listado
        self.assertEqual([m['cantidad_evidencias'] for m in listado], [3])

        # 5. Permisos: los cuatro roles leen; solo el Ejecutor adjunta.
        for usuario in (self.planificacion, self.admin_sistema, self.consulta, self.ejecutor):
            self.como(usuario)
            self.assertEqual(len(self.client.get(f'/api/mediciones/{medicion_id}/evidencias/').data), 3)
            self.assertEqual(
                self.client.get(f'/api/mediciones/{medicion_id}/evidencias/{primeras["foto actividad.jpg"]}/ver/').status_code,
                status.HTTP_200_OK,
            )

        for usuario in (self.planificacion, self.admin_sistema, self.consulta):
            self.como(usuario)
            intento = self.client.post(
                f'/api/mediciones/{medicion_id}/evidencias/',
                {'archivos': [SimpleUploadedFile('intruso.pdf', b'%PDF', content_type='application/pdf')]},
                format='multipart',
            )
            self.assertEqual(intento.status_code, status.HTTP_403_FORBIDDEN, usuario.username)

        self.client.force_authenticate(user=None)
        self.assertIn(
            self.client.get(f'/api/mediciones/{medicion_id}/evidencias/').status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

        self.assertEqual(EvidenciaMedicion.objects.filter(medicion_id=medicion_id).count(), 3)
        self.assertFalse(Medicion.objects.get(id=medicion_id).evidencia)

        # El reporte PDF de D5 lista los tres nombres.
        self.como(self.consulta)
        pdf = self.client.get(f'/api/indicadores-kpi/{kpi_id}/reporte-pdf/').content
        # (sección "Evidencias documentales": un nombre por línea)
        for nombre in (b'acta enero.pdf', b'foto actividad.jpg', b'informe.pdf'):
            self.assertIn(b'(' + nombre + b') Tj', pdf)
        self.assertIn(b'3 archivos', pdf)
