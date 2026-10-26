"""D5: consulta histórica y reporte PDF de KPI (solo lectura).

Reutiliza la API existente: GET /api/mediciones/?indicador=<id> (historial
cronológico) y GET /api/indicadores-kpi/<id>/reporte-pdf/."""

import re
import gc
import shutil
import tempfile
from datetime import date
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework import status

from apps.auditoria.models import Bitacora

from .models import Medicion
from .reporte_pdf import formatear_numero, partir_texto
from .services import cerrar_mediciones_vencidas
from .tests import MedicionTestsBase, crear_usuario_admin

_MEDIA_ROOT_D5 = tempfile.mkdtemp(prefix='sniff_d5_reportes_')


def textos_pdf(contenido):
    """Cadenas que el PDF dibuja con Tj (contenido sin comprimir)."""
    texto = contenido.decode('cp1252')
    cadenas = re.findall(r'\(((?:\\.|[^\\)])*)\) Tj', texto)
    return [re.sub(r'\\(.)', r'\1', cadena) for cadena in cadenas]


@override_settings(MEDIA_ROOT=_MEDIA_ROOT_D5)
class ReportesBase(MedicionTestsBase):
    NOMBRE_USUARIO = 'ejecutor_d5'

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        # Windows no borra un archivo que un FileResponse aún tiene abierto.
        gc.collect()
        shutil.rmtree(_MEDIA_ROOT_D5, ignore_errors=True)

    def registrar(self, kpi, valor, fecha, **extra):
        with mock.patch('apps.indicadores.services.hoy', return_value=fecha):
            response = self.client.post(
                '/api/mediciones/',
                {'indicador': kpi.id, 'valor_resultado': str(valor), **extra},
                format='multipart',
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        return response.data

    def historial(self, kpi):
        response = self.client.get('/api/mediciones/', {'indicador': kpi.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        datos = response.data
        return datos['results'] if isinstance(datos, dict) else datos

    def pdf(self, kpi):
        response = self.client.get(f'/api/indicadores-kpi/{kpi.id}/reporte-pdf/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return response

    def kpi_con_omision(self):
        """Mensual: Enero 80, Febrero sin registro (cierre automático),
        Marzo 90."""
        kpi = self.crear_kpi('Mensual', nombre='KPI mensual con omision', unidad='%')
        self.registrar(kpi, 80, date(2027, 1, 31))

        with mock.patch('apps.indicadores.services.hoy', return_value=date(2027, 3, 10)):
            cerrar_mediciones_vencidas()

        self.registrar(kpi, 90, date(2027, 3, 31))
        return kpi


class HistorialTests(ReportesBase):

    def test_filtro_por_kpi_y_orden_cronologico(self):
        kpi = self.kpi_con_omision()
        otro = self.crear_kpi('Mensual', nombre='Otro KPI')
        self.registrar(otro, 10, date(2027, 1, 31))

        historial = self.historial(kpi)

        self.assertEqual({m['indicador'] for m in historial}, {kpi.id})
        self.assertEqual([m['periodo_nombre'] for m in historial], ['Enero 2027', 'Febrero 2027', 'Marzo 2027'])
        self.assertEqual([m['fecha_medicion'] for m in historial], sorted(m['fecha_medicion'] for m in historial))

    def test_sin_registro_no_es_cero(self):
        historial = self.historial(self.kpi_con_omision())
        febrero = historial[1]

        self.assertTrue(febrero['sin_registro'])
        self.assertTrue(febrero['cierre_automatico'])
        self.assertIsNone(febrero['valor_resultado'])
        self.assertIsNone(febrero['porcentaje_cumplimiento'])

    def test_kpi_sin_mediciones(self):
        self.assertEqual(self.historial(self.crear_kpi('Mensual', nombre='KPI vacio')), [])

    def test_filtro_invalido_no_devuelve_nada(self):
        self.registrar(self.crear_kpi('Mensual'), 10, date(2027, 1, 31))

        response = self.client.get('/api/mediciones/', {'indicador': 'abc'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        datos = response.data['results'] if isinstance(response.data, dict) else response.data
        self.assertEqual(datos, [])

    def test_sin_filtro_el_listado_no_cambia(self):
        self.registrar(self.crear_kpi('Mensual', nombre='A'), 10, date(2027, 1, 31))
        self.registrar(self.crear_kpi('Mensual', nombre='B'), 20, date(2027, 1, 31))

        response = self.client.get('/api/mediciones/')
        datos = response.data['results'] if isinstance(response.data, dict) else response.data

        self.assertEqual(len(datos), 2)

    def test_frecuencias_reales(self):
        trimestral = self.crear_kpi('Trimestral', nombre='KPI trimestral', unidad='unidades')
        self.registrar(trimestral, 1500, date(2027, 3, 31))
        self.registrar(trimestral, 1750, date(2027, 6, 30))

        semestral = self.crear_kpi('Semestral', nombre='KPI semestral')
        self.registrar(semestral, 40, date(2027, 6, 30))

        trimestres = self.historial(trimestral)
        self.assertEqual(len(trimestres), 2)
        self.assertEqual([m['fecha_medicion'] for m in trimestres], ['2027-03-31', '2027-06-30'])

        semestres = self.historial(semestral)
        self.assertEqual([m['fecha_medicion'] for m in semestres], ['2027-06-30'])

    def test_evidencias_multiples_en_el_historial(self):
        kpi = self.crear_kpi('Mensual')
        archivos = [
            SimpleUploadedFile(nombre, b'%PDF-1.4', content_type='application/pdf')
            for nombre in ('acta.pdf', 'informe.pdf')
        ]
        medicion = self.registrar(kpi, 50, date(2027, 1, 31), archivos_evidencia=archivos)
        self.client.post(
            f'/api/mediciones/{medicion["id"]}/evidencias/',
            {'archivos': [SimpleUploadedFile('foto.jpg', b'img', content_type='image/jpeg')]},
            format='multipart',
        )

        fila = self.historial(kpi)[0]

        self.assertEqual(fila['cantidad_evidencias'], 3)
        self.assertEqual([e['nombre_original'] for e in fila['evidencias']], ['acta.pdf', 'informe.pdf', 'foto.jpg'])


class ReportePdfTests(ReportesBase):

    def test_pdf_valido_y_descargable(self):
        response = self.pdf(self.kpi_con_omision())
        contenido = response.content

        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertIn('attachment;', response['Content-Disposition'])
        self.assertTrue(contenido.startswith(b'%PDF-1.4'))
        self.assertTrue(contenido.rstrip().endswith(b'%%EOF'))

        # La tabla xref apunta exactamente al inicio de cada objeto.
        inicio_xref = int(re.search(rb'startxref\n(\d+)', contenido).group(1))
        self.assertTrue(contenido[inicio_xref:].startswith(b'xref'))
        entradas = re.findall(rb'(\d{10}) 00000 n', contenido[inicio_xref:])

        for numero, posicion in enumerate(entradas, start=1):
            self.assertTrue(contenido[int(posicion):].startswith(b'%d 0 obj' % numero))

    def test_contenido_con_datos_reales(self):
        kpi = self.kpi_con_omision()
        textos = ' | '.join(textos_pdf(self.pdf(kpi).content))

        for esperado in (
            'Cooperativa Chiquimuljá R. L.', 'Reporte histórico de indicador KPI', 'SNIFF',
            'KPI mensual con omision', 'Plan Mediciones', 'Objetivo especifico de mediciones',
            'Mensual', 'Meta', '100.00 %', 'Enero 2027', 'Febrero 2027', 'Marzo 2027',
            '80.00 %', '90.00 %', 'Sin registro', 'Cierre automático', 'Generado', 'ejecutor_d5',
        ):
            self.assertIn(esperado, textos)

        # Febrero (omisión) no aparece como 0 y no se inventan periodos.
        self.assertNotIn('0.00 %', textos.replace('100.00 %', '').replace('80.00 %', '').replace('90.00 %', ''))
        self.assertNotIn('Abril 2027', textos)
        self.assertEqual(Medicion.objects.filter(indicador=kpi).count(), 3)

    def test_kpi_sin_mediciones(self):
        textos = ' '.join(textos_pdf(self.pdf(self.crear_kpi('Mensual', nombre='KPI sin datos')).content))

        self.assertIn('KPI sin datos', textos)
        self.assertIn('todavía no tiene mediciones', textos)

    def test_unidad_distinta_a_porcentaje(self):
        kpi = self.crear_kpi('Trimestral', nombre='KPI quetzales', valor_meta='2500.00', unidad='Q')
        self.registrar(kpi, 1234.5, date(2027, 3, 31))

        textos = ' | '.join(textos_pdf(self.pdf(kpi).content))

        self.assertIn('Q 1,234.50', textos)
        self.assertIn('Q 2,500.00', textos)
        self.assertNotIn('%', textos.replace('Página', ''))

    def test_nombres_de_evidencias_sin_incrustar_archivos(self):
        kpi = self.crear_kpi('Mensual')
        contenido_archivo = b'%PDF-1.4 CONTENIDO-SECRETO-DE-EVIDENCIA'
        self.registrar(kpi, 50, date(2027, 1, 31), archivos_evidencia=[
            SimpleUploadedFile('acta (firmada).pdf', contenido_archivo, content_type='application/pdf'),
            SimpleUploadedFile('foto.jpg', b'img', content_type='image/jpeg'),
        ])

        contenido = self.pdf(kpi).content
        textos = ' '.join(textos_pdf(contenido))

        # Sección 04: agrupadas por periodo, un nombre por línea.
        self.assertIn('EVIDENCIAS DOCUMENTALES', textos)
        self.assertIn('Enero 2027  ·  2 archivos', textos)
        self.assertIn('acta (firmada).pdf', textos)
        self.assertIn('foto.jpg', textos)
        self.assertNotIn(b'CONTENIDO-SECRETO-DE-EVIDENCIA', contenido)

    def test_kpi_no_autorizado_no_tiene_reporte(self):
        kpi = self.crear_kpi('Mensual')
        kpi.estado = 'borrador'
        kpi.save(update_fields=['estado'])

        response = self.client.get(f'/api/indicadores-kpi/{kpi.id}/reporte-pdf/')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_genera_bitacora_y_no_modifica_datos(self):
        kpi = self.kpi_con_omision()
        antes = list(Medicion.objects.filter(indicador=kpi).values().order_by('id'))

        self.pdf(kpi)

        registro = Bitacora.objects.filter(modulo='Reportes').latest('id')
        self.assertEqual(registro.usuario, self.usuario)
        self.assertEqual(registro.accion, 'consultar')
        self.assertIn(kpi.nombre, registro.descripcion)
        self.assertEqual(list(Medicion.objects.filter(indicador=kpi).values().order_by('id')), antes)


class PermisosReportesTests(ReportesBase):

    def test_los_cuatro_roles_consultan_y_descargan(self):
        kpi = self.kpi_con_omision()
        usuarios = [
            self.usuario,
            crear_usuario_admin('d5_admin_sistema', rol_nombre='Administrador del sistema'),
            crear_usuario_admin('d5_admin_plan', rol_nombre='Administrador de planificación'),
            crear_usuario_admin('d5_consulta', rol_nombre='Usuario de consulta'),
        ]

        for usuario in usuarios:
            self.client.force_authenticate(user=usuario)
            self.assertEqual(len(self.historial(kpi)), 3, usuario.username)
            self.assertTrue(self.pdf(kpi).content.startswith(b'%PDF'), usuario.username)

    def test_anonimo_no_accede(self):
        kpi = self.crear_kpi('Mensual')
        self.client.force_authenticate(user=None)

        for url in (f'/api/indicadores-kpi/{kpi.id}/reporte-pdf/', f'/api/mediciones/?indicador={kpi.id}'):
            self.assertIn(
                self.client.get(url).status_code,
                (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
            )

    def test_el_reporte_es_solo_lectura(self):
        kpi = self.crear_kpi('Mensual')
        self.client.force_authenticate(user=crear_usuario_admin('d5_plan_escritura'))

        for metodo in (self.client.post, self.client.put, self.client.patch, self.client.delete):
            response = metodo(f'/api/indicadores-kpi/{kpi.id}/reporte-pdf/')
            self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_consulta_no_obtiene_permisos_de_escritura(self):
        kpi = self.crear_kpi('Mensual')
        medicion = self.registrar(kpi, 50, date(2027, 1, 31))
        self.client.force_authenticate(user=crear_usuario_admin('d5_solo_consulta', rol_nombre='Usuario de consulta'))

        response = self.client.patch(f'/api/mediciones/{medicion["id"]}/', {'valor_resultado': '99'})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class FormatoPdfTests(ReportesBase):

    def test_formato_numerico_igual_al_frontend(self):
        self.assertEqual(formatear_numero('1234.5', 'Q'), 'Q 1,234.50')
        self.assertEqual(formatear_numero('85', '%'), '85.00 %')
        self.assertEqual(formatear_numero('12.3456', 'horas'), '12.35 horas')
        self.assertEqual(formatear_numero(None, '%'), '-')

    def test_partir_texto_respeta_el_ancho(self):
        lineas = partir_texto('palabra ' * 40 + 'x' * 200, 'F1', 9, 120)

        self.assertGreater(len(lineas), 5)
        self.assertTrue(all(len(linea) <= 200 for linea in lineas))
