"""D5: reporte PDF institucional de un KPI (consulta histórica).

Se escribe el PDF directamente (PDF 1.4, fuentes estándar Helvetica con
WinAnsiEncoding, gráficos vectoriales), sin dependencias: el documento solo
necesita texto, tablas, rectángulos, líneas y círculos. La maquetación
controla cada salto de página: encabezado y pie en todas las páginas,
encabezados de tabla repetidos, filas que nunca se parten y "Página X de Y"
real (el pie se dibuja cuando ya se conoce el total).

Todo el contenido sale de los datos ya serializados por la API
(IndicadorKPISerializer / MedicionSerializer), así el PDF muestra lo mismo
que la pantalla de Reportes. Los archivos de evidencia NO se incrustan: solo
se listan sus nombres."""

import math
import unicodedata
from decimal import Decimal, InvalidOperation

ANCHO_PAGINA = 595  # A4 vertical, en puntos
ALTO_PAGINA = 842
MARGEN = 42
ANCHO_UTIL = ANCHO_PAGINA - 2 * MARGEN
ALTO_ENCABEZADO = 62
ALTO_PIE = 30
TOPE_CONTENIDO = ALTO_PAGINA - MARGEN - ALTO_ENCABEZADO
BASE_CONTENIDO = MARGEN + ALTO_PIE

INSTITUCION = 'Cooperativa Chiquimuljá R. L.'
TITULO = 'Reporte histórico de indicador KPI'

# Paleta del frontend de SNIFF.
AZUL_OSCURO = (0.114, 0.208, 0.341)   # #1d3557
AZUL = (0.271, 0.482, 0.616)          # #457b9d
TEXTO = (0.114, 0.208, 0.341)
SECUNDARIO = (0.369, 0.431, 0.510)    # #5e6e82
TENUE = (0.604, 0.659, 0.722)         # #9aa8b8
BORDE = (0.835, 0.867, 0.894)         # #d5dde4
GUIA = (0.918, 0.937, 0.953)
FONDO_SUAVE = (0.957, 0.969, 0.976)   # #f4f7f9
FONDO_ETIQUETA = (0.918, 0.961, 0.961)  # #eaf5f5
BLANCO = (1, 1, 1)

# Colores de estado (EstadoCumplimiento.color), mismo significado que en la
# interfaz; tonos algo más oscuros para que se lean impresos.
COLORES_ESTADO = {
    'verde': (0.165, 0.616, 0.561),     # #2a9d8f
    'amarillo': (0.725, 0.439, 0.118),  # #b9701e
    'rojo': (0.820, 0.341, 0.224),      # #d15739
    'gris': (0.553, 0.600, 0.682),      # #8d99ae
}
GRIS_SIN_REGISTRO = COLORES_ESTADO['gris']

# Anchos AFM (milésimas de em) de Helvetica y Helvetica-Bold, 32..126.
_ANCHOS = {
    'F1': [
        278, 278, 355, 556, 556, 889, 667, 191, 333, 333, 389, 584, 278, 333, 278, 278,
        556, 556, 556, 556, 556, 556, 556, 556, 556, 556, 278, 278, 584, 584, 584, 556,
        1015, 667, 667, 722, 722, 667, 611, 778, 722, 278, 500, 667, 556, 833, 722, 778,
        667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 278, 278, 278, 469, 556,
        333, 556, 556, 500, 556, 556, 278, 556, 556, 222, 222, 500, 222, 833, 556, 556,
        556, 556, 333, 500, 278, 556, 500, 722, 500, 500, 500, 334, 260, 334, 584,
    ],
    'F2': [
        278, 333, 474, 556, 556, 889, 722, 238, 333, 333, 389, 584, 278, 333, 278, 278,
        556, 556, 556, 556, 556, 556, 556, 556, 556, 556, 333, 333, 584, 584, 584, 611,
        975, 722, 722, 722, 722, 667, 611, 778, 722, 278, 556, 722, 611, 833, 722, 778,
        667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 333, 278, 333, 584, 556,
        333, 556, 611, 556, 611, 556, 333, 611, 611, 278, 278, 556, 278, 889, 611, 611,
        611, 611, 389, 556, 333, 611, 556, 778, 556, 556, 500, 389, 280, 389, 584,
    ],
}
# Símbolos de WinAnsi usados en el reporte que no son letras acentuadas.
_ANCHOS_ESPECIALES = {'·': 278, '×': 584, '—': 1000, '–': 556, '•': 350, '«': 556, '»': 556, '°': 400, '¿': 611, '¡': 333}

MESES_CORTOS = {
    'enero': 'Ene', 'febrero': 'Feb', 'marzo': 'Mar', 'abril': 'Abr', 'mayo': 'May', 'junio': 'Jun',
    'julio': 'Jul', 'agosto': 'Ago', 'septiembre': 'Sep', 'octubre': 'Oct', 'noviembre': 'Nov', 'diciembre': 'Dic',
}


# ------------------------------------------------------------------
# Texto y formato
# ------------------------------------------------------------------

def ancho_texto(texto, fuente, tamano):
    total = 0

    for caracter in str(texto):
        if caracter in _ANCHOS_ESPECIALES:
            total += _ANCHOS_ESPECIALES[caracter]
            continue

        codigo = ord(caracter)

        if not 32 <= codigo <= 126:
            base = unicodedata.normalize('NFD', caracter)[0]
            codigo = ord(base) if 32 <= ord(base) <= 126 else ord('n')

        total += _ANCHOS[fuente][codigo - 32]

    return total * tamano / 1000


def partir_texto(texto, fuente, tamano, ancho):
    """Divide en líneas que entren en `ancho`; corta palabras largas (nombres
    de archivo sin espacios) sin perder caracteres."""
    lineas = []

    for parrafo in str(texto or '').split('\n'):
        actual = ''

        for palabra in parrafo.split():
            candidata = f'{actual} {palabra}'.strip()

            if ancho_texto(candidata, fuente, tamano) <= ancho:
                actual = candidata
                continue

            if actual:
                lineas.append(actual)

            while ancho_texto(palabra, fuente, tamano) > ancho:
                corte = len(palabra)

                while corte > 1 and ancho_texto(palabra[:corte], fuente, tamano) > ancho:
                    corte -= 1

                lineas.append(palabra[:corte])
                palabra = palabra[corte:]

            actual = palabra

        lineas.append(actual)

    return lineas or ['']


def _cadena_pdf(texto):
    datos = str(texto).encode('cp1252', errors='replace')
    return b'(' + datos.replace(b'\\', b'\\\\').replace(b'(', b'\\(').replace(b')', b'\\)') + b')'


def _numero(valor):
    if valor is None or valor == '':
        return None

    try:
        return Decimal(str(valor))
    except InvalidOperation:
        return None


def formatear_numero(valor, unidad=''):
    """Mismo formato que formatearNumero() del frontend (es-GT, 2 decimales)."""
    numero = _numero(valor)

    if numero is None:
        return '-' if valor in (None, '') else str(valor)

    texto = f'{numero:,.2f}'

    if not unidad:
        return texto

    if unidad == 'Q':
        return f'Q {texto}'

    return f'{texto} {unidad}'


def formatear_fecha(valor):
    """'2027-01-31' o '2027-01-31T10:20:00-06:00' -> '31/01/2027'."""
    if not valor:
        return '-'

    anio, mes, dia = str(valor)[:10].split('-')
    return f'{dia}/{mes}/{anio}'


def etiqueta_corta_periodo(nombre):
    """'Enero 2027' -> ('Ene', '2027'); 'Enero - febrero 2027' ->
    ('Ene-Feb', '2027'). Solo para el eje de la gráfica."""
    partes = str(nombre or '-').split()

    if len(partes) >= 2 and partes[-1].isdigit():
        anio = partes[-1]
        meses = [MESES_CORTOS.get(p.lower(), p) for p in partes[:-1] if p != '-']
        return '-'.join(meses), anio

    return str(nombre or '-'), ''


# ------------------------------------------------------------------
# Datos del reporte (solo a partir de lo que devuelve la API)
# ------------------------------------------------------------------

def resumen_kpi(kpi, mediciones):
    """Valores de los cuatro cuadros de resumen. Solo resumen lo que se
    presenta en el reporte: no se guardan ni sustituyen cálculos oficiales.
    Un periodo "Sin registro" nunca cuenta como cero."""
    unidad = kpi.get('unidad_medida') or ''
    con_resultado = [
        m for m in mediciones
        if not m.get('sin_registro') and _numero(m.get('valor_resultado')) is not None
    ]
    sin_registro = sum(1 for m in mediciones if m.get('sin_registro'))

    meta = {
        'etiqueta': 'META',
        'valor': formatear_numero(kpi.get('valor_meta'), unidad) if _numero(kpi.get('valor_meta')) is not None else 'Sin datos',
        'detalle': f'Unidad: {unidad}' if unidad else 'Meta configurada del KPI',
    }

    if con_resultado:
        ultima = con_resultado[-1]
        ultimo = {
            'etiqueta': 'ÚLTIMO RESULTADO',
            'valor': formatear_numero(ultima.get('valor_resultado'), unidad),
            'detalle': f'Periodo: {ultima.get("periodo_nombre") or "-"}',
        }
        valores = [_numero(m.get('valor_resultado')) for m in con_resultado]
        promedio = {
            'etiqueta': 'PROMEDIO DEL PERIODO',
            'valor': formatear_numero(sum(valores) / len(valores), unidad),
            'detalle': f'Promedio simple de {len(valores)} resultado{"s" if len(valores) != 1 else ""}',
        }
        favorables = sum(1 for m in con_resultado if m.get('estado_cumplimiento_nombre') == 'Favorable')
        detalle = 'mediciones con resultado'
        if sin_registro:
            detalle += f' · {sin_registro} sin registro aparte'
        periodos = {'etiqueta': 'PERIODOS FAVORABLES', 'valor': f'{favorables} de {len(con_resultado)}', 'detalle': detalle}
    else:
        ultimo = {'etiqueta': 'ÚLTIMO RESULTADO', 'valor': 'Sin datos', 'detalle': 'Ninguna medición con resultado'}
        promedio = {'etiqueta': 'PROMEDIO DEL PERIODO', 'valor': 'No aplica', 'detalle': 'Sin resultados que promediar'}
        periodos = {
            'etiqueta': 'PERIODOS FAVORABLES',
            'valor': 'Sin datos',
            'detalle': f'{sin_registro} periodo{"s" if sin_registro != 1 else ""} sin registro' if sin_registro else 'Sin mediciones evaluadas',
        }

    return [meta, ultimo, promedio, periodos]


def filas_mediciones(mediciones, unidad):
    """Celdas de la tabla de detalle, en el orden recibido (cronológico).
    Una omisión se muestra "Sin registro", nunca como 0."""
    filas = []

    for medicion in mediciones:
        sin_registro = medicion.get('sin_registro')
        cantidad = len(medicion.get('evidencias') or [])
        filas.append({
            'periodo': medicion.get('periodo_nombre') or '-',
            'fecha': 'Cierre automático' if medicion.get('cierre_automatico') else formatear_fecha(medicion.get('fecha_registro')),
            'resultado': 'Sin registro' if sin_registro else formatear_numero(medicion.get('valor_resultado'), unidad),
            'meta': formatear_numero(medicion.get('valor_meta'), unidad),
            'estado': medicion.get('estado_cumplimiento_nombre') or '-',
            'color': (medicion.get('estado_cumplimiento_color') or '').lower().strip(),
            'evidencias': str(cantidad) if cantidad else '-',
            'sin_registro': bool(sin_registro),
        })

    return filas


# ------------------------------------------------------------------
# Páginas y documento
# ------------------------------------------------------------------

class _Pagina:
    def __init__(self):
        self.ops = []

    def _color(self, rgb, relleno=True):
        self.ops.append(('%.3f %.3f %.3f %s' % (*rgb, 'rg' if relleno else 'RG')).encode())

    def texto(self, x, y, contenido, fuente='F1', tamano=9, rgb=TEXTO, alineacion='izquierda'):
        if alineacion == 'derecha':
            x -= ancho_texto(contenido, fuente, tamano)
        elif alineacion == 'centro':
            x -= ancho_texto(contenido, fuente, tamano) / 2

        self._color(rgb)
        self.ops.append(
            b'BT /' + fuente.encode() + b' %.2f Tf %.2f %.2f Td ' % (tamano, x, y)
            + _cadena_pdf(contenido) + b' Tj ET'
        )

    def rectangulo(self, x, y, ancho, alto, relleno=None, borde=None, grosor=0.6):
        if relleno:
            self._color(relleno)
        if borde:
            self._color(borde, relleno=False)
            self.ops.append(b'%.2f w' % grosor)

        operador = b'B' if relleno and borde else (b'f' if relleno else b'S')
        self.ops.append(b'%.2f %.2f %.2f %.2f re ' % (x, y, ancho, alto) + operador)

    def linea(self, x1, y1, x2, y2, rgb=BORDE, grosor=0.6, guiones=None):
        self._color(rgb, relleno=False)
        patron = b'[%s] 0 d' % b' '.join(b'%.1f' % g for g in guiones) if guiones else b'[] 0 d'
        self.ops.append(b'%s %.2f w %.2f %.2f m %.2f %.2f l S [] 0 d' % (patron, grosor, x1, y1, x2, y2))

    def polilinea(self, puntos, rgb, grosor=1.6, guiones=None):
        if len(puntos) < 2:
            return

        self._color(rgb, relleno=False)
        patron = b'[%s] 0 d' % b' '.join(b'%.1f' % g for g in guiones) if guiones else b'[] 0 d'
        trazo = b' '.join(
            b'%.2f %.2f %s' % (x, y, b'm' if indice == 0 else b'l') for indice, (x, y) in enumerate(puntos)
        )
        self.ops.append(b'%s %.2f w 1 J 1 j %s S [] 0 d 0 J 0 j' % (patron, grosor, trazo))

    def circulo(self, cx, cy, radio, relleno, borde=BLANCO, grosor=1.2):
        k = 0.5523 * radio
        self._color(relleno)
        self._color(borde, relleno=False)
        self.ops.append(
            b'%.2f w %.2f %.2f m ' % (grosor, cx + radio, cy)
            + b'%.2f %.2f %.2f %.2f %.2f %.2f c ' % (cx + radio, cy + k, cx + k, cy + radio, cx, cy + radio)
            + b'%.2f %.2f %.2f %.2f %.2f %.2f c ' % (cx - k, cy + radio, cx - radio, cy + k, cx - radio, cy)
            + b'%.2f %.2f %.2f %.2f %.2f %.2f c ' % (cx - radio, cy - k, cx - k, cy - radio, cx, cy - radio)
            + b'%.2f %.2f %.2f %.2f %.2f %.2f c B' % (cx + k, cy - radio, cx + radio, cy - k, cx + radio, cy)
        )

    def contenido(self):
        return b'\n'.join(self.ops)


class _Documento:
    def __init__(self, generado_en, generado_por):
        self.paginas = []
        self.generado = generado_en.strftime('%d/%m/%Y %H:%M')
        self.generado_por = generado_por
        self.nueva_pagina()

    def nueva_pagina(self):
        self.pagina = _Pagina()
        self.paginas.append(self.pagina)
        self.y = TOPE_CONTENIDO

    def cabe(self, alto):
        return self.y - alto >= BASE_CONTENIDO

    def reservar(self, alto):
        """Garantiza `alto` puntos libres; si no entran, pasa de página.
        Devuelve True si hubo salto."""
        if self.cabe(alto):
            return False

        self.nueva_pagina()
        return True

    # Encabezado y pie: se dibujan al final, con el total de páginas.
    def _marco(self, pagina, numero, total):
        tope = ALTO_PAGINA - MARGEN
        pagina.texto(MARGEN, tope - 14, INSTITUCION, 'F2', 14, AZUL_OSCURO)
        pagina.texto(MARGEN, tope - 31, TITULO, 'F1', 10.5, AZUL)
        pagina.texto(MARGEN, tope - 45, 'SNIFF · Sistema de seguimiento de indicadores', 'F1', 7.5, TENUE)

        ancho_bloque = 150
        x_bloque = ANCHO_PAGINA - MARGEN - ancho_bloque
        pagina.rectangulo(x_bloque, tope - 47, ancho_bloque, 47, relleno=FONDO_SUAVE, borde=BORDE)
        filas = [
            ('Generado', self.generado),
            ('Usuario', self.generado_por),
            ('Página', f'{numero} de {total}'),
        ]
        for indice, (etiqueta, valor) in enumerate(filas):
            y = tope - 13 - indice * 13
            pagina.texto(x_bloque + 8, y, etiqueta, 'F2', 7.5, SECUNDARIO)
            valor = valor if ancho_texto(valor, 'F1', 7.5) <= ancho_bloque - 60 else partir_texto(valor, 'F1', 7.5, ancho_bloque - 60)[0]
            pagina.texto(x_bloque + ancho_bloque - 8, y, valor, 'F1', 7.5, TEXTO, 'derecha')

        pagina.linea(MARGEN, tope - ALTO_ENCABEZADO + 8, ANCHO_PAGINA - MARGEN, tope - ALTO_ENCABEZADO + 8, AZUL_OSCURO, 1.4)

        # Pie: solo la numeración, pequeña y en gris discreto.
        pagina.texto(ANCHO_PAGINA - MARGEN, MARGEN + 4, f'Página {numero} de {total}', 'F1', 7, TENUE, 'derecha')

    def bytes(self):
        total = len(self.paginas)

        for numero, pagina in enumerate(self.paginas, start=1):
            self._marco(pagina, numero, total)

        objetos = [
            b'<< /Type /Catalog /Pages 2 0 R >>',
            None,  # Pages: se completa abajo
            b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>',
            b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>',
        ]
        hijos = []

        for pagina in self.paginas:
            flujo = pagina.contenido()
            objetos.append(b'<< /Length %d >>\nstream\n' % len(flujo) + flujo + b'\nendstream')
            numero_flujo = len(objetos)
            objetos.append(
                b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %d %d] '
                b'/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents %d 0 R >>'
                % (ANCHO_PAGINA, ALTO_PAGINA, numero_flujo)
            )
            hijos.append(b'%d 0 R' % len(objetos))

        objetos[1] = b'<< /Type /Pages /Kids [' + b' '.join(hijos) + b'] /Count %d >>' % len(hijos)

        salida = bytearray(b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n')
        posiciones = []

        for indice, objeto in enumerate(objetos, start=1):
            posiciones.append(len(salida))
            salida += b'%d 0 obj\n' % indice + objeto + b'\nendobj\n'

        inicio_xref = len(salida)
        salida += b'xref\n0 %d\n0000000000 65535 f \n' % (len(objetos) + 1)

        for posicion in posiciones:
            salida += b'%010d 00000 n \n' % posicion

        salida += b'trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n' % (len(objetos) + 1, inicio_xref)
        return bytes(salida)


# ------------------------------------------------------------------
# Bloques del reporte
# ------------------------------------------------------------------

def _barra_seccion(documento, numero, titulo, continuacion=False):
    alto = 18
    # La barra nunca queda sola al pie: exige lugar para algo de contenido.
    documento.reservar(alto + 40)
    p = documento.pagina
    p.rectangulo(MARGEN, documento.y - alto, ANCHO_UTIL, alto, relleno=AZUL_OSCURO)
    p.texto(MARGEN + 8, documento.y - 12.5, numero, 'F2', 9, (0.659, 0.855, 0.863))
    p.texto(MARGEN + 30, documento.y - 12.5, titulo + (' (continuación)' if continuacion else ''), 'F2', 9, BLANCO)
    documento.y -= alto + 8


def _informacion_general(documento, kpi, objetivo):
    unidad = kpi.get('unidad_medida') or ''
    # formatear_numero ya agrega la unidad ("90.00 %", "Q 2,500.00").
    if _numero(kpi.get('valor_meta')) is not None:
        meta = formatear_numero(kpi.get('valor_meta'), unidad) if unidad else formatear_numero(kpi.get('valor_meta'))
    else:
        meta = f'Sin meta configurada (unidad: {unidad or "-"})'
    datos = [
        ('Indicador KPI', kpi.get('nombre')),
        ('Plan estratégico', kpi.get('plan_estrategico_titulo')),
        ('Plan anual', kpi.get('plan_anual_nombre')),
        ('Objetivo relacionado', objetivo),
        ('Frecuencia de medición', kpi.get('frecuencia_nombre')),
        ('Meta y unidad', meta),
        ('Fórmula de medición', kpi.get('formula_medicion')),
    ]
    ancho_etiqueta = 128
    ancho_valor = ANCHO_UTIL - ancho_etiqueta
    interlineado = 11
    relleno = 5

    _barra_seccion(documento, '01', 'INFORMACIÓN GENERAL')

    for etiqueta, valor in datos:
        fuente = 'F2' if etiqueta == 'Indicador KPI' else 'F1'
        lineas = partir_texto(valor or '-', fuente, 8.5, ancho_valor - 2 * relleno)
        alto = len(lineas) * interlineado + 2 * relleno

        if documento.reservar(alto):
            _barra_seccion(documento, '01', 'INFORMACIÓN GENERAL', continuacion=True)

        p = documento.pagina
        y = documento.y
        p.rectangulo(MARGEN, y - alto, ancho_etiqueta, alto, relleno=FONDO_ETIQUETA, borde=BORDE)
        p.rectangulo(MARGEN + ancho_etiqueta, y - alto, ancho_valor, alto, borde=BORDE)
        p.texto(MARGEN + relleno, y - relleno - 8, etiqueta, 'F2', 8, AZUL_OSCURO)

        for indice, linea in enumerate(lineas):
            p.texto(MARGEN + ancho_etiqueta + relleno, y - relleno - 8 - indice * interlineado, linea, fuente, 8.5, TEXTO)

        documento.y -= alto


def _cuadros_resumen(documento, cuadros):
    separacion = 8
    ancho = (ANCHO_UTIL - separacion * (len(cuadros) - 1)) / len(cuadros)
    detalles = [partir_texto(c['detalle'], 'F1', 6.8, ancho - 14) for c in cuadros]
    alto = 34 + max(len(d) for d in detalles) * 8.5

    documento.y -= 10
    documento.reservar(alto)
    p = documento.pagina

    for indice, (cuadro, detalle) in enumerate(zip(cuadros, detalles)):
        x = MARGEN + indice * (ancho + separacion)
        y = documento.y
        p.rectangulo(x, y - alto, ancho, alto, relleno=BLANCO, borde=BORDE)
        p.rectangulo(x, y - alto, 2.2, alto, relleno=AZUL)
        p.texto(x + 9, y - 12, cuadro['etiqueta'], 'F2', 6.8, SECUNDARIO)

        valor = cuadro['valor']
        tamano = 12
        while tamano > 8 and ancho_texto(valor, 'F2', tamano) > ancho - 16:
            tamano -= 0.5
        p.texto(x + 9, y - 27, valor, 'F2', tamano, AZUL_OSCURO)

        for n, linea in enumerate(detalle):
            p.texto(x + 9, y - 38 - n * 8.5, linea, 'F1', 6.8, SECUNDARIO)

    documento.y -= alto + 4
    nota = ('Resumen de los periodos incluidos en este reporte. El promedio es una media simple de los resultados '
            'registrados y no sustituye el seguimiento acumulado oficial del KPI.')
    for linea in partir_texto(nota, 'F1', 6.8, ANCHO_UTIL):
        documento.y -= 8.5
        documento.pagina.texto(MARGEN, documento.y, linea, 'F1', 6.8, TENUE)


def _escala(valores, unidad):
    if unidad == '%':
        return 0, 100, [0, 25, 50, 75, 100]

    mayor = max([0] + valores)

    if mayor == 0:
        return 0, 1, [0, 0.25, 0.5, 0.75, 1]

    # Mismo criterio que escalaVertical() del frontend: paso "redondo"
    # (1, 2, 2.5, 5 o 10 por potencia de diez) para unas cuatro divisiones.
    bruto = mayor / 4
    potencia = 10 ** math.floor(math.log10(bruto))
    fraccion = bruto / potencia
    paso = (1 if fraccion <= 1 else 2 if fraccion <= 2 else 2.5 if fraccion <= 2.5 else 5 if fraccion <= 5 else 10) * potencia
    maximo = paso * math.ceil(mayor * 1.05 / paso)
    marcas = []
    marca = 0
    while marca <= maximo + paso / 2:
        marcas.append(round(marca, 10))
        marca += paso
    return 0, maximo, marcas


def _grafica(documento, kpi, mediciones):
    unidad = kpi.get('unidad_medida') or ''
    _barra_seccion(documento, '02', 'EVOLUCIÓN DEL INDICADOR')

    if not mediciones:
        documento.y -= 4
        documento.pagina.texto(MARGEN, documento.y - 10, 'Este KPI todavía no tiene mediciones registradas.', 'F1', 8.5, SECUNDARIO)
        documento.y -= 22
        return

    alto_total = 238
    documento.reservar(alto_total)
    p = documento.pagina
    tope = documento.y

    puntos = []
    for medicion in mediciones:
        sin_registro = bool(medicion.get('sin_registro'))
        valor = None if sin_registro else _numero(medicion.get('valor_resultado'))
        puntos.append({
            'valor': float(valor) if valor is not None else None,
            'meta': float(_numero(medicion.get('valor_meta'))) if _numero(medicion.get('valor_meta')) is not None else None,
            'sin_registro': sin_registro,
            'color': COLORES_ESTADO.get((medicion.get('estado_cumplimiento_color') or '').lower().strip(), GRIS_SIN_REGISTRO),
            'etiqueta': etiqueta_corta_periodo(medicion.get('periodo_nombre')),
        })

    valores = [v for pt in puntos for v in (pt['valor'], pt['meta']) if v is not None]
    minimo, maximo, marcas = _escala(valores, unidad)

    izquierda = MARGEN + 46
    derecha = MARGEN + ANCHO_UTIL - 6
    arriba = tope - 10
    abajo = tope - 176
    alto = arriba - abajo
    paso_x = (derecha - izquierda) / len(puntos)

    def px(indice):
        return izquierda + (indice + 0.5) * paso_x

    def py(valor):
        return abajo + (valor - minimo) / (maximo - minimo) * alto

    # Guías y eje vertical en la unidad del KPI.
    for marca in marcas:
        y = py(marca)
        p.linea(izquierda, y, derecha, y, GUIA, 0.6)
        texto = f'{marca:,.0f}' if float(marca).is_integer() else f'{marca:,.2f}'
        p.texto(izquierda - 5, y - 2.5, texto, 'F1', 7, SECUNDARIO, 'derecha')

    p.texto(MARGEN, arriba + 9, f'Unidad: {unidad or "-"}', 'F2', 7, SECUNDARIO)

    # Periodos sin resultado: franja y × sobre el eje (nunca un punto en 0).
    for indice, punto in enumerate(puntos):
        if punto['valor'] is None:
            p.rectangulo(px(indice) - paso_x / 2, abajo, paso_x, alto, relleno=(0.953, 0.961, 0.969))
            cx, cy = px(indice), abajo + 7
            p.linea(cx - 3.5, cy - 3.5, cx + 3.5, cy + 3.5, GRIS_SIN_REGISTRO, 1.4)
            p.linea(cx - 3.5, cy + 3.5, cx + 3.5, cy - 3.5, GRIS_SIN_REGISTRO, 1.4)

    p.linea(izquierda, abajo, derecha, abajo, BORDE, 1)

    # Meta de referencia (punteada).
    metas = [(px(i), py(pt['meta'])) for i, pt in enumerate(puntos) if pt['meta'] is not None]
    if len(metas) == 1:
        p.linea(izquierda, metas[0][1], derecha, metas[0][1], AZUL_OSCURO, 1, guiones=(4, 3))
    else:
        p.polilinea(metas, AZUL_OSCURO, 1, guiones=(4, 3))

    # Resultado real: tramos continuos; una omisión corta la línea.
    tramo = []
    for indice, punto in enumerate(puntos + [{'valor': None}]):
        if punto['valor'] is None:
            p.polilinea(tramo, AZUL, 1.8)
            tramo = []
        else:
            tramo.append((px(indice), py(punto['valor'])))

    radio = 3.2 if paso_x >= 18 else 2.4
    for indice, punto in enumerate(puntos):
        if punto['valor'] is not None:
            p.circulo(px(indice), py(punto['valor']), radio, punto['color'], grosor=1.2 if radio > 3 else 0.7)

    # Etiquetas del eje horizontal: si no entran todas, una de cada k. La
    # última siempre se muestra; si quedaría pegada a la anterior, la
    # reemplaza.
    ancho_etiqueta = max(ancho_texto(e[0], 'F1', 6.8) for e in (pt['etiqueta'] for pt in puntos)) + 6
    cada = max(1, math.ceil(ancho_etiqueta / paso_x))
    visibles = list(range(0, len(puntos), cada))
    if visibles[-1] != len(puntos) - 1:
        if len(puntos) - 1 - visibles[-1] < cada:
            visibles.pop()
        visibles.append(len(puntos) - 1)

    for indice in visibles:
        punto = puntos[indice]
        linea1, linea2 = punto['etiqueta']
        color = TENUE if punto['valor'] is None else SECUNDARIO
        p.texto(px(indice), abajo - 10, linea1, 'F1', 6.8, color, 'centro')
        if linea2:
            p.texto(px(indice), abajo - 18.5, linea2, 'F1', 6.8, color, 'centro')

    # Leyenda.
    y = abajo - 36
    x = izquierda
    p.linea(x, y + 2.5, x + 16, y + 2.5, AZUL, 1.8)
    p.texto(x + 20, y, f'Resultado real ({unidad or "valor"})', 'F1', 7, SECUNDARIO)
    x += 28 + ancho_texto(f'Resultado real ({unidad or "valor"})', 'F1', 7) + 12
    if metas:
        p.linea(x, y + 2.5, x + 16, y + 2.5, AZUL_OSCURO, 1, guiones=(4, 3))
        p.texto(x + 20, y, 'Meta', 'F1', 7, SECUNDARIO)
        x += 20 + ancho_texto('Meta', 'F1', 7) + 14
    if any(pt['valor'] is None for pt in puntos):
        p.linea(x, y, x + 6, y + 6, GRIS_SIN_REGISTRO, 1.4)
        p.linea(x, y + 6, x + 6, y, GRIS_SIN_REGISTRO, 1.4)
        p.texto(x + 10, y, 'Sin registro (no equivale a cero)', 'F1', 7, SECUNDARIO)
        x += 10 + ancho_texto('Sin registro (no equivale a cero)', 'F1', 7) + 14

    vistos = []
    for medicion in mediciones:
        nombre = medicion.get('estado_cumplimiento_nombre')
        if medicion.get('sin_registro') or not nombre or nombre in [v[0] for v in vistos]:
            continue
        vistos.append((nombre, COLORES_ESTADO.get((medicion.get('estado_cumplimiento_color') or '').lower().strip(), GRIS_SIN_REGISTRO)))

    for nombre, color in vistos:
        ancho = 10 + ancho_texto(nombre, 'F1', 7) + 12
        if x + ancho > derecha:
            y -= 11
            x = izquierda
        p.circulo(x + 3, y + 2.5, 3, color, grosor=0.6)
        p.texto(x + 10, y, nombre, 'F1', 7, SECUNDARIO)
        x += ancho

    documento.y = min(y - 12, tope - alto_total)


COLUMNAS = [
    ('periodo', 'Periodo', 104, 'izquierda'),
    ('fecha', 'Fecha de registro', 80, 'izquierda'),
    ('resultado', 'Resultado', 78, 'derecha'),
    ('meta', 'Meta', 76, 'derecha'),
    ('estado', 'Estado del periodo', 115, 'izquierda'),
    ('evidencias', 'Evidencias', ANCHO_UTIL - 104 - 80 - 78 - 76 - 115, 'derecha'),
]


def _detalle_mediciones(documento, filas):
    tamano = 8
    interlineado = 10
    relleno = 5

    def encabezado(continuacion=False):
        _barra_seccion(documento, '03', 'DETALLE DE MEDICIONES', continuacion)
        alto = interlineado + 2 * relleno
        p = documento.pagina
        p.rectangulo(MARGEN, documento.y - alto, ANCHO_UTIL, alto, relleno=FONDO_ETIQUETA, borde=BORDE)
        x = MARGEN
        for _, titulo, ancho, alineacion in COLUMNAS:
            tx = x + ancho - relleno if alineacion == 'derecha' else x + relleno
            p.texto(tx, documento.y - relleno - 7.5, titulo, 'F2', 7.5, AZUL_OSCURO, alineacion)
            x += ancho
        documento.y -= alto

    if not filas:
        _barra_seccion(documento, '03', 'DETALLE DE MEDICIONES')
        documento.pagina.texto(MARGEN, documento.y - 10, 'Este KPI todavía no tiene mediciones registradas.', 'F1', 8.5, SECUNDARIO)
        documento.y -= 22
        return

    encabezado()

    for numero, fila in enumerate(filas):
        celdas = {
            clave: partir_texto(fila[clave], 'F1', tamano, ancho - 2 * relleno - (10 if clave == 'estado' else 0))
            for clave, _, ancho, _ in COLUMNAS
        }
        alto = max(len(lineas) for lineas in celdas.values()) * interlineado + 2 * relleno

        # La fila nunca se parte: si no entra, la tabla sigue en otra página
        # con sus encabezados.
        if not documento.cabe(alto):
            documento.nueva_pagina()
            encabezado(continuacion=True)

        p = documento.pagina
        y = documento.y
        if numero % 2:
            p.rectangulo(MARGEN, y - alto, ANCHO_UTIL, alto, relleno=FONDO_SUAVE)

        x = MARGEN
        for clave, _, ancho, alineacion in COLUMNAS:
            color = TEXTO
            fuente = 'F1'
            desplazamiento = 0

            if clave == 'estado':
                tono = GRIS_SIN_REGISTRO if fila['sin_registro'] else COLORES_ESTADO.get(fila['color'], GRIS_SIN_REGISTRO)
                p.circulo(x + relleno + 3, y - relleno - 5, 2.8, tono, grosor=0.4)
                desplazamiento = 10
                color = tono
                fuente = 'F2'
            elif clave == 'resultado' and fila['sin_registro']:
                color = SECUNDARIO

            for indice, linea in enumerate(celdas[clave]):
                tx = x + ancho - relleno if alineacion == 'derecha' else x + relleno + desplazamiento
                p.texto(tx, y - relleno - 7.5 - indice * interlineado, linea, fuente, tamano, color, alineacion)
            x += ancho

        p.linea(MARGEN, y - alto, MARGEN + ANCHO_UTIL, y - alto, BORDE, 0.5)
        documento.y -= alto

    documento.y -= 6


def _evidencias(documento, mediciones):
    _barra_seccion(documento, '04', 'EVIDENCIAS DOCUMENTALES')
    con_evidencias = [m for m in mediciones if m.get('evidencias')]

    if not con_evidencias:
        documento.pagina.texto(MARGEN, documento.y - 10, 'Sin evidencias registradas.', 'F1', 8.5, SECUNDARIO)
        documento.y -= 22
        return

    sangria = 14
    for medicion in con_evidencias:
        evidencias = medicion['evidencias']
        titulo = f'{medicion.get("periodo_nombre") or "-"}  ·  {len(evidencias)} archivo{"s" if len(evidencias) != 1 else ""}'

        if documento.reservar(30):
            _barra_seccion(documento, '04', 'EVIDENCIAS DOCUMENTALES', continuacion=True)

        documento.y -= 11
        documento.pagina.texto(MARGEN, documento.y, titulo, 'F2', 8.5, AZUL_OSCURO)
        documento.y -= 3

        for evidencia in evidencias:
            lineas = partir_texto(evidencia.get('nombre_original') or '-', 'F1', 8, ANCHO_UTIL - sangria - 150)
            alto = len(lineas) * 10 + 2

            if documento.reservar(alto):
                _barra_seccion(documento, '04', 'EVIDENCIAS DOCUMENTALES', continuacion=True)
                documento.y -= 11
                documento.pagina.texto(MARGEN, documento.y, f'{titulo} (continuación)', 'F2', 8.5, AZUL_OSCURO)
                documento.y -= 3

            p = documento.pagina
            y = documento.y
            p.texto(MARGEN + 4, y - 8, '•', 'F1', 8, AZUL)
            for indice, linea in enumerate(lineas):
                p.texto(MARGEN + sangria, y - 8 - indice * 10, linea, 'F1', 8, TEXTO)

            detalle = ' · '.join(filter(None, [
                formatear_fecha(evidencia['fecha_subida']) if evidencia.get('fecha_subida') else '',
                evidencia.get('subido_por_username'),
            ]))
            p.texto(MARGEN + ANCHO_UTIL, y - 8, detalle, 'F1', 7, SECUNDARIO, 'derecha')
            documento.y -= alto

        documento.y -= 2
        documento.pagina.linea(MARGEN, documento.y, MARGEN + ANCHO_UTIL, documento.y, GUIA, 0.5)


def generar_reporte_kpi_pdf(kpi, objetivo, mediciones, generado_en, generado_por):
    """`kpi`: IndicadorKPISerializer().data; `mediciones`:
    MedicionSerializer(many=True).data en orden cronológico."""
    documento = _Documento(generado_en, generado_por)
    unidad = kpi.get('unidad_medida') or ''

    _informacion_general(documento, kpi, objetivo)
    _cuadros_resumen(documento, resumen_kpi(kpi, mediciones))
    documento.y -= 12
    _grafica(documento, kpi, mediciones)
    documento.y -= 8
    _detalle_mediciones(documento, filas_mediciones(mediciones, unidad))
    documento.y -= 6
    _evidencias(documento, mediciones)

    return documento.bytes()
