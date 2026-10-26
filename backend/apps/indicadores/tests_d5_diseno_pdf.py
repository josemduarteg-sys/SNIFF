"""D5: diseño institucional del reporte PDF.

Cada escenario genera el PDF por la API real y pasa un verificador de
maquetación: ningún texto fuera de los márgenes ni superpuesto con otro en
la misma página, encabezado y "Página X de Y" correctos en todas las páginas.

Con la variable de entorno SNIFF_PDF_SALIDA=<carpeta> los PDF generados se
guardan allí para revisarlos a mano (fuera del proyecto)."""

import gc
import os
import re
import shutil
import tempfile
from datetime import date, datetime
from decimal import Decimal
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, override_settings
from rest_framework import status

from apps.estrategia.models import PlanEstrategico

from .reporte_pdf import (
    ALTO_PAGINA,
    ANCHO_PAGINA,
    MARGEN,
    ancho_texto,
    formatear_numero,
    generar_reporte_kpi_pdf,
    resumen_kpi,
)
from .services import cerrar_mediciones_vencidas
from .tests import MedicionTestsBase

_MEDIA_ROOT = tempfile.mkdtemp(prefix='sniff_d5_diseno_')
_TEXTO = re.compile(rb'BT /(F\d) ([\d.]+) Tf ([\d.-]+) ([\d.-]+) Td \(((?:\\.|[^\\)])*)\) Tj ET')


def paginas_pdf(contenido):
    """Por página: lista de (texto, fuente, tamaño, x0, y0, x1, y1)."""
    paginas = []

    for flujo in re.findall(rb'stream\n(.*?)\nendstream', contenido, re.S):
        textos = []

        for fuente, tamano, x, y, cadena in _TEXTO.findall(flujo):
            texto = re.sub(rb'\\(.)', rb'\1', cadena).decode('cp1252')
            fuente, tamano, x, y = fuente.decode(), float(tamano), float(x), float(y)
            textos.append((texto, fuente, tamano, x, y - 0.21 * tamano, x + ancho_texto(texto, fuente, tamano), y + 0.72 * tamano))

        paginas.append(textos)

    return paginas


def problemas_de_maquetacion(contenido):
    problemas = []
    paginas = paginas_pdf(contenido)
    total = len(paginas)

    for numero, textos in enumerate(paginas, start=1):
        for texto, _, _, x0, y0, x1, y1 in textos:
            if x0 < MARGEN - 0.5 or x1 > ANCHO_PAGINA - MARGEN + 0.5 or y0 < MARGEN - 3 or y1 > ALTO_PAGINA - MARGEN + 1:
                problemas.append(f'p{numero}: fuera de márgenes {texto!r} ({x0:.1f}-{x1:.1f}, {y0:.1f}-{y1:.1f})')

        for i, a in enumerate(textos):
            for b in textos[i + 1:]:
                if a[3] < b[5] - 0.3 and b[3] < a[5] - 0.3 and a[4] < b[6] - 0.3 and b[4] < a[6] - 0.3:
                    problemas.append(f'p{numero}: superpuestos {a[0]!r} / {b[0]!r}')

        contenidos = [t[0] for t in textos]
        # Pie "Página X de Y" una vez; el bloque del encabezado dice "X de Y"
        # (el cuadro "Periodos favorables" puede coincidir, p. ej. "1 de 2").
        if contenidos.count(f'Página {numero} de {total}') != 1 or f'{numero} de {total}' not in contenidos:
            problemas.append(f'p{numero}: numeración incorrecta')
        if 'Cooperativa Chiquimuljá R. L.' not in contenidos:
            problemas.append(f'p{numero}: sin encabezado')

    return problemas


def guardar(nombre, contenido):
    carpeta = os.environ.get('SNIFF_PDF_SALIDA')

    if carpeta:
        with open(os.path.join(carpeta, f'{nombre}.pdf'), 'wb') as archivo:
            archivo.write(contenido)


@override_settings(MEDIA_ROOT=_MEDIA_ROOT)
class DisenoReportePdfTests(MedicionTestsBase):
    NOMBRE_USUARIO = 'ejecutor_diseno'

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        gc.collect()
        shutil.rmtree(_MEDIA_ROOT, ignore_errors=True)

    def registrar(self, kpi, valor, fecha, archivos=None):
        datos = {'indicador': kpi.id, 'valor_resultado': str(valor)}
        if archivos:
            datos['archivos_evidencia'] = archivos

        with mock.patch('apps.indicadores.services.hoy', return_value=fecha):
            response = self.client.post('/api/mediciones/', datos, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        return response.data

    def agregar(self, medicion_id, archivos):
        response = self.client.post(f'/api/mediciones/{medicion_id}/evidencias/', {'archivos': archivos}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    def historial(self, kpi):
        datos = self.client.get('/api/mediciones/', {'indicador': kpi.id}).data
        return datos['results'] if isinstance(datos, dict) else datos

    def pdf(self, kpi, nombre):
        response = self.client.get(f'/api/indicadores-kpi/{kpi.id}/reporte-pdf/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        contenido = response.content
        guardar(nombre, contenido)
        self.assertEqual(problemas_de_maquetacion(contenido), [])
        return contenido

    def textos(self, contenido):
        return [t[0] for pagina in paginas_pdf(contenido) for t in pagina]

    @staticmethod
    def fin_de_mes(anio, mes):
        return date(anio, mes + 1, 1).fromordinal(date(anio, mes + 1, 1).toordinal() - 1) if mes < 12 else date(anio, 12, 31)

    # ---------- Escenarios ----------

    def test_mensual_con_8_mediciones_coincide_con_la_api(self):
        kpi = self.crear_kpi('Mensual', nombre='KPI mensual ocho periodos', unidad='%')
        valores = [62, 71, 88, 79, 90, 66, 92, 85]

        for mes, valor in enumerate(valores, start=1):
            archivos = [SimpleUploadedFile(f'respaldo_{mes}.pdf', b'%PDF', content_type='application/pdf')] if mes % 3 == 0 else None
            self.registrar(kpi, valor, self.fin_de_mes(2027, mes), archivos)

        contenido = self.pdf(kpi, '1_mensual_8')
        textos = self.textos(contenido)
        historial = self.historial(kpi)

        self.assertEqual(len(paginas_pdf(contenido)), 2)
        for medicion in historial:
            self.assertIn(medicion['periodo_nombre'], textos)
            self.assertIn(formatear_numero(medicion['valor_resultado'], '%'), textos)
            self.assertIn(medicion['estado_cumplimiento_nombre'], textos)

        for seccion in ('INFORMACIÓN GENERAL', 'EVOLUCIÓN DEL INDICADOR', 'DETALLE DE MEDICIONES', 'EVIDENCIAS DOCUMENTALES'):
            self.assertTrue(any(seccion in texto for texto in textos), seccion)

        # Cuadros: último resultado y promedio simple de los 8.
        self.assertIn('85.00 %', textos)
        self.assertIn('Periodo: Agosto 2027', textos)
        self.assertIn(formatear_numero(Decimal(sum(valores)) / 8, '%'), textos)
        self.assertIn('Promedio simple de 8 resultados', textos)
        favorables = sum(1 for m in historial if m['estado_cumplimiento_nombre'] == 'Favorable')
        self.assertIn(f'{favorables} de 8', textos)

    def test_sin_mediciones(self):
        contenido = self.pdf(self.crear_kpi('Mensual', nombre='KPI sin mediciones'), '2_sin_mediciones')
        textos = self.textos(contenido)

        self.assertEqual(textos.count('Este KPI todavía no tiene mediciones registradas.'), 2)
        self.assertIn('Sin evidencias registradas.', textos)
        self.assertEqual(textos.count('Sin datos'), 2)  # último resultado y periodos favorables
        self.assertIn('No aplica', textos)

    def test_periodos_sin_registro(self):
        kpi = self.crear_kpi('Mensual', nombre='KPI con omisiones', unidad='%')
        self.registrar(kpi, 80, date(2027, 1, 31))

        with mock.patch('apps.indicadores.services.hoy', return_value=date(2027, 4, 10)):
            cerrar_mediciones_vencidas()

        self.registrar(kpi, 90, date(2027, 4, 30))
        contenido = self.pdf(kpi, '3_sin_registro')
        textos = self.textos(contenido)

        self.assertEqual([m['sin_registro'] for m in self.historial(kpi)], [False, True, True, False])
        # Promedio solo de 80 y 90 (las omisiones no cuentan como cero).
        self.assertIn('85.00 %', textos)
        self.assertIn('Promedio simple de 2 resultados', textos)
        self.assertIn('1 de 2', textos)
        self.assertIn('mediciones con resultado · 2 sin registro aparte', ' '.join(textos))
        self.assertIn('Sin registro (no equivale a cero)', textos)
        self.assertEqual(textos.count('Cierre automático'), 2)
        self.assertNotIn('0.00 %', textos)

    def test_unidad_no_porcentual(self):
        kpi = self.crear_kpi('Trimestral', nombre='KPI recuperación en quetzales', valor_meta='250000.00', unidad='Q')
        self.registrar(kpi, '187500.50', date(2027, 3, 31))
        self.registrar(kpi, '262000', date(2027, 6, 30))

        textos = self.textos(self.pdf(kpi, '4_no_porcentual'))

        self.assertIn('Q 262,000.00', textos)
        self.assertIn('Q 250,000.00', textos)
        self.assertIn('Unidad: Q', textos)
        self.assertIn('Resultado real (Q)', textos)
        self.assertFalse(any('%' in texto for texto in textos))

    def test_nombres_y_formulas_largos(self):
        nombre = ('Porcentaje de socios de la cartera de créditos productivos con seguimiento domiciliar '
                  'completado dentro del plazo establecido por la política institucional de cobranza')[:200]
        kpi = self.crear_kpi('Mensual', nombre=nombre, unidad='%')
        kpi.formula_medicion = (
            '(Número de socios con visita de seguimiento domiciliar registrada y validada por el jefe de agencia '
            'dentro de los primeros quince días hábiles posteriores al desembolso / Número total de créditos '
            'productivos desembolsados durante el periodo evaluado, excluyendo reestructuraciones y '
            'refinanciamientos autorizados por el comité de créditos) x 100'
        )
        kpi.save(update_fields=['formula_medicion'])
        PlanEstrategico.objects.filter(pk=self.plan_estrategico.pk).update(
            titulo='Plan estratégico institucional de fortalecimiento financiero, inclusión y transformación digital 2027-2030',
        )
        self.objetivo_especifico.texto_objetivo = (
            'Fortalecer la calidad de la cartera productiva mediante el seguimiento oportuno de cada crédito '
            'desembolsado, reduciendo la morosidad temprana y mejorando la relación con los asociados.'
        )
        self.objetivo_especifico.save(update_fields=['texto_objetivo'])
        self.registrar(kpi, 77, date(2027, 1, 31))

        contenido = self.pdf(kpi, '5_textos_largos')
        unido = ' '.join(self.textos(contenido))

        for fragmento in ('seguimiento domiciliar', 'refinanciamientos', 'transformación digital', 'morosidad temprana'):
            self.assertIn(fragmento, unido)

    def test_varias_paginas_con_evidencias_de_nombres_extensos(self):
        kpi = self.crear_kpi('Mensual', nombre='KPI con muchas evidencias', unidad='%')

        for mes in range(1, 13):
            medicion = self.registrar(kpi, 55 + mes * 3, self.fin_de_mes(2027, mes))
            self.agregar(medicion['id'], [
                SimpleUploadedFile(
                    f'acta_de_verificacion_de_campo_agencia_central_{mes:02d}_{n}_documento_de_respaldo_firmado_y_sellado_'
                    f'por_la_gerencia_de_creditos_version_final_definitiva.pdf',
                    b'%PDF', content_type='application/pdf',
                )
                for n in range(1, 7)
            ])

        contenido = self.pdf(kpi, '6_varias_paginas')
        paginas = paginas_pdf(contenido)
        unido = [t[0] for pagina in paginas for t in pagina]

        self.assertGreaterEqual(len(paginas), 3)
        self.assertIn('EVIDENCIAS DOCUMENTALES (continuación)', unido)
        # Ningún nombre se trunca: las 72 evidencias aparecen completas.
        nombres_partidos = ''.join(texto for texto in unido if texto.startswith(('acta_de', 'por_la', 'documento', '_')) or 'definitiva' in texto)
        for mes in range(1, 13):
            for n in range(1, 7):
                self.assertIn(f'agencia_central_{mes:02d}_{n}_documento', nombres_partidos)
        self.assertEqual(sum(1 for texto in unido if texto.endswith('6 archivos')), 12)


class TablaMultipaginaTests(SimpleTestCase):
    """La tabla de detalle con muchas filas (datos sintéticos, sin base):
    continúa en páginas nuevas con encabezados repetidos y sin partir filas."""

    def test_tabla_de_60_periodos(self):
        meses = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
        mediciones = []
        for indice in range(60):
            anio, mes = 2026 + indice // 12, indice % 12
            sin_registro = indice % 7 == 4
            mediciones.append({
                'periodo_nombre': f'{meses[mes]} {anio}',
                'fecha_registro': f'{anio}-{mes + 1:02d}-05T09:00:00',
                'cierre_automatico': sin_registro,
                'sin_registro': sin_registro,
                'valor_resultado': None if sin_registro else str(50 + indice % 45),
                'valor_meta': '80.0000',
                'estado_cumplimiento_nombre': 'Sin registro' if sin_registro else 'En riesgo',
                'estado_cumplimiento_color': 'gris' if sin_registro else 'amarillo',
                'evidencias': [],
            })
        kpi = {'nombre': 'KPI sintético', 'unidad_medida': '%', 'valor_meta': '80', 'frecuencia_nombre': 'Mensual'}

        contenido = generar_reporte_kpi_pdf(kpi, 'Objetivo', mediciones, datetime(2026, 10, 25, 10, 0), 'prueba')
        guardar('7_tabla_60', contenido)

        self.assertEqual(problemas_de_maquetacion(contenido), [])
        paginas = paginas_pdf(contenido)
        self.assertGreaterEqual(len(paginas), 3)

        filas_vistas = []
        for pagina in paginas:
            textos = [t[0] for t in pagina]
            periodos = [t for t in textos if any(t.startswith(m + ' 20') for m in meses)]
            if periodos:
                # Cada página con filas de la tabla repite los encabezados de columnas.
                self.assertIn('Estado del periodo', textos)
            filas_vistas.extend(periodos)

        # Las 60 filas aparecen una vez cada una (ninguna partida ni repetida).
        self.assertEqual(filas_vistas, [m['periodo_nombre'] for m in mediciones])

    def test_resumen_no_mezcla_sin_registro_ni_inventa(self):
        mediciones = [
            {'periodo_nombre': 'Enero 2027', 'valor_resultado': '70', 'sin_registro': False, 'estado_cumplimiento_nombre': 'En riesgo'},
            {'periodo_nombre': 'Febrero 2027', 'valor_resultado': None, 'sin_registro': True, 'estado_cumplimiento_nombre': 'Sin registro'},
            {'periodo_nombre': 'Marzo 2027', 'valor_resultado': '95', 'sin_registro': False, 'estado_cumplimiento_nombre': 'Favorable'},
        ]
        meta, ultimo, promedio, periodos = resumen_kpi({'unidad_medida': 'días', 'valor_meta': '90'}, mediciones)

        self.assertEqual(meta['valor'], '90.00 días')
        self.assertEqual((ultimo['valor'], ultimo['detalle']), ('95.00 días', 'Periodo: Marzo 2027'))
        self.assertEqual(promedio['valor'], '82.50 días')
        self.assertEqual(periodos['valor'], '1 de 2')
        self.assertIn('1 sin registro aparte', periodos['detalle'])
