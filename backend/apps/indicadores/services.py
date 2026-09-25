from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .models import Alerta, EstadoCumplimiento, IndicadorKPI, Medicion, MetaKPI, PeriodoMedicion, RangoKPI


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
    porcentaje = calcular_porcentaje_cumplimiento(
        valor_resultado=valor_resultado,
        valor_meta=meta.valor_meta,
    )

    # Se clasifica sobre el mismo valor redondeado a 2 decimales que ve el
    # usuario (porcentaje_cumplimiento en pantalla), para que el estado
    # mostrado sea siempre coherente con el número mostrado.
    porcentaje_para_clasificar = round(porcentaje, 2)

    estado = obtener_estado_por_cumplimiento(
        indicador=indicador,
        porcentaje_cumplimiento=porcentaje_para_clasificar,
    )

    return estado


PLANTILLA_RANGOS_PROVISIONALES = (
    # (nombre del EstadoCumplimiento real, valor_minimo, valor_maximo)
    # valor_maximo=None => sin límite superior.
    ('Incumplido', Decimal('0'), Decimal('70')),
    ('En riesgo', Decimal('70'), Decimal('85')),
    ('Favorable', Decimal('85'), None),
)
"""Plantilla ÚNICA y centralizada usada para generar los RangoKPI iniciales
de un KPI (provisional, pendiente de validación con el cliente). La
clasificación de mediciones NUNCA lee esta plantilla directamente: siempre
consulta los RangoKPI ya guardados en base de datos. Cambiar los valores acá
solo afecta a los rangos que se generen de ahora en adelante."""


def obtener_estados_cumplimiento_plantilla():
    nombres = [nombre for nombre, _, _ in PLANTILLA_RANGOS_PROVISIONALES]
    estados = EstadoCumplimiento.objects.filter(nombre__in=nombres, estado=True)
    return {estado.nombre: estado for estado in estados}


def crear_rangos_provisionales(indicador):
    """Crea los RangoKPI provisionales de un KPI que todavía no tenga ninguno
    para ese estado. Idempotente: si ya existe un rango para ese
    (indicador, estado_cumplimiento), no lo duplica ni lo modifica."""
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


def actualizar_rangos_a_plantilla(indicador):
    """Actualiza a los valores provisionales los RangoKPI que ya existen
    para un KPI, emparejando por estado_cumplimiento. No crea filas nuevas
    ni elimina ninguna; solo ajusta valor_minimo/valor_maximo si difieren."""
    estados = obtener_estados_cumplimiento_plantilla()
    actualizados = 0

    for nombre_estado, minimo, maximo in PLANTILLA_RANGOS_PROVISIONALES:
        estado_cumplimiento = estados.get(nombre_estado)

        if not estado_cumplimiento:
            continue

        rango = RangoKPI.objects.filter(
            indicador=indicador,
            estado_cumplimiento=estado_cumplimiento,
        ).first()

        if not rango:
            continue

        if rango.valor_minimo != minimo or rango.valor_maximo != maximo:
            rango.valor_minimo = minimo
            rango.valor_maximo = maximo
            rango.save(update_fields=['valor_minimo', 'valor_maximo'])
            actualizados += 1

    return actualizados


def configurar_rangos_provisionales_para_todos():
    """Revisa todos los KPI existentes y deja configurados sus RangoKPI
    provisionales:
    - Si el KPI no tiene ningún rango, crea los tres de la plantilla.
    - Si ya tiene exactamente los tres rangos esperados (uno por cada
      estado de la plantilla), los actualiza a los valores provisionales.
    - Si tiene una configuración distinta (cantidad o estados que no
      coinciden con lo esperado), NO la toca: la reporta como omitida para
      revisión manual.
    Es reproducible: correrlo de nuevo no duplica ni rompe nada.
    """
    nombres_plantilla = {nombre for nombre, _, _ in PLANTILLA_RANGOS_PROVISIONALES}

    kpi_procesados = 0
    rangos_creados_total = 0
    rangos_actualizados_total = 0
    detalle = []

    with transaction.atomic():
        for indicador in IndicadorKPI.objects.all().order_by('id'):
            kpi_procesados += 1
            rangos_existentes = list(
                RangoKPI.objects.filter(indicador=indicador).select_related('estado_cumplimiento')
            )

            if not rangos_existentes:
                creados = crear_rangos_provisionales(indicador)
                rangos_creados_total += creados
                detalle.append({
                    'indicador_id': indicador.id,
                    'indicador': indicador.nombre,
                    'accion': 'creado',
                    'rangos_creados': creados,
                })
                continue

            nombres_existentes = [r.estado_cumplimiento.nombre for r in rangos_existentes]

            coincide_estructura = (
                len(rangos_existentes) == len(nombres_plantilla)
                and set(nombres_existentes) == nombres_plantilla
                and len(nombres_existentes) == len(set(nombres_existentes))
            )

            if not coincide_estructura:
                detalle.append({
                    'indicador_id': indicador.id,
                    'indicador': indicador.nombre,
                    'accion': 'omitido',
                    'motivo': (
                        'Tiene una configuración de RangoKPI distinta a la esperada '
                        f'({len(rangos_existentes)} rango(s): '
                        f'{", ".join(nombres_existentes) or "ninguno"}). '
                        'Revisar manualmente antes de modificar.'
                    ),
                })
                continue

            actualizados = actualizar_rangos_a_plantilla(indicador)
            rangos_actualizados_total += actualizados
            detalle.append({
                'indicador_id': indicador.id,
                'indicador': indicador.nombre,
                'accion': 'actualizado' if actualizados else 'sin cambios',
                'rangos_actualizados': actualizados,
            })

    return {
        'kpi_procesados': kpi_procesados,
        'rangos_creados': rangos_creados_total,
        'rangos_actualizados': rangos_actualizados_total,
        'detalle': detalle,
    }


def recalcular_mediciones_pendientes():
    """Recalcula ÚNICAMENTE las mediciones cuyo estado_cumplimiento actual
    es el fallback técnico 'Pendiente de actualización', y solo si el KPI
    correspondiente ya tiene RangoKPI válidos que permitan clasificarlas.

    No toca mediciones que ya estén en Favorable/En riesgo/Incumplido, no
    modifica valor_resultado ni ningún otro campo, y no recalcula la
    fórmula: usa el mismo cálculo existente (Medicion.calcular_cumplimiento)
    únicamente para volver a consultar RangoKPI con el resultado ya
    obtenido.
    """
    estado_pendiente = EstadoCumplimiento.objects.filter(
        nombre__iexact='Pendiente de actualización',
    ).first()

    if not estado_pendiente:
        return {'revisadas': 0, 'recalculadas': 0, 'detalle': []}

    mediciones = Medicion.objects.filter(
        estado_cumplimiento=estado_pendiente,
    ).select_related('indicador', 'meta', 'estado_cumplimiento')

    revisadas = 0
    recalculadas = 0
    detalle = []

    with transaction.atomic():
        for medicion in mediciones:
            revisadas += 1

            porcentaje = round(medicion.calcular_cumplimiento(), 2)

            nuevo_estado = obtener_estado_por_cumplimiento(
                indicador=medicion.indicador,
                porcentaje_cumplimiento=porcentaje,
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
                'porcentaje_cumplimiento': str(porcentaje),
                'estado_anterior': estado_pendiente.nombre,
                'estado_nuevo': nuevo_estado.nombre,
            })

    return {
        'revisadas': revisadas,
        'recalculadas': recalculadas,
        'detalle': detalle,
    }


def generar_alerta_para_medicion(medicion):
    estado_nombre = medicion.estado_cumplimiento.nombre.lower()
    porcentaje = calcular_porcentaje_cumplimiento(
        valor_resultado=medicion.valor_resultado,
        valor_meta=medicion.meta.valor_meta,
    )

    if estado_nombre == 'favorable':
        Alerta.objects.filter(
            indicador=medicion.indicador,
            medicion=medicion,
            estado_alerta='pendiente',
        ).update(
            estado_alerta='descartada',
            fecha_revision=timezone.now(),
        )
        return None

    tipo_alerta = f'Indicador {medicion.estado_cumplimiento.nombre}'
    mensaje = (
        f'El indicador "{medicion.indicador.nombre}" presenta un cumplimiento '
        f'del {round(porcentaje, 2)}%, por lo que requiere seguimiento.'
    )

    alerta_existente = Alerta.objects.filter(
        indicador=medicion.indicador,
        medicion=medicion,
        estado_alerta='pendiente',
    ).first()

    if alerta_existente:
        alerta_existente.tipo_alerta = tipo_alerta
        alerta_existente.mensaje = mensaje
        alerta_existente.save()
        return alerta_existente

    return Alerta.objects.create(
        indicador=medicion.indicador,
        medicion=medicion,
        tipo_alerta=tipo_alerta,
        mensaje=mensaje,
        estado_alerta='pendiente',
    )


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
        tipo_alerta='Periodo vencido sin medición',
        estado_alerta='pendiente',
        mensaje__icontains=periodo_nombre,
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


def obtener_siguiente_periodo_esperado(indicador, excluir_medicion_id=None):
    intervalo = obtener_intervalo_meses(indicador)

    primer_periodo = date(
        indicador.fecha_inicio_vigencia.year,
        indicador.fecha_inicio_vigencia.month,
        1,
    )

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

    return sumar_meses(ultimo_periodo, intervalo)


def obtener_ultimo_dia_mes(fecha):
    if fecha.month == 12:
        siguiente_mes = date(fecha.year + 1, 1, 1)
    else:
        siguiente_mes = date(fecha.year, fecha.month + 1, 1)

    return siguiente_mes - date.resolution


def calcular_fecha_cierre_periodo(fecha_inicio_periodo, intervalo_meses):
    mes_final = sumar_meses(fecha_inicio_periodo, intervalo_meses - 1)

    return obtener_ultimo_dia_mes(mes_final)


VENTANA_REGISTRO_DIAS = 5
"""Ventana oficial del proyecto (Bloque 4): la medición manual puede
registrarse el mismo día del cierre del periodo y durante los 5 días
calendario siguientes."""


def calcular_fecha_limite_registro(fecha_cierre):
    return fecha_cierre + timedelta(days=VENTANA_REGISTRO_DIAS)


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


def obtener_info_siguiente_periodo(indicador, fecha_referencia=None):
    """Fuente ÚNICA de verdad (Bloque 4) sobre qué periodo corresponde
    registrar para un KPI y si está disponible ahora mismo. La usan tanto
    el endpoint `GET /mediciones/siguiente-periodo/` como la creación de
    Medicion (serializer) y el cierre automático (management command), para
    no duplicar la regla en varios lugares.

    Devuelve siempre las mismas claves:
      disponible, motivo, periodo_nombre, tipo_periodo,
      fecha_inicio_periodo, fecha_cierre, fecha_limite_registro.

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
    fecha_limite = calcular_fecha_limite_registro(fecha_cierre)
    periodo_nombre = formatear_periodo(fecha_inicio_periodo, intervalo)

    info = {
        'disponible': False,
        'motivo': '',
        'periodo_nombre': periodo_nombre,
        'tipo_periodo': tipo_periodo,
        'fecha_inicio_periodo': fecha_inicio_periodo,
        'fecha_cierre': fecha_cierre,
        'fecha_limite_registro': fecha_limite,
    }

    if fecha_referencia < fecha_cierre:
        info['motivo'] = f'El periodo {periodo_nombre} todavía no está disponible para registro.'
        return info

    if fecha_referencia <= fecha_limite:
        info['disponible'] = True
        return info

    info['motivo'] = (
        f'El periodo {periodo_nombre} venció su ventana de registro y está '
        'pendiente de cierre automático.'
    )
    return info


def cerrar_mediciones_vencidas(fecha_referencia=None):
    """Servicio central del management command `cerrar_mediciones_vencidas`
    (Bloque 4). Por cada KPI autorizado, cierra EN ORDEN todos los periodos
    cuya ventana de 5 días ya venció sin medición manual, creando una
    Medicion con valor_resultado=0.00 y cierre_automatico=True.

    Idempotente: se apoya en `obtener_info_siguiente_periodo`, que siempre
    calcula el siguiente periodo a partir de la última Medicion real ya
    guardada — si un periodo ya fue cerrado (automática o manualmente), la
    siguiente llamada directamente evalúa el periodo posterior. Además
    verifica explícitamente que no exista ya una Medicion para ese
    (indicador, periodo) antes de crear, sin depender únicamente de que la
    constraint `unique_medicion_por_indicador_periodo` lo impida."""
    fecha_referencia = fecha_referencia or hoy()

    kpi_revisados = 0
    cierres_creados = 0
    kpi_bloqueados = 0
    errores = []
    detalle = []

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
                # de no saltar/adelantar periodos.
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
                    estado_cumplimiento = obtener_estado_para_medicion(
                        indicador=indicador,
                        meta=meta,
                        valor_resultado=Decimal('0.00'),
                    )

                    if estado_cumplimiento is None:
                        raise ValueError(
                            'No se encontró un estado de cumplimiento válido para clasificar el cierre automático.'
                        )

                    medicion = Medicion.objects.create(
                        indicador=indicador,
                        meta=meta,
                        estado_cumplimiento=estado_cumplimiento,
                        periodo=periodo,
                        registrado_por=None,
                        fecha_medicion=info['fecha_cierre'],
                        valor_resultado=Decimal('0.00'),
                        cierre_automatico=True,
                    )

                    generar_alerta_para_medicion(medicion)
                    resolver_alertas_periodo_vencido(medicion, usuario=None)
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
        'errores': errores,
        'detalle': detalle,
    }


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
            tipo_alerta='Periodo vencido sin medición',
            mensaje__icontains=periodo_nombre,
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

        mensaje = (
            f'El indicador "{indicador.nombre}" tiene vencido el periodo de {periodo_nombre} '
            f'(cierre {fecha_cierre.strftime("%d/%m/%Y")}) y no se registró ninguna medición.'
        )

        Alerta.objects.create(
            indicador=indicador,
            medicion=None,
            tipo_alerta='Periodo vencido sin medición',
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

