from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .models import Alerta, EstadoCumplimiento, IndicadorKPI, Medicion, MetaKPI, PeriodoMedicion, RangoKPI

TIPO_ALERTA_PERIODO_VENCIDO = 'Periodo vencido sin medición'
"""Único lugar donde vive este literal (Bloque 5): lo usan tanto las
alertas de periodo vencido (Bloque 4) como el nuevo cálculo de alerta de
cumplimiento acumulado, para que este último pueda ignorar sin ambigüedad
las alertas de la otra familia al buscar la alerta pendiente del KPI."""

TIPO_ALERTA_PERIODO_SIN_REGISTRO = 'Periodo sin registro'
"""Etapa 3 (auditoría C3): alerta que deja el cierre automático cuando un
periodo venció sin resultado. Es un incumplimiento del registro oportuno,
no un resultado de desempeño."""

TIPOS_ALERTA_REGISTRO = (TIPO_ALERTA_PERIODO_VENCIDO, TIPO_ALERTA_PERIODO_SIN_REGISTRO)
"""Alertas sobre el REGISTRO (no sobre el cumplimiento del KPI): la alerta de
cumplimiento acumulado las ignora al buscar su propia alerta pendiente."""

ESTADO_SIN_REGISTRO = 'Sin registro'
"""Estado del catálogo (migración indicadores.0015) para los cierres
automáticos por falta de registro. Ningún RangoKPI lo usa."""


def obtener_estado_sin_registro():
    return EstadoCumplimiento.objects.filter(nombre__iexact=ESTADO_SIN_REGISTRO).first()


def hoy():
    """Punto único de acceso a la fecha 'actual' del sistema (Bloque 4).
    Usa la fecha local de Django (respeta TIME_ZONE), nunca la fecha del
    navegador. Centralizado acá para que las pruebas puedan mockear
    `apps.indicadores.services.hoy` en vez de manipular el reloj real."""
    return timezone.localdate()


def calcular_porcentaje_cumplimiento(valor_resultado, valor_meta):
    if valor_meta is None or valor_meta == 0:
        return Decimal('0')

    return (Decimal(valor_resultado) / Decimal(valor_meta)) * Decimal('100')


def precargado(instancia, relacion):
    """Etapa 6 (M8): lista ya cargada con prefetch_related (o None). Las
    funciones de abajo la usan si existe — mismo resultado, sin una consulta
    por cada fila de un listado — y si no, consultan como siempre."""
    cache = getattr(instancia, '_prefetched_objects_cache', None) or {}

    if relacion in cache:
        return list(cache[relacion])

    return None


def obtener_estado_por_cumplimiento(indicador, porcentaje_cumplimiento):
    """Clasifica un porcentaje de cumplimiento usando ÚNICAMENTE los RangoKPI
    reales del indicador (fuente de verdad). No hardcodea umbrales (85/70,
    90/70, etc.) — si no hay un rango aplicable, cae al fallback técnico
    'Pendiente de actualización'.

    valor_minimo es inclusivo y valor_maximo es exclusivo; valor_maximo NULL
    significa "sin límite superior". Con rangos contiguos (el mínimo de uno
    coincide con el máximo del anterior) esto cubre el eje sin huecos ni
    solapamientos, a cualquier precisión.
    """
    rangos = precargado(indicador, 'rangos')

    if rangos is not None:
        # Etapa 6 (M8): misma condición y mismo orden (valor_minimo) que la
        # consulta de abajo, sobre los rangos ya cargados del KPI.
        valor = Decimal(porcentaje_cumplimiento)
        aplicables = [
            r for r in sorted(rangos, key=lambda r: (r.valor_minimo, r.id))
            if r.estado and r.valor_minimo <= valor and (r.valor_maximo is None or r.valor_maximo > valor)
        ]

        if aplicables:
            return aplicables[0].estado_cumplimiento

        if not hasattr(indicador, '_estado_pendiente_cache'):
            indicador._estado_pendiente_cache = EstadoCumplimiento.objects.filter(
                nombre__iexact='Pendiente de actualización',
                estado=True,
            ).first()

        return indicador._estado_pendiente_cache

    rango = RangoKPI.objects.select_related(
        'estado_cumplimiento'
    ).filter(
        Q(valor_maximo__isnull=True) | Q(valor_maximo__gt=porcentaje_cumplimiento),
        indicador=indicador,
        estado=True,
        valor_minimo__lte=porcentaje_cumplimiento,
    ).first()

    if rango:
        return rango.estado_cumplimiento

    estado_pendiente = EstadoCumplimiento.objects.filter(
        nombre__iexact='Pendiente de actualización',
        estado=True,
    ).first()

    return estado_pendiente


def obtener_estado_para_medicion(indicador, meta, valor_resultado):
    """REGLA V2 (corrección del 120 %): el Estado del periodo clasifica
    `valor_resultado` DIRECTAMENTE contra los RangoKPI del indicador —
    igual que ya hacía `obtener_estado_acumulado_kpi` con el promedio
    acumulado. Antes de esta corrección se clasificaba
    `valor_resultado / meta * 100` (lógica de VERSIÓN 1), lo que producía
    valores engañosos como "120 %" en KPI cuya unidad no es un porcentaje
    y donde un valor mayor puede ser peor (ej. días), y era inconsistente
    con el estado acumulado (que nunca usó ese porcentaje). `meta` se
    conserva en la firma por compatibilidad con los 3 llamadores
    existentes (creación/edición de Medicion y cierre automático), aunque
    ya no participa en la clasificación."""
    valor_para_clasificar = round(Decimal(valor_resultado), 2)

    estado = obtener_estado_por_cumplimiento(
        indicador=indicador,
        porcentaje_cumplimiento=valor_para_clasificar,
    )

    return estado


PLANTILLA_RANGOS_PROVISIONALES = (
    # (nombre del EstadoCumplimiento real, valor_minimo, valor_maximo)
    # valor_minimo inclusivo, valor_maximo exclusivo; None = sin límite.
    ('Incumplido', Decimal('0'), Decimal('60.01')),
    ('En riesgo', Decimal('60.01'), Decimal('75.01')),
    ('Favorable', Decimal('75.01'), None),
)
"""Plantilla de rangos para KPI NUEVOS en porcentaje (D3, criterio de Hernán
del 06/10/2026): 0 a 60 inclusive Incumplido, más de 60 hasta 75 inclusive
En riesgo, más de 75 Favorable. Los límites técnicos 60,01 y 75,01 son
exactos porque todo valor se redondea a dos decimales antes de clasificarse
(round(..., 2) en cada medición y quantize(0.01) en el promedio): 60,00 cae
en Incumplido, 60,01 en En riesgo, 75,00 en En riesgo y 75,01 en Favorable.

Reemplaza a la plantilla provisional 70/85, que sigue vigente en los KPI que
ya la tienen guardada: la clasificación NUNCA lee esta plantilla, siempre
consulta los RangoKPI guardados en la base de datos. Cambiarla solo afecta a
los KPI que se creen de ahora en adelante."""

UNIDAD_PORCENTAJE = '%'


def es_kpi_porcentual(indicador):
    return (indicador.unidad_medida or '').strip() == UNIDAD_PORCENTAJE


def obtener_estados_cumplimiento_plantilla():
    nombres = [nombre for nombre, _, _ in PLANTILLA_RANGOS_PROVISIONALES]
    estados = EstadoCumplimiento.objects.filter(nombre__in=nombres, estado=True)
    return {estado.nombre: estado for estado in estados}


def crear_rangos_provisionales(indicador):
    """Crea los RangoKPI de la plantilla para un KPI en PORCENTAJE que todavía
    no tenga rango para ese estado. Idempotente: no duplica ni modifica un
    rango existente. A un KPI en otra unidad (días, quetzales...) no le crea
    nada: sus rangos se configuran según su unidad antes de autorizarlo (ver
    validar_rangos_para_autorizar)."""
    if not es_kpi_porcentual(indicador):
        return 0

    estados = obtener_estados_cumplimiento_plantilla()

    faltantes = [
        nombre for nombre, _, _ in PLANTILLA_RANGOS_PROVISIONALES
        if nombre not in estados
    ]

    if faltantes:
        raise ValueError(
            'No se encontraron en el catálogo EstadoCumplimiento los '
            f'estados requeridos: {", ".join(faltantes)}.'
        )

    creados = 0

    for nombre_estado, minimo, maximo in PLANTILLA_RANGOS_PROVISIONALES:
        estado_cumplimiento = estados[nombre_estado]

        _, fue_creado = RangoKPI.objects.get_or_create(
            indicador=indicador,
            estado_cumplimiento=estado_cumplimiento,
            defaults={
                'valor_minimo': minimo,
                'valor_maximo': maximo,
                'estado': True,
            },
        )

        if fue_creado:
            creados += 1

    return creados


def rangos_son_plantilla_porcentual(rangos):
    """True si los rangos activos son exactamente una plantilla porcentual:
    la vigente (60/75) o la anterior (70/85)."""
    plantillas = [
        {(nombre, minimo, maximo) for nombre, minimo, maximo in PLANTILLA_RANGOS_PROVISIONALES},
        {('Incumplido', Decimal('0'), Decimal('70')), ('En riesgo', Decimal('70'), Decimal('85')), ('Favorable', Decimal('85'), None)},
    ]
    actuales = {(r.estado_cumplimiento.nombre, r.valor_minimo, r.valor_maximo) for r in rangos}
    return actuales in plantillas


def validar_rangos_para_autorizar(indicador):
    """Errores que impiden autorizar un KPI por sus rangos (lista vacía si
    están bien). Un KPI autorizado clasifica cada medición con sus rangos, así
    que antes de autorizarlo debe tener rangos activos, coherentes y propios
    de su unidad. No cambia nada; los KPI ya autorizados no se revisan."""
    rangos = list(
        RangoKPI.objects.filter(indicador=indicador, estado=True)
        .select_related('estado_cumplimiento')
        .order_by('valor_minimo', 'id')
    )

    if not rangos:
        return [
            'El KPI no tiene rangos de evaluación configurados. Configurá los rangos de '
            f'Incumplido, En riesgo y Favorable según su unidad ({indicador.unidad_medida}) antes de autorizarlo.'
        ]

    errores = []

    for rango in rangos:
        if rango.valor_maximo is not None and rango.valor_maximo <= rango.valor_minimo:
            errores.append(
                f'El rango "{rango.estado_cumplimiento.nombre}" tiene un máximo menor o igual a su mínimo.'
            )

    for anterior, siguiente in zip(rangos, rangos[1:]):
        if anterior.valor_maximo is None or anterior.valor_maximo > siguiente.valor_minimo:
            errores.append(
                f'Los rangos "{anterior.estado_cumplimiento.nombre}" y '
                f'"{siguiente.estado_cumplimiento.nombre}" se superponen.'
            )

    if not es_kpi_porcentual(indicador) and rangos_son_plantilla_porcentual(rangos):
        errores.append(
            f'El KPI se mide en {indicador.unidad_medida}, pero conserva los rangos porcentuales por '
            'defecto. Configurá rangos propios de su unidad antes de autorizarlo.'
        )

    return errores


def validar_conjunto_rangos(datos):
    """Valida el conjunto completo de rangos enviado para un KPI (acción
    configurar-rangos). Devuelve (rangos normalizados, errores). Cada rango:
    {estado_cumplimiento: id, valor_minimo, valor_maximo (vacío = sin
    límite)}. Reglas: al menos un rango, estados del catálogo activos y sin
    repetir ("Sin registro" no clasifica resultados), mínimo no negativo,
    máximo mayor que el mínimo y sin superposiciones (mínimo inclusivo,
    máximo exclusivo)."""
    from decimal import InvalidOperation

    if not isinstance(datos, list) or not datos:
        return [], ['Enviá al menos un rango de evaluación.']

    errores = []
    rangos = []
    vistos = set()

    def a_decimal(valor):
        """(número, válido): vacío -> (None, True); inválido -> (None, False)."""
        if valor is None or str(valor).strip() == '':
            return None, True
        try:
            numero = Decimal(str(valor).replace(',', '.'))
        except (InvalidOperation, ValueError):
            return None, False
        if not numero.is_finite():
            return None, False
        return numero.quantize(Decimal('0.0001')), True

    for item in datos:
        if not isinstance(item, dict):
            errores.append('Cada rango debe indicar estado, mínimo y máximo.')
            continue

        estado = EstadoCumplimiento.objects.filter(pk=item.get('estado_cumplimiento'), estado=True).first()

        if estado is None or estado.nombre.strip().lower() == ESTADO_SIN_REGISTRO.lower():
            errores.append('Uno de los rangos no tiene un estado de cumplimiento válido.')
            continue

        if estado.id in vistos:
            errores.append(f'El estado "{estado.nombre}" está repetido.')
            continue

        vistos.add(estado.id)
        minimo, minimo_valido = a_decimal(item.get('valor_minimo'))
        maximo, maximo_valido = a_decimal(item.get('valor_maximo'))

        if not minimo_valido or not maximo_valido:
            errores.append(f'Los valores de "{estado.nombre}" deben ser números.')
            continue

        if minimo is None:
            errores.append(f'Indicá el mínimo de "{estado.nombre}".')
            continue

        if minimo < 0:
            errores.append(f'El mínimo de "{estado.nombre}" no puede ser negativo.')
        if maximo is not None and maximo <= minimo:
            errores.append(f'El máximo de "{estado.nombre}" debe ser mayor que su mínimo.')

        rangos.append({'estado_cumplimiento': estado, 'valor_minimo': minimo, 'valor_maximo': maximo})

    ordenados = sorted(rangos, key=lambda r: r['valor_minimo'])

    for anterior, siguiente in zip(ordenados, ordenados[1:]):
        if anterior['valor_maximo'] is None or anterior['valor_maximo'] > siguiente['valor_minimo']:
            errores.append(
                f'Los rangos "{anterior["estado_cumplimiento"].nombre}" y '
                f'"{siguiente["estado_cumplimiento"].nombre}" se superponen.'
            )

    return (ordenados if not errores else []), errores


def configurar_rangos_provisionales_para_todos():
    """Completa SOLO configuraciones ausentes y seguras: crea los rangos de la
    plantilla en los KPI en porcentaje que no tienen ningún rango. Nunca
    modifica ni reemplaza rangos existentes (personalizados, invertidos o de
    la plantilla anterior) y nunca asigna rangos porcentuales a un KPI en otra
    unidad: esos casos se informan como omitidos. Reproducible: correrlo de
    nuevo no duplica ni cambia nada.

    Antes de D3 este proceso también sobrescribía con la plantilla los KPI que
    tuvieran exactamente sus tres estados, sin mirar la unidad: habría pisado
    rangos personalizados (como los del KPI #9) o invertidos (#10, en días)."""
    kpi_procesados = 0
    rangos_creados_total = 0
    detalle = []

    with transaction.atomic():
        for indicador in IndicadorKPI.objects.all().order_by('id'):
            kpi_procesados += 1

            if RangoKPI.objects.filter(indicador=indicador).exists():
                detalle.append({
                    'indicador_id': indicador.id,
                    'indicador': indicador.nombre,
                    'accion': 'omitido',
                    'motivo': 'Ya tiene rangos configurados: no se modifican.',
                })
                continue

            if not es_kpi_porcentual(indicador):
                detalle.append({
                    'indicador_id': indicador.id,
                    'indicador': indicador.nombre,
                    'accion': 'omitido',
                    'motivo': (
                        f'Se mide en {indicador.unidad_medida}: sus rangos se configuran '
                        'manualmente según su unidad.'
                    ),
                })
                continue

            creados = crear_rangos_provisionales(indicador)
            rangos_creados_total += creados
            detalle.append({
                'indicador_id': indicador.id,
                'indicador': indicador.nombre,
                'accion': 'creado',
                'rangos_creados': creados,
            })

    return {
        'kpi_procesados': kpi_procesados,
        'rangos_creados': rangos_creados_total,
        'rangos_actualizados': 0,
        'detalle': detalle,
    }


def recalcular_mediciones_pendientes():
    """Recalcula ÚNICAMENTE las mediciones cuyo estado_cumplimiento actual
    es el fallback técnico 'Pendiente de actualización', y solo si el KPI
    correspondiente ya tiene RangoKPI válidos que permitan clasificarlas.

    No toca mediciones que ya estén en Favorable/En riesgo/Incumplido, no
    modifica valor_resultado ni ningún otro campo. REGLA V2: clasifica
    `valor_resultado` DIRECTAMENTE contra RangoKPI (igual que
    `obtener_estado_para_medicion`), no `Medicion.calcular_cumplimiento()`
    (que sigue siendo el porcentaje legacy resultado/meta*100).
    """
    estado_pendiente = EstadoCumplimiento.objects.filter(
        nombre__iexact='Pendiente de actualización',
    ).first()

    if not estado_pendiente:
        return {'revisadas': 0, 'recalculadas': 0, 'detalle': []}

    mediciones = Medicion.objects.filter(
        estado_cumplimiento=estado_pendiente,
        valor_resultado__isnull=False,
    ).select_related('indicador', 'meta', 'estado_cumplimiento')

    revisadas = 0
    recalculadas = 0
    detalle = []

    with transaction.atomic():
        for medicion in mediciones:
            revisadas += 1

            valor_clasificado = round(Decimal(medicion.valor_resultado), 2)

            nuevo_estado = obtener_estado_por_cumplimiento(
                indicador=medicion.indicador,
                porcentaje_cumplimiento=valor_clasificado,
            )

            if not nuevo_estado or nuevo_estado.id == estado_pendiente.id:
                # Sigue sin haber un rango aplicable: se deja como está.
                continue

            Medicion.objects.filter(id=medicion.id).update(
                estado_cumplimiento=nuevo_estado,
            )

            recalculadas += 1
            detalle.append({
                'medicion_id': medicion.id,
                'indicador': medicion.indicador.nombre,
                'valor_clasificado': str(valor_clasificado),
                'estado_anterior': estado_pendiente.nombre,
                'estado_nuevo': nuevo_estado.nombre,
            })

    return {
        'revisadas': revisadas,
        'recalculadas': recalculadas,
        'detalle': detalle,
    }


def calcular_promedio_acumulado_kpi(indicador, hasta_periodo=None):
    """REGLA DEFINITIVA del promedio acumulado (Bloque 5): promedio directo
    de `Medicion.valor_resultado` de este KPI — NUNCA de
    `valor_resultado / meta * 100` ni de `porcentaje_cumplimiento`, y NUNCA
    mezclado con las mediciones de otro KPI (cada KPI tiene su propia
    unidad, sus propios RangoKPI y su propio promedio). Ejemplo: mediciones
    80, 60, 40 -> promedio = (80+60+40)/3 = 60.00 (nunca un valor derivado
    de meta como 70.58/68.42).

    Se aplica igual para todas las frecuencias (cada Medicion cuenta como
    UNA observación, sin importar cuántos meses cubra su periodo).

    Etapa 3 (auditoría C3), ajuste funcional adoptado durante la revisión
    del sistema: SUSTITUYE el criterio anterior por el que toda omisión se
    cerraba en 0.00 y participaba del promedio como una medición más. Ahora
    una omisión ("Sin registro", valor_resultado NULL) no es un resultado y
    queda fuera del promedio; se cuenta aparte (contar_omisiones_kpi). Un
    0.00 registrado sigue siendo un resultado real y sí participa. Los
    cierres automáticos anteriores guardados con 0.00, si existieran, se
    conservan tal cual (no se reinterpreta el historial).

    No se persiste en base de datos (no existe un campo
    `promedio_acumulado` en IndicadorKPI): se calcula al vuelo cada vez que
    se necesita, siempre sobre las Mediciones reales de este KPI (que ya
    pertenecen a un único año/PlanAnual).

    `hasta_periodo` (un PeriodoMedicion) permite el acumulado histórico
    "hasta cierta medición" (ej. hasta la de enero, hasta la de febrero...).
    Se filtra por `PeriodoMedicion.fecha_inicio`, NUNCA por
    `Medicion.fecha_registro` (una medición de enero registrada en febrero
    sigue perteneciendo a enero).

    Devuelve None cuando el KPI todavía no tiene ninguna medición (0.00
    sería un resultado real y no puede usarse para representar "sin
    datos"), o el promedio redondeado a 2 decimales en caso contrario.
    """
    precargadas = precargado(indicador, 'mediciones')

    if precargadas is not None:
        # Etapa 6 (M8): mismos filtros que la consulta de abajo.
        valores = [
            m.valor_resultado for m in precargadas
            if m.valor_resultado is not None
            and (hasta_periodo is None or m.periodo.fecha_inicio <= hasta_periodo.fecha_inicio)
        ]
    else:
        mediciones = Medicion.objects.filter(indicador=indicador, valor_resultado__isnull=False)

        if hasta_periodo is not None:
            mediciones = mediciones.filter(periodo__fecha_inicio__lte=hasta_periodo.fecha_inicio)

        valores = list(mediciones.values_list('valor_resultado', flat=True))

    if not valores:
        return None

    total = sum((Decimal(valor) for valor in valores), Decimal('0'))
    promedio = total / Decimal(len(valores))

    return promedio.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def contar_mediciones_kpi(indicador):
    """Mediciones con resultado real (Etapa 3, C3: excluye las omisiones)."""
    precargadas = precargado(indicador, 'mediciones')

    if precargadas is not None:
        return sum(1 for m in precargadas if m.valor_resultado is not None)

    return Medicion.objects.filter(indicador=indicador, valor_resultado__isnull=False).count()


def contar_omisiones_kpi(indicador):
    """Periodos cerrados automáticamente por falta de registro."""
    precargadas = precargado(indicador, 'mediciones')

    if precargadas is not None:
        return sum(1 for m in precargadas if m.valor_resultado is None)

    return Medicion.objects.filter(indicador=indicador, valor_resultado__isnull=True).count()


def obtener_estado_acumulado_kpi(indicador, promedio_acumulado):
    """Estado 'gerencial' actual del KPI (Bloque 5): clasifica el promedio
    acumulado DIRECTAMENTE contra los RangoKPI reales del indicador,
    reutilizando la misma función de clasificación que ya usa cada Medicion
    individual (`obtener_estado_por_cumplimiento` — pese a su nombre de
    parámetro, solo compara un número contra valor_minimo/valor_maximo, sin
    asumir que sea un porcentaje). No hay umbrales hardcodeados acá.

    Sin mediciones (promedio_acumulado=None) no hay nada que clasificar. Si
    el promedio existe pero ningún RangoKPI lo cubre, se conserva el mismo
    fallback técnico 'Pendiente de actualización' que ya usan las
    Mediciones individuales."""
    if promedio_acumulado is None:
        return None

    return obtener_estado_por_cumplimiento(
        indicador=indicador,
        porcentaje_cumplimiento=promedio_acumulado,
    )


def formatear_valor_acumulado(valor, unidad):
    """Texto del promedio acumulado con la unidad propia del KPI (nunca se
    le agrega '%' si la unidad real es otra, punto 10 del Bloque 5)."""
    texto = f'{valor:.2f}'

    if not unidad:
        return texto

    if unidad == 'Q':
        return f'Q {texto}'

    return f'{texto} {unidad}'


def actualizar_alerta_cumplimiento_kpi(indicador, medicion_actual=None):
    """Alerta de cumplimiento del KPI basada en el PROMEDIO ACUMULADO
    (Bloque 5) — reemplaza la lógica anterior (VERSIÓN 1) que clasificaba
    una sola Medicion aislada. Se llama después de crear o editar
    cualquier Medicion (manual o de cierre automático).

    Garantiza como máximo UNA alerta 'pendiente' de cumplimiento por KPI, y
    es completamente independiente de las alertas de tipo
    `TIPO_ALERTA_PERIODO_VENCIDO` (se excluyen explícitamente al buscar la
    alerta pendiente existente, para no interferir con esa otra familia):

    - Sin mediciones todavía: no genera ni mantiene ninguna alerta.
    - Favorable: descarta la alerta pendiente existente (si la había) y no
      crea una nueva.
    - Sin RangoKPI aplicable ('Pendiente de actualización'): no se inventa
      una alerta nueva; tampoco se descarta una alerta pendiente ya
      existente solo por esta causa (puede seguir reflejando el último
      estado real conocido).
    - En riesgo / Incumplido: si ya hay una alerta pendiente para ese mismo
      estado, se reutiliza (mensaje + medición asociada actualizados, sin
      duplicar). Si el estado cambió respecto a la alerta pendiente
      existente, esa alerta se descarta y se crea la correspondiente al
      nuevo estado.
    """
    promedio = calcular_promedio_acumulado_kpi(indicador)
    estado = obtener_estado_acumulado_kpi(indicador, promedio)

    alerta_pendiente = Alerta.objects.filter(
        indicador=indicador,
        estado_alerta='pendiente',
    ).exclude(tipo_alerta__in=TIPOS_ALERTA_REGISTRO).first()

    def descartar_pendiente():
        alerta_pendiente.estado_alerta = 'descartada'
        alerta_pendiente.fecha_revision = timezone.now()
        alerta_pendiente.save(update_fields=['estado_alerta', 'fecha_revision'])

    if promedio is None:
        if alerta_pendiente:
            descartar_pendiente()
        return None

    if estado is None or estado.nombre.lower() == 'pendiente de actualización':
        return alerta_pendiente

    if estado.nombre.lower() == 'favorable':
        if alerta_pendiente:
            descartar_pendiente()
        return None

    tipo_alerta = f'KPI {estado.nombre}'
    cantidad = contar_mediciones_kpi(indicador)
    mensaje = (
        f'El KPI "{indicador.nombre}" tiene un promedio acumulado de '
        f'{formatear_valor_acumulado(promedio, indicador.unidad_medida)} después de '
        f'{cantidad} mediciones y se encuentra {estado.nombre}.'
    )

    if alerta_pendiente and alerta_pendiente.tipo_alerta == tipo_alerta:
        alerta_pendiente.mensaje = mensaje

        if medicion_actual is not None:
            alerta_pendiente.medicion = medicion_actual

        alerta_pendiente.save()
        return alerta_pendiente

    if alerta_pendiente:
        descartar_pendiente()

    return Alerta.objects.create(
        indicador=indicador,
        medicion=medicion_actual,
        tipo_alerta=tipo_alerta,
        mensaje=mensaje,
        estado_alerta='pendiente',
    )


def marcar_alerta_revisada(alerta, usuario=None):
    """Marca una Alerta (de cualquier tipo: cumplimiento o 'Periodo vencido
    sin medición') como revisada por un usuario. No la elimina ni reescribe
    su mensaje: solo transiciona su estado, dejando trazabilidad completa
    para auditoría (queda almacenada, con fecha_revision y revisado_por).

    Idempotente: si la alerta ya no está 'pendiente' (ya es 'revisada' o
    'descartada'), no hace nada y devuelve la alerta tal cual — evita
    pisar, por ejemplo, una alerta ya 'descartada' por
    `actualizar_alerta_cumplimiento_kpi`/`resolver_alertas_periodo_vencido`
    con un estado 'revisada' contradictorio.

    Una alerta ya revisada NUNCA vuelve a quedar 'pendiente' por este
    camino: si más adelante se registra una nueva Medicion y el KPI sigue
    En riesgo/Incumplido, es `actualizar_alerta_cumplimiento_kpi` quien
    crea una alerta 'pendiente' nueva (ver esa función), no esta."""
    if alerta.estado_alerta != 'pendiente':
        return alerta

    alerta.estado_alerta = 'revisada'
    alerta.fecha_revision = timezone.now()
    alerta.revisado_por = usuario
    alerta.save(update_fields=['estado_alerta', 'fecha_revision', 'revisado_por'])

    return alerta


def filtrar_alertas_vigentes(queryset):
    """Etapa 4 (auditoría M6): alertas que todavía requieren atención —
    excluye las de KPI anulados y las de KPI cuyo Plan anual o Plan
    estratégico está Cerrado. No modifica ninguna alerta: las excluidas
    siguen guardadas como historial con su estado original."""
    return queryset.exclude(indicador__estado='anulado').exclude(
        indicador__objetivo_especifico__plan_anual__estado='cerrado',
    ).exclude(
        indicador__objetivo_especifico__plan_anual__plan_estrategico__estado='cerrado',
    )


def marcar_todas_alertas_revisadas(usuario=None, solo_vigentes=False):
    """Marca como revisadas TODAS las Alerta actualmente 'pendiente' (Bloque
    5.1 — Centro de notificaciones). Alerta no está asociada a un usuario
    destino (a diferencia de Notificacion): es información de KPI visible
    para cualquiera con permiso de verla, así que "marcar todas" aplica al
    total de alertas pendientes del sistema, sin distinguir tipo_alerta
    (cumplimiento y 'Periodo vencido sin medición' comparten el mismo
    ciclo de vida de estado_alerta).

    Etapa 4: con solo_vigentes=True (lo que usa la API) se limita a las
    alertas que todavía requieren atención (ver filtrar_alertas_vigentes)."""
    pendientes = Alerta.objects.filter(estado_alerta='pendiente')

    if solo_vigentes:
        pendientes = filtrar_alertas_vigentes(pendientes)

    # update() sobre un queryset con exclude() a través de relaciones usa
    # una subconsulta por id; se materializan los ids para que sea portable.
    return Alerta.objects.filter(id__in=list(pendientes.values_list('id', flat=True))).update(
        estado_alerta='revisada',
        fecha_revision=timezone.now(),
        revisado_por=usuario,
    )


def marca_periodo_en_mensaje(periodo_nombre):
    """Etapa 4 (M6): fragmento con el que la alerta de periodo vencido
    identifica su periodo ("periodo de enero 2027 ("). Antes se buscaba solo
    el nombre del periodo, que también podía aparecer en el nombre del KPI
    (p. ej. "Meta enero 2027") y confundir la deduplicación. El formato de
    los mensajes anteriores ya contenía este fragmento."""
    return f'periodo de {periodo_nombre} ('


def resolver_alertas_periodo_vencido(medicion, usuario=None):
    """Descarta las alertas de 'Periodo vencido sin medición' cuyo periodo
    ya quedó cubierto por esta medición (manual o cierre automático). No
    borra nada, solo cambia estado. Bloque 4: como ahora existen periodos
    de más de un mes, el nombre se calcula con el mismo intervalo real del
    periodo (derivado de sus propias fecha_inicio/fecha_fin) para que
    coincida exactamente con el mensaje que generó la alerta."""
    if not medicion.periodo_id or not medicion.periodo.fecha_inicio:
        return 0

    intervalo = (
        (medicion.periodo.fecha_fin.year - medicion.periodo.fecha_inicio.year) * 12
        + (medicion.periodo.fecha_fin.month - medicion.periodo.fecha_inicio.month)
        + 1
    )

    periodo_nombre = formatear_periodo(
        date(
            medicion.periodo.fecha_inicio.year,
            medicion.periodo.fecha_inicio.month,
            1,
        ),
        intervalo,
    )

    return Alerta.objects.filter(
        indicador=medicion.indicador,
        tipo_alerta=TIPO_ALERTA_PERIODO_VENCIDO,
        estado_alerta='pendiente',
        mensaje__icontains=marca_periodo_en_mensaje(periodo_nombre),
    ).update(
        estado_alerta='descartada',
        fecha_revision=timezone.now(),
        revisado_por=usuario,
    )


NOMBRES_MESES = {
    1: 'enero',
    2: 'febrero',
    3: 'marzo',
    4: 'abril',
    5: 'mayo',
    6: 'junio',
    7: 'julio',
    8: 'agosto',
    9: 'septiembre',
    10: 'octubre',
    11: 'noviembre',
    12: 'diciembre',
}

# Único lugar que traduce la Frecuencia de un KPI a un intervalo de meses y
# al tipo_periodo real de PeriodoMedicion (Bloque 4). `obtener_intervalo_meses`
# se mantiene con la misma firma que ya usaban services/serializers previos
# a este bloque (no se duplica una segunda lógica paralela).
FRECUENCIA_INTERVALO = {
    'mensual': 1,
    'bimestral': 2,
    'trimestral': 3,
    'semestral': 6,
    'anual': 12,
}


def obtener_tipo_periodo(indicador):
    frecuencia = (indicador.frecuencia.nombre or '').lower()

    if 'bimestral' in frecuencia or 'bimensual' in frecuencia:
        return 'bimestral'

    if 'trimestral' in frecuencia:
        return 'trimestral'

    if 'semestral' in frecuencia:
        return 'semestral'

    if 'anual' in frecuencia:
        return 'anual'

    return 'mensual'


def obtener_intervalo_meses(indicador):
    return FRECUENCIA_INTERVALO[obtener_tipo_periodo(indicador)]


def sumar_meses(fecha, meses):
    mes = fecha.month - 1 + meses
    anio = fecha.year + mes // 12
    mes = mes % 12 + 1

    return date(anio, mes, 1)


def formatear_periodo(fecha_inicio, intervalo_meses=1):
    """Nombre legible de un periodo a partir de su mes de inicio.
    intervalo_meses=1 (mensual, default de siempre) -> 'enero 2027'.
    intervalo_meses>1 (bimestral/trimestral/semestral/anual) -> rango,
    ej. 'enero - febrero 2027'. Firma retrocompatible: todo llamador
    existente que no pase intervalo_meses sigue obteniendo el mismo
    resultado de antes."""
    if intervalo_meses <= 1:
        return f"{NOMBRES_MESES.get(fecha_inicio.month, fecha_inicio.month)} {fecha_inicio.year}"

    fecha_fin_mes = sumar_meses(fecha_inicio, intervalo_meses - 1)

    return (
        f"{NOMBRES_MESES.get(fecha_inicio.month, fecha_inicio.month)} - "
        f"{NOMBRES_MESES.get(fecha_fin_mes.month, fecha_fin_mes.month)} {fecha_fin_mes.year}"
    )


def obtener_primer_periodo_exigible(indicador):
    """C2: primer periodo que se exige medir. Es el periodo de la cuadrícula
    del plan anual (anclada al mes de inicio de su vigencia y avanzada según
    la frecuencia) que contiene la fecha de inicio del seguimiento del KPI.
    Ese primer periodo puede ser parcial: se mide desde ese día, pero su
    cierre es el de siempre. Si el seguimiento empieza después del fin de la
    vigencia, devuelve un mes posterior a la vigencia: no hay periodos."""
    intervalo = obtener_intervalo_meses(indicador)
    inicio_vigencia = indicador.fecha_inicio_vigencia
    fin_vigencia = indicador.fecha_fin_vigencia
    inicio = indicador.fecha_inicio_seguimiento

    if inicio > fin_vigencia:
        return sumar_meses(date(fin_vigencia.year, fin_vigencia.month, 1), 1)

    periodo = date(inicio_vigencia.year, inicio_vigencia.month, 1)
    mes_inicio = date(inicio.year, inicio.month, 1)

    while sumar_meses(periodo, intervalo) <= mes_inicio:
        periodo = sumar_meses(periodo, intervalo)

    return periodo


def obtener_siguiente_periodo_esperado(indicador, excluir_medicion_id=None):
    """Siguiente periodo a medir: el posterior a la última medición
    guardada (real u omisión), pero nunca anterior al primer periodo
    exigible (C2). Las mediciones retroactivas de periodos anteriores al
    inicio del seguimiento se conservan; los periodos intermedios no se
    exigen ni generan omisiones."""
    intervalo = obtener_intervalo_meses(indicador)

    primer_periodo = obtener_primer_periodo_exigible(indicador)

    precargadas = precargado(indicador, 'mediciones') if excluir_medicion_id is None else None

    if precargadas is not None:
        # Etapa 6 (M8): la de periodo más reciente entre las ya cargadas.
        ultima_medicion = max(
            (m for m in precargadas if m.periodo), key=lambda m: m.periodo.fecha_inicio, default=None,
        )
    else:
        ultima_medicion = (
            Medicion.objects
            .filter(indicador=indicador)
            .exclude(id=excluir_medicion_id)
            .select_related('periodo')
            .order_by('-periodo__fecha_inicio')
            .first()
        )

    if not ultima_medicion or not ultima_medicion.periodo:
        return primer_periodo

    ultimo_periodo = date(
        ultima_medicion.periodo.fecha_inicio.year,
        ultima_medicion.periodo.fecha_inicio.month,
        1,
    )

    return max(sumar_meses(ultimo_periodo, intervalo), primer_periodo)


def obtener_ultimo_dia_mes(fecha):
    if fecha.month == 12:
        siguiente_mes = date(fecha.year + 1, 1, 1)
    else:
        siguiente_mes = date(fecha.year, fecha.month + 1, 1)

    return siguiente_mes - date.resolution


def calcular_fecha_cierre_periodo(fecha_inicio_periodo, intervalo_meses):
    mes_final = sumar_meses(fecha_inicio_periodo, intervalo_meses - 1)

    return obtener_ultimo_dia_mes(mes_final)


def calcular_fecha_limite_registro(fecha_cierre, dias_plazo=None, fecha_inicio_periodo=None):
    """Límite inclusivo por inicio del período: calendario antes del corte,
    cinco hábiles desde 01/11/2026. Sin inicio explícito conserva calendario.
    dias_plazo permite reutilizar la configuración sin consultas repetidas.
    """
    from .models import ConfiguracionMediciones

    dias = dias_plazo if dias_plazo is not None else ConfiguracionMediciones.obtener().dias_plazo_registro

    from .plazos import limite_ordinario
    return limite_ordinario(fecha_cierre, fecha_inicio_periodo, dias)


def obtener_ampliaciones_del_periodo(indicador, fecha_inicio_periodo):
    """Etapa 5: solicitud autorizada y solicitud pendiente (como máximo una
    de cada una, por las restricciones únicas) del KPI en ese periodo."""
    from .models import SolicitudAmpliacionPlazo

    autorizada = None
    pendiente = None
    tipo_periodo = obtener_tipo_periodo(indicador)
    estados = [SolicitudAmpliacionPlazo.ESTADO_AUTORIZADA, SolicitudAmpliacionPlazo.ESTADO_PENDIENTE]
    precargadas = precargado(indicador, 'solicitudes_ampliacion')

    if precargadas is not None:
        # Etapa 6 (M8): mismos filtros, sobre las solicitudes ya cargadas.
        solicitudes = [
            s for s in precargadas
            if s.estado in estados
            and s.periodo.tipo_periodo == tipo_periodo
            and s.periodo.fecha_inicio == fecha_inicio_periodo
        ]
    else:
        solicitudes = SolicitudAmpliacionPlazo.objects.filter(
            indicador=indicador,
            periodo__tipo_periodo=tipo_periodo,
            periodo__fecha_inicio=fecha_inicio_periodo,
            estado__in=estados,
        )

    for solicitud in solicitudes:
        if solicitud.estado == SolicitudAmpliacionPlazo.ESTADO_AUTORIZADA:
            autorizada = solicitud
        else:
            pendiente = solicitud

    return autorizada, pendiente


def obtener_fecha_limite_efectiva(indicador, fecha_inicio_periodo, fecha_cierre, dias_plazo=None):
    """Etapa 5: punto ÚNICO que decide hasta cuándo puede registrarse la
    medición de un KPI en un periodo. Lo usan el registro, la consulta del
    siguiente periodo, las alertas y el cierre automático.

    Sin ampliación autorizada es el límite ordinario (cierre + plazo
    general). Con una ampliación autorizada es el mayor entre el límite
    ordinario actual y la fecha extraordinaria guardada al autorizar: un
    cambio posterior del plazo general nunca acorta una ampliación ya
    concedida. Solo afecta a ese KPI y ese periodo."""
    fecha_limite_ordinaria = calcular_fecha_limite_registro(fecha_cierre, dias_plazo, fecha_inicio_periodo)
    autorizada, pendiente = obtener_ampliaciones_del_periodo(indicador, fecha_inicio_periodo)
    fecha_limite = fecha_limite_ordinaria

    if autorizada and autorizada.fecha_limite_extraordinaria > fecha_limite:
        fecha_limite = autorizada.fecha_limite_extraordinaria

    return {
        'fecha_limite_registro': fecha_limite,
        'fecha_limite_ordinaria': fecha_limite_ordinaria,
        'ampliacion_autorizada': autorizada,
        'ampliacion_pendiente': pendiente,
    }


def obtener_o_crear_periodo(indicador, fecha_inicio_periodo):
    """Obtiene (o crea) el PeriodoMedicion real que corresponde al mes de
    inicio dado, según la frecuencia del KPI. Reutiliza PeriodoMedicion
    como catálogo compartido: dos KPI con la misma frecuencia y el mismo
    año reutilizan la misma fila (la relación con un indicador específico
    vive en Medicion.indicador + Medicion.periodo, no acá)."""
    tipo_periodo = obtener_tipo_periodo(indicador)
    intervalo = FRECUENCIA_INTERVALO[tipo_periodo]
    fecha_fin_periodo = calcular_fecha_cierre_periodo(fecha_inicio_periodo, intervalo)
    descripcion = formatear_periodo(fecha_inicio_periodo, intervalo).capitalize()

    periodo, _ = PeriodoMedicion.objects.get_or_create(
        tipo_periodo=tipo_periodo,
        fecha_inicio=fecha_inicio_periodo,
        fecha_fin=fecha_fin_periodo,
        defaults={
            'anio': fecha_inicio_periodo.year,
            'mes': fecha_inicio_periodo.month if tipo_periodo == 'mensual' else None,
            'descripcion': descripcion,
        },
    )

    return periodo


def obtener_o_crear_meta_vigente(indicador):
    """Centraliza la creación/reuso de la MetaKPI 'vigente' de un indicador,
    usada tanto por el registro manual de mediciones como por el cierre
    automático (Bloque 4). MetaKPI no se rediseña en este bloque: se sigue
    derivando de IndicadorKPI.valor_meta + su vigencia heredada del Plan
    anual (fecha_inicio_vigencia / fecha_fin_vigencia, ver Bloque 3)."""
    meta_existente = MetaKPI.objects.filter(
        indicador=indicador,
        estado='vigente',
    ).order_by('-fecha_inicio').first()

    if meta_existente:
        return meta_existente

    if indicador.valor_meta is None:
        raise ValueError('El KPI seleccionado no tiene una meta configurada.')

    meta, _ = MetaKPI.objects.get_or_create(
        indicador=indicador,
        valor_meta=indicador.valor_meta,
        fecha_inicio=indicador.fecha_inicio_vigencia,
        fecha_fin=indicador.fecha_fin_vigencia,
        estado='vigente',
    )

    return meta


def obtener_info_siguiente_periodo(indicador, fecha_referencia=None, dias_plazo=None):
    """Fuente ÚNICA de verdad (Bloque 4) sobre qué periodo corresponde
    registrar para un KPI y si está disponible ahora mismo. La usan tanto
    el endpoint `GET /mediciones/siguiente-periodo/` como la creación de
    Medicion (serializer) y el cierre automático (management command), para
    no duplicar la regla en varios lugares.

    Devuelve siempre las mismas claves:
      disponible, motivo, periodo_nombre, tipo_periodo,
      fecha_inicio_periodo, fecha_cierre, fecha_limite_registro,
      fecha_limite_ordinaria, ampliacion_autorizada, ampliacion_pendiente.

    Etapa 5: `fecha_limite_registro` es la fecha límite EFECTIVA (incluye
    una ampliación autorizada, ver obtener_fecha_limite_efectiva);
    `fecha_limite_ordinaria` es la del plazo general. Las dos ampliaciones
    son instancias de SolicitudAmpliacionPlazo o None.

    `fecha_cierre` es None únicamente cuando no hay un periodo concreto que
    evaluar todavía (KPI no autorizado, sin meta, o sin más periodos dentro
    de su vigencia) — el comando de cierre automático usa exactamente esa
    condición para saber cuándo dejar de intentar cerrar periodos de un KPI.
    """
    fecha_referencia = fecha_referencia or hoy()

    base = {
        'disponible': False,
        'motivo': '',
        'periodo_nombre': None,
        'tipo_periodo': None,
        'fecha_inicio_periodo': None,
        'fecha_cierre': None,
        'fecha_limite_registro': None,
        'fecha_limite_ordinaria': None,
        'ampliacion_autorizada': None,
        'ampliacion_pendiente': None,
        'inicio_seguimiento': None,
        'periodo_parcial': False,
    }

    if indicador.estado != 'autorizado':
        return {
            **base,
            'motivo': 'Solo se pueden registrar mediciones para KPI autorizados.',
        }

    if not indicador.valor_meta:
        return {
            **base,
            'motivo': 'El KPI seleccionado no tiene una meta configurada.',
        }

    tipo_periodo = obtener_tipo_periodo(indicador)
    intervalo = FRECUENCIA_INTERVALO[tipo_periodo]
    fecha_inicio_periodo = obtener_siguiente_periodo_esperado(indicador)

    fecha_fin_vigencia_mes = date(
        indicador.fecha_fin_vigencia.year,
        indicador.fecha_fin_vigencia.month,
        1,
    )

    if fecha_inicio_periodo > fecha_fin_vigencia_mes:
        return {
            **base,
            'tipo_periodo': tipo_periodo,
            'motivo': 'No existen más periodos pendientes dentro de la vigencia del KPI.',
        }

    fecha_cierre = calcular_fecha_cierre_periodo(fecha_inicio_periodo, intervalo)
    limites = obtener_fecha_limite_efectiva(indicador, fecha_inicio_periodo, fecha_cierre, dias_plazo)
    fecha_limite = limites['fecha_limite_registro']
    periodo_nombre = formatear_periodo(fecha_inicio_periodo, intervalo)

    info = {
        'disponible': False,
        'motivo': '',
        'periodo_nombre': periodo_nombre,
        'tipo_periodo': tipo_periodo,
        'fecha_inicio_periodo': fecha_inicio_periodo,
        'fecha_cierre': fecha_cierre,
        **limites,
        # C2: el primer periodo puede ser parcial (empieza a medirse el día
        # de inicio del seguimiento, no el primer día del periodo).
        'inicio_seguimiento': indicador.fecha_inicio_seguimiento,
        'periodo_parcial': fecha_inicio_periodo < indicador.fecha_inicio_seguimiento,
    }

    if fecha_referencia < fecha_cierre:
        info['motivo'] = f'El periodo {periodo_nombre} todavía no está disponible para registro.'
        return info

    if fecha_referencia <= fecha_limite:
        info['disponible'] = True
        return info

    pendiente = limites['ampliacion_pendiente']

    if pendiente and fecha_referencia <= pendiente.fecha_limite_maxima:
        # Etapa 5 (regla 7): vencido el plazo ordinario, una solicitud
        # pendiente no habilita el registro hasta que se autorice.
        info['motivo'] = (
            f'El plazo de registro del periodo {periodo_nombre} terminó el '
            f'{fecha_limite.strftime("%d/%m/%Y")}. La solicitud de días adicionales '
            'está pendiente de resolución: vas a poder registrar si se autoriza.'
        )
        return info

    info['motivo'] = (
        f'El periodo {periodo_nombre} venció su ventana de registro y está '
        'pendiente de cierre automático.'
    )
    return info


def evaluar_solicitud_ampliacion(indicador, fecha_referencia=None):
    """Etapa 5: decide si hoy puede pedirse una ampliación para el siguiente
    periodo del KPI (el único que puede estar pendiente, porque el registro
    es secuencial). Devuelve (info, motivo): motivo vacío si se puede.

    Reglas aprobadas: KPI que hoy admite registro (autorizado, con meta,
    plan no Cerrado), desde el cierre del periodo hasta el último día del
    plazo ordinario inclusive, sin otra solicitud pendiente ni una
    ampliación ya autorizada para ese periodo."""
    fecha_referencia = fecha_referencia or hoy()
    info = obtener_info_siguiente_periodo(indicador, fecha_referencia=fecha_referencia)

    if indicador.estado != 'autorizado' or info['fecha_cierre'] is None:
        return info, info['motivo']

    if indicador.esta_bloqueado():
        return info, 'El Plan anual o el Plan estratégico de este KPI están Cerrados.'

    periodo = info['periodo_nombre']

    if fecha_referencia < info['fecha_cierre']:
        return info, (
            f'Los días adicionales para el periodo {periodo} solo pueden pedirse desde '
            f'su cierre, el {info["fecha_cierre"].strftime("%d/%m/%Y")}.'
        )

    if info['ampliacion_autorizada']:
        return info, (
            f'El periodo {periodo} ya tiene una ampliación autorizada hasta el '
            f'{info["ampliacion_autorizada"].fecha_limite_extraordinaria.strftime("%d/%m/%Y")}.'
        )

    if info['ampliacion_pendiente']:
        return info, f'Ya existe una solicitud pendiente de días adicionales para el periodo {periodo}.'

    if fecha_referencia > info['fecha_limite_ordinaria']:
        return info, (
            f'El plazo ordinario del periodo {periodo} terminó el '
            f'{info["fecha_limite_ordinaria"].strftime("%d/%m/%Y")}: ya no pueden pedirse días adicionales.'
        )

    return info, ''


def responsables_vigentes(indicador):
    """Etapa 4 (auditoría M6): Ejecutores operativos asignados al KPI que
    siguen habilitados. Se recalcula al momento de notificar: una
    asignación cuyo usuario se inactivó o cambió de rol deja de recibir
    avisos sin necesidad de tocar la asignación."""
    from apps.usuarios.models import Usuario
    from apps.usuarios.permissions import ROL_EJECUTOR_OPERATIVO

    return Usuario.objects.filter(
        kpis_responsables__indicador=indicador,
        kpis_responsables__estado=True,
        is_active=True,
        estado=True,
        rol__nombre__iexact=ROL_EJECUTOR_OPERATIVO,
    ).distinct()


def motivo_no_admite_evidencias(medicion):
    """D2: '' si a la medición se le pueden adjuntar evidencias; si no, el
    motivo (omisión del sistema o plan Cerrado)."""
    if medicion.cierre_automatico:
        return 'No se pueden adjuntar evidencias a un periodo cerrado automáticamente sin registro.'

    if medicion.indicador.esta_bloqueado():
        return 'El Plan anual o el Plan estratégico de este KPI están Cerrados: no admite nuevas evidencias.'

    return ''


def adjuntar_evidencias(medicion, archivos, usuario, request=None):
    """D2: agrega archivos de evidencia a una medición. Cada archivo queda
    como un registro independiente y se conservan todos los anteriores
    (nunca se reemplaza ni se borra nada). Una entrada de bitácora por
    archivo, con el archivo, el usuario y la medición. Las validaciones de
    tipo, tamaño y cantidad las hace quien llama (serializers)."""
    import os

    from apps.auditoria.services import registrar_bitacora_obligatoria
    from .models import EvidenciaMedicion

    creadas = []

    for archivo in archivos:
        nombre_original = os.path.basename(getattr(archivo, 'name', '') or 'evidencia')[:255]
        evidencia = EvidenciaMedicion.objects.create(
            medicion=medicion,
            archivo=archivo,
            nombre_original=nombre_original,
            tamano=getattr(archivo, 'size', 0) or 0,
            tipo_contenido=(getattr(archivo, 'content_type', '') or '')[:100],
            subido_por=usuario,
        )
        creadas.append(evidencia)

        registrar_bitacora_obligatoria(
            usuario=usuario,
            accion='crear',
            modulo='Evidencias',
            descripcion=(
                f'Adjuntó la evidencia "{nombre_original}" ({evidencia.tamano} bytes) a la medición '
                f'#{medicion.id} del KPI {medicion.indicador.nombre} (periodo {medicion.periodo.descripcion}).'
            ),
            request=request,
        )

    return creadas


def notificar_sin_duplicar(usuario, tipo, titulo, mensaje, enlace):
    """Crea la notificación salvo que ese usuario ya tenga una igual (mismo
    tipo y enlace). Devuelve la notificación creada o None."""
    from apps.auditoria.models import Notificacion
    from apps.auditoria.services import crear_notificacion

    if usuario is None or Notificacion.objects.filter(usuario_destino=usuario, tipo=tipo, enlace=enlace).exists():
        return None

    return crear_notificacion(usuario_destino=usuario, tipo=tipo, titulo=titulo, mensaje=mensaje, enlace=enlace)


MODULO_AMPLIACIONES = 'Ampliaciones de plazo'


def enlace_solicitud_ampliacion(solicitud):
    return f'/mediciones?tab=solicitudes&solicitud={solicitud.id}'


def describir_solicitud_ampliacion(solicitud):
    return (
        f'la solicitud de ampliación #{solicitud.id} del KPI {solicitud.indicador.nombre} '
        f'(periodo {solicitud.periodo.descripcion})'
    )


def finalizar_solicitud_ampliacion(solicitud, estado, motivo, usuario=None, request=None):
    """Etapa 5: cierra una solicitud PENDIENTE como Vencida o Sin efecto,
    con su bitácora (del usuario que provocó el cambio o del Sistema) y el
    aviso al solicitante. Nunca borra la solicitud ni toca mediciones."""
    from apps.auditoria.services import registrar_bitacora_obligatoria, registrar_bitacora_sistema
    from .models import SolicitudAmpliacionPlazo

    solicitud.estado = estado
    solicitud.fecha_resolucion = timezone.now()
    solicitud.observacion_revision = motivo
    solicitud.save(update_fields=['estado', 'fecha_resolucion', 'observacion_revision'])

    texto_estado = 'vencida' if estado == SolicitudAmpliacionPlazo.ESTADO_VENCIDA else 'sin efecto'
    descripcion = f'L{describir_solicitud_ampliacion(solicitud)[1:]} quedó {texto_estado}: {motivo}'

    if usuario is None:
        registrar_bitacora_sistema('actualizar', MODULO_AMPLIACIONES, descripcion)
    else:
        registrar_bitacora_obligatoria(
            usuario=usuario, accion='actualizar', modulo=MODULO_AMPLIACIONES, descripcion=descripcion, request=request,
        )

    if usuario is None or solicitud.solicitante_id != usuario.id:
        notificar_sin_duplicar(
            solicitud.solicitante,
            tipo=f'ampliacion_{estado}',
            titulo='Solicitud de días adicionales vencida' if texto_estado == 'vencida' else 'Solicitud de días adicionales sin efecto',
            mensaje=(
                f'Tu solicitud de días adicionales para el KPI "{solicitud.indicador.nombre}" '
                f'(periodo {solicitud.periodo.descripcion}) quedó {texto_estado}: {motivo}'
            ),
            enlace=enlace_solicitud_ampliacion(solicitud),
        )

    return solicitud


def dejar_sin_efecto_solicitudes_pendientes(indicador, motivo, periodo=None, usuario=None, request=None):
    """Etapa 5: las solicitudes pendientes del KPI (o de uno de sus
    periodos) que perdieron su objeto — se registró la medición o el KPI
    fue anulado — pasan a Sin efecto. Devuelve cuántas cambió."""
    from .models import SolicitudAmpliacionPlazo

    pendientes = SolicitudAmpliacionPlazo.objects.filter(indicador=indicador)

    if periodo is not None:
        pendientes = pendientes.filter(periodo=periodo)

    return _dejar_sin_efecto(pendientes, motivo, usuario, request)


def dejar_sin_efecto_por_cierre_de_plan(motivo, usuario, request=None, plan_anual=None, plan_estrategico=None):
    """Ajuste de la Etapa 5: al Cerrar un Plan anual o un Plan estratégico,
    sus solicitudes PENDIENTES pasan a Sin efecto dentro de la misma
    operación de cierre (misma transacción de la petición). No toca las que
    ya están Autorizadas, Rechazadas, Vencidas, Retiradas o Sin efecto."""
    from .models import SolicitudAmpliacionPlazo

    pendientes = SolicitudAmpliacionPlazo.objects.all()

    if plan_anual is not None:
        pendientes = pendientes.filter(indicador__objetivo_especifico__plan_anual=plan_anual)

    if plan_estrategico is not None:
        pendientes = pendientes.filter(indicador__objetivo_especifico__plan_anual__plan_estrategico=plan_estrategico)

    return _dejar_sin_efecto(pendientes, motivo, usuario, request)


def _dejar_sin_efecto(solicitudes, motivo, usuario, request):
    from .models import SolicitudAmpliacionPlazo

    # Solo pendientes, bloqueadas: un cierre repetido o simultáneo no las
    # procesa dos veces (ya no estarán pendientes).
    ids = list(solicitudes.filter(estado=SolicitudAmpliacionPlazo.ESTADO_PENDIENTE).values_list('id', flat=True))
    # FOR UPDATE OF solo la solicitud: no bloquea el KPI, el periodo ni el usuario.
    pendientes = SolicitudAmpliacionPlazo.objects.select_for_update(of=('self',)).select_related(
        'indicador', 'periodo', 'solicitante',
    ).filter(id__in=ids, estado=SolicitudAmpliacionPlazo.ESTADO_PENDIENTE).order_by('id')

    cantidad = 0

    for solicitud in pendientes:
        finalizar_solicitud_ampliacion(
            solicitud, SolicitudAmpliacionPlazo.ESTADO_SIN_EFECTO, motivo, usuario=usuario, request=request,
        )
        cantidad += 1

    return cantidad


def procesar_solicitudes_ampliacion(fecha_referencia=None):
    """Etapa 5: paso previo del cierre automático (tarea del Sistema).
    - Pendiente después de su fecha máxima (según la regla de su período)
      -> Vencida (regla 9).
    - Pendiente de un KPI anulado, de un plan Cerrado o de un periodo que
      ya tiene medición -> Sin efecto.
    Cada solicitud se procesa en su propia transacción: si falla, queda
    como estaba y se informa el error, sin frenar las demás."""
    from .models import SolicitudAmpliacionPlazo

    fecha_referencia = fecha_referencia or hoy()
    vencidas = 0
    sin_efecto = 0
    errores = []

    pendientes = SolicitudAmpliacionPlazo.objects.select_related(
        'indicador',
        'indicador__objetivo_especifico__plan_anual__plan_estrategico',
        'periodo',
        'solicitante',
    ).filter(estado=SolicitudAmpliacionPlazo.ESTADO_PENDIENTE).order_by('id')

    for solicitud in pendientes:
        indicador = solicitud.indicador

        if fecha_referencia > solicitud.fecha_limite_maxima:
            estado = SolicitudAmpliacionPlazo.ESTADO_VENCIDA
            motivo = (
                'no se resolvió dentro del plazo máximo, que terminó el '
                f'{solicitud.fecha_limite_maxima.strftime("%d/%m/%Y")}.'
            )
        elif indicador.estado == 'anulado':
            estado, motivo = SolicitudAmpliacionPlazo.ESTADO_SIN_EFECTO, 'el KPI fue anulado.'
        elif indicador.esta_bloqueado():
            estado = SolicitudAmpliacionPlazo.ESTADO_SIN_EFECTO
            motivo = 'el Plan anual o el Plan estratégico del KPI está Cerrado.'
        elif Medicion.objects.filter(indicador=indicador, periodo=solicitud.periodo).exists():
            estado, motivo = SolicitudAmpliacionPlazo.ESTADO_SIN_EFECTO, 'el periodo ya tiene una medición.'
        else:
            continue

        try:
            with transaction.atomic():
                actual = SolicitudAmpliacionPlazo.objects.select_for_update().get(pk=solicitud.pk)

                if actual.estado != SolicitudAmpliacionPlazo.ESTADO_PENDIENTE:
                    continue

                finalizar_solicitud_ampliacion(solicitud, estado, motivo)
        except Exception as error:
            errores.append({
                'indicador_id': indicador.id,
                'indicador': indicador.nombre,
                'periodo': solicitud.periodo.descripcion,
                'error': f'Solicitud de ampliación #{solicitud.id}: {error}',
            })
            continue

        if estado == SolicitudAmpliacionPlazo.ESTADO_VENCIDA:
            vencidas += 1
        else:
            sin_efecto += 1

    return {'vencidas': vencidas, 'sin_efecto': sin_efecto, 'errores': errores}


def registrar_alerta_periodo_sin_registro(medicion, info):
    """Etapa 3 (auditoría C3): una alerta pendiente por cada omisión, ligada
    a su Medicion. Idempotente: si ya existe para esa medición, no la
    duplica. No modifica ninguna alerta existente."""
    existente = Alerta.objects.filter(
        medicion=medicion,
        tipo_alerta=TIPO_ALERTA_PERIODO_SIN_REGISTRO,
    ).first()

    if existente:
        return existente

    alerta = Alerta.objects.create(
        indicador=medicion.indicador,
        medicion=medicion,
        tipo_alerta=TIPO_ALERTA_PERIODO_SIN_REGISTRO,
        mensaje=(
            f'El indicador "{medicion.indicador.nombre}" quedó sin registro en el periodo '
            f'{info["periodo_nombre"]} (cierre {info["fecha_cierre"].strftime("%d/%m/%Y")}, '
            f'plazo vencido el {info["fecha_limite_registro"].strftime("%d/%m/%Y")}'
            f'{", incluida la ampliación autorizada" if info["fecha_limite_registro"] != info.get("fecha_limite_ordinaria", info["fecha_limite_registro"]) else ""}). '
            'El sistema lo cerró automáticamente sin resultado.'
        ),
        estado_alerta='pendiente',
    )

    # Los avisos individuales a responsables de KPI (Etapa 4) se retiraron
    # del flujo junto con esa función: la alerta sigue visible en el centro
    # de notificaciones, como antes de la Etapa 4.
    return alerta


def cerrar_mediciones_vencidas(fecha_referencia=None):
    """Servicio central del management command `cerrar_mediciones_vencidas`
    (Bloque 4). Por cada KPI autorizado, cierra EN ORDEN todos los periodos
    cuyo plazo de registro configurado (ver ConfiguracionMediciones) ya
    venció sin medición manual, creando una Medicion "Sin registro"
    (valor_resultado=NULL, cierre_automatico=True, registrado_por=NULL) y su
    alerta "Periodo sin registro" — Etapa 3 (C3), en lugar del 0.00 de antes.

    Idempotente: se apoya en `obtener_info_siguiente_periodo`, que siempre
    calcula el siguiente periodo a partir de la última Medicion ya
    guardada (real u omisión) — si un periodo ya fue cerrado (automática o manualmente), la
    siguiente llamada directamente evalúa el periodo posterior. Además
    verifica explícitamente que no exista ya una Medicion para ese
    (indicador, periodo) antes de crear, sin depender únicamente de que la
    constraint `unique_medicion_por_indicador_periodo` lo impida."""
    fecha_referencia = fecha_referencia or hoy()

    kpi_revisados = 0
    cierres_creados = 0
    kpi_bloqueados = 0
    kpi_en_espera = 0
    detalle = []

    # Etapa 5: antes de cerrar, las solicitudes de ampliación sin resolver
    # a tiempo pasan a Vencida y las que perdieron su objeto, a Sin efecto.
    solicitudes = procesar_solicitudes_ampliacion(fecha_referencia)
    errores = list(solicitudes['errores'])

    indicadores = IndicadorKPI.objects.filter(estado='autorizado').select_related(
        'frecuencia',
        'objetivo_especifico',
        'objetivo_especifico__plan_anual',
        'objetivo_especifico__plan_anual__plan_estrategico',
    )

    for indicador in indicadores:
        kpi_revisados += 1

        if indicador.esta_bloqueado():
            # Plan anual o Plan estratégico Cerrado: la inmutabilidad ya
            # implementada tiene prioridad, el cierre automático no debe
            # tocar nada debajo de un Plan Cerrado.
            kpi_bloqueados += 1
            continue

        while True:
            info = obtener_info_siguiente_periodo(indicador, fecha_referencia=fecha_referencia)

            if info['disponible'] or info['fecha_cierre'] is None:
                # Vigente/en ventana todavía, o no quedan periodos: nada
                # que cerrar para este KPI por ahora.
                break

            if fecha_referencia <= info['fecha_limite_registro']:
                # Ventana aún no vence: se detiene, tal como exige la regla
                # de no saltar/adelantar periodos. Etapa 5: es la fecha
                # límite efectiva (incluye una ampliación autorizada).
                break

            pendiente = info['ampliacion_pendiente']

            if pendiente and fecha_referencia <= pendiente.fecha_limite_maxima:
                # Etapa 5 (regla 6): una solicitud pendiente detiene el
                # cierre de este periodo hasta su fecha máxima inclusive.
                # Pasada esa fecha ya no detiene nada, aunque no se haya
                # podido marcar como Vencida.
                kpi_en_espera += 1
                break

            try:
                with transaction.atomic():
                    periodo = obtener_o_crear_periodo(indicador, info['fecha_inicio_periodo'])

                    ya_existe = Medicion.objects.select_for_update().filter(
                        indicador=indicador,
                        periodo=periodo,
                    ).exists()

                    if ya_existe:
                        # Verificación defensiva de idempotencia: no debería
                        # ocurrir dado que obtener_info_siguiente_periodo ya
                        # excluye periodos con Medicion existente, pero no se
                        # depende únicamente de la constraint de base de datos.
                        break

                    meta = obtener_o_crear_meta_vigente(indicador)

                    # Etapa 3 (auditoría C3): la omisión no tiene
                    # resultado (NULL) ni se clasifica con los rangos del
                    # KPI; queda en "Sin registro". Sustituye el criterio
                    # anterior de cerrar toda omisión en 0.00.
                    estado_sin_registro = obtener_estado_sin_registro()

                    if estado_sin_registro is None:
                        raise ValueError(
                            f'No existe el estado "{ESTADO_SIN_REGISTRO}" en el catálogo '
                            '(migración indicadores.0015).'
                        )

                    medicion = Medicion.objects.create(
                        indicador=indicador,
                        meta=meta,
                        estado_cumplimiento=estado_sin_registro,
                        periodo=periodo,
                        registrado_por=None,
                        fecha_medicion=info['fecha_cierre'],
                        valor_resultado=None,
                        cierre_automatico=True,
                    )

                    # El promedio acumulado no cambia (las omisiones no
                    # participan), así que la alerta de cumplimiento no se
                    # toca. La de periodo vencido se resuelve y la
                    # trazabilidad pasa a la alerta "Periodo sin registro".
                    resolver_alertas_periodo_vencido(medicion, usuario=None)
                    registrar_alerta_periodo_sin_registro(medicion, info)
            except Exception as error:
                errores.append({
                    'indicador_id': indicador.id,
                    'indicador': indicador.nombre,
                    'periodo': info['periodo_nombre'],
                    'error': str(error),
                })
                break

            cierres_creados += 1
            detalle.append({
                'indicador_id': indicador.id,
                'indicador': indicador.nombre,
                'periodo': info['periodo_nombre'],
                'medicion_id': medicion.id,
            })
            # Continúa el while: puede haber más de un periodo vencido
            # atrasado (Bloque 4, punto 8) — se procesan en orden hasta
            # llegar a uno que ya no esté vencido o hasta agotar el año.

    return {
        'kpi_revisados': kpi_revisados,
        'cierres_creados': cierres_creados,
        'kpi_bloqueados': kpi_bloqueados,
        'kpi_en_espera': kpi_en_espera,
        'solicitudes_vencidas': solicitudes['vencidas'],
        'solicitudes_sin_efecto': solicitudes['sin_efecto'],
        'errores': errores,
        'detalle': detalle,
    }


def redactar_alerta_periodo_pendiente(indicador, periodo_nombre, fecha_cierre, limites, fecha_referencia):
    """Mensaje y título de la alerta 'Periodo vencido sin medición' según la
    fecha límite efectiva (Etapa 5). Siempre incluye
    marca_periodo_en_mensaje(periodo_nombre), que la deduplica y resuelve."""
    fecha_limite = limites['fecha_limite_registro']
    ampliado = fecha_limite != limites['fecha_limite_ordinaria']
    pendiente = limites['ampliacion_pendiente']
    cierre_texto = fecha_cierre.strftime('%d/%m/%Y')
    limite_texto = fecha_limite.strftime('%d/%m/%Y')

    if fecha_referencia <= fecha_limite:
        if ampliado:
            return (
                f'El indicador "{indicador.nombre}" tiene pendiente el registro del '
                f'periodo de {periodo_nombre} (cierre {cierre_texto}). Tiene una ampliación '
                f'autorizada: puede registrarse hasta el {limite_texto}.'
            ), 'Periodo pendiente de registro (plazo ampliado)'

        return (
            f'El indicador "{indicador.nombre}" tiene pendiente el registro del '
            f'periodo de {periodo_nombre} (cierre {cierre_texto}). Puede registrarse '
            f'hasta el {limite_texto}.'
        ), 'Periodo pendiente de registro'

    if pendiente and fecha_referencia <= pendiente.fecha_limite_maxima:
        return (
            f'El indicador "{indicador.nombre}" tiene vencido el periodo de {periodo_nombre} '
            f'(cierre {cierre_texto}): el plazo de registro terminó el {limite_texto}. Hay una '
            'solicitud de días adicionales pendiente de resolución; si no se autoriza, el '
            'sistema cerrará el periodo como "Sin registro".'
        ), 'Periodo con plazo vencido y ampliación pendiente'

    return (
        f'El indicador "{indicador.nombre}" tiene vencido el periodo de {periodo_nombre} '
        f'(cierre {cierre_texto}): el plazo de registro terminó el {limite_texto} y '
        'el sistema lo cerrará como "Sin registro".'
    ), 'Periodo con plazo de registro vencido'


def actualizar_alertas_por_ampliacion(solicitud, usuario, fecha_referencia=None):
    """Etapa 5: al autorizar una ampliación, la alerta pendiente del periodo
    deja de estar vigente (se descarta, sin reescribir su mensaje: queda
    como historial) y se crea otra con la fecha límite extraordinaria. Si
    el periodo todavía no tenía alerta, no se crea ninguna: la tarea diaria
    la generará ya con la fecha efectiva."""
    fecha_referencia = fecha_referencia or hoy()
    indicador = solicitud.indicador
    intervalo = obtener_intervalo_meses(indicador)
    inicio = solicitud.periodo.fecha_inicio
    periodo_nombre = formatear_periodo(date(inicio.year, inicio.month, 1), intervalo)
    marca = marca_periodo_en_mensaje(periodo_nombre)

    anteriores = Alerta.objects.filter(
        indicador=indicador, tipo_alerta=TIPO_ALERTA_PERIODO_VENCIDO, mensaje__icontains=marca,
    )

    if not anteriores.exists():
        return None

    anteriores.filter(estado_alerta='pendiente').update(
        estado_alerta='descartada', fecha_revision=timezone.now(), revisado_por=usuario,
    )

    fecha_cierre = calcular_fecha_cierre_periodo(date(inicio.year, inicio.month, 1), intervalo)
    limites = obtener_fecha_limite_efectiva(indicador, inicio, fecha_cierre)
    mensaje, _ = redactar_alerta_periodo_pendiente(
        indicador, periodo_nombre, fecha_cierre, limites, fecha_referencia,
    )

    # El solicitante recibe su propio aviso de la autorización (en la vista).
    return Alerta.objects.create(
        indicador=indicador,
        medicion=None,
        tipo_alerta=TIPO_ALERTA_PERIODO_VENCIDO,
        mensaje=mensaje,
        estado_alerta='pendiente',
    )


def generar_alertas_periodos_vencidos(fecha_referencia=None):
    fecha_referencia = fecha_referencia or hoy()

    total_kpi_revisados = 0
    total_alertas_creadas = 0
    total_omitidas = 0
    detalle = []

    indicadores = IndicadorKPI.objects.filter(estado='autorizado').select_related(
        'frecuencia',
        'objetivo_especifico',
        'objetivo_especifico__plan_anual',
        'objetivo_especifico__plan_anual__plan_estrategico',
    )

    for indicador in indicadores:
        total_kpi_revisados += 1

        # Etapa 4 (M6): un KPI de un Plan anual o Plan estratégico Cerrado
        # ya no admite registros; no tiene sentido alertar por él (mismo
        # criterio que cerrar_mediciones_vencidas). Los anulados y en
        # borrador ya quedan fuera por el filtro estado='autorizado'.
        if indicador.esta_bloqueado():
            continue

        periodo_esperado = obtener_siguiente_periodo_esperado(indicador)

        if not periodo_esperado:
            continue

        fecha_fin_kpi = date(
            indicador.fecha_fin_vigencia.year,
            indicador.fecha_fin_vigencia.month,
            1,
        )

        if periodo_esperado > fecha_fin_kpi:
            continue

        intervalo = obtener_intervalo_meses(indicador)
        fecha_cierre = calcular_fecha_cierre_periodo(periodo_esperado, intervalo)

        if fecha_cierre >= fecha_referencia:
            continue

        periodo_nombre = formatear_periodo(periodo_esperado, intervalo)

        ya_existe = Alerta.objects.filter(
            indicador=indicador,
            tipo_alerta=TIPO_ALERTA_PERIODO_VENCIDO,
            mensaje__icontains=marca_periodo_en_mensaje(periodo_nombre),
        ).exists()

        if ya_existe:
            total_omitidas += 1
            detalle.append({
                'indicador_id': indicador.id,
                'indicador': indicador.nombre,
                'periodo': periodo_nombre,
                'accion': 'omitida',
            })
            continue

        # Etapa 4 (M6): el mensaje respeta el plazo adicional configurado.
        # Antes decía "vencido" desde el día siguiente al cierre, aunque el
        # periodo todavía podía registrarse. Etapa 5: usa la fecha límite
        # efectiva (con una ampliación autorizada, si existe).
        limites = obtener_fecha_limite_efectiva(indicador, periodo_esperado, fecha_cierre)
        mensaje, _ = redactar_alerta_periodo_pendiente(
            indicador, periodo_nombre, fecha_cierre, limites, fecha_referencia,
        )

        Alerta.objects.create(
            indicador=indicador,
            medicion=None,
            tipo_alerta=TIPO_ALERTA_PERIODO_VENCIDO,
            mensaje=mensaje,
            estado_alerta='pendiente',
        )

        total_alertas_creadas += 1
        detalle.append({
            'indicador_id': indicador.id,
            'indicador': indicador.nombre,
            'periodo': periodo_nombre,
            'accion': 'creada',
        })

    return {
        'revisados': total_kpi_revisados,
        'creadas': total_alertas_creadas,
        'omitidas': total_omitidas,
        'detalle': detalle,
    }


def resumen_ponderacion_kpi_ambito(plan_anual, objetivo_general, excluir_id=None):
    """Suma de IndicadorKPI.ponderacion ya configuradas dentro del ámbito
    (plan_anual, objetivo_general) — regla 5/6 confirmada por Hernán: el
    100% del cumplimiento anual de un Objetivo general se reparte entre
    TODOS los KPI de ese año y ese objetivo general, sin distinguir si
    llegan a él por un Objetivo específico real o por ser KPI directos
    (ambos resuelven al mismo ámbito, ver IndicadorKPI.plan_anual/
    .objetivo_general). `excluir_id` permite calcular "cuánto hay en los
    DEMÁS KPI del ámbito" al validar un KPI nuevo o editado.

    Un KPI sin ponderacion asignada (None) NO cuenta como 0%: queda fuera
    de la suma, como "pendiente de ponderar" (distribución en
    preparación), nunca como parte ya distribuida.

    Etapa 1 (auditoría M1): un KPI anulado conserva su `ponderacion`
    guardada como dato histórico, pero ya no es vigente — queda fuera de
    la suma y libera ese porcentaje para los KPI que siguen en Borrador o
    Autorizado."""
    from decimal import Decimal

    kpis = IndicadorKPI.objects.filter(
        objetivo_especifico__plan_anual=plan_anual,
        objetivo_especifico__objetivo_general=objetivo_general,
        ponderacion__isnull=False,
    ).exclude(estado='anulado')

    if excluir_id is not None:
        kpis = kpis.exclude(id=excluir_id)

    total_asignado = sum((kpi.ponderacion for kpi in kpis), Decimal('0'))

    return {
        'total_asignado': total_asignado,
        'pendiente': Decimal('100') - total_asignado,
        'completo': total_asignado == Decimal('100'),
    }

