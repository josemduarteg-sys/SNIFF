from datetime import date
from decimal import Decimal

from django.utils import timezone

from .models import Alerta, EstadoCumplimiento, IndicadorKPI, Medicion, RangoKPI


def calcular_porcentaje_cumplimiento(valor_resultado, valor_meta):
    if valor_meta is None or valor_meta == 0:
        return Decimal('0')

    return (Decimal(valor_resultado) / Decimal(valor_meta)) * Decimal('100')


def obtener_estado_por_cumplimiento(indicador, porcentaje_cumplimiento):
    rango = RangoKPI.objects.select_related(
        'estado_cumplimiento'
    ).filter(
        indicador=indicador,
        estado=True,
        valor_minimo__lte=porcentaje_cumplimiento,
        valor_maximo__gte=porcentaje_cumplimiento,
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

    estado = obtener_estado_por_cumplimiento(
        indicador=indicador,
        porcentaje_cumplimiento=porcentaje,
    )

    return estado


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


def obtener_intervalo_meses(indicador):
    frecuencia = (indicador.frecuencia.nombre or '').lower()

    if 'bimestral' in frecuencia or 'bimensual' in frecuencia:
        return 2

    if 'trimestral' in frecuencia:
        return 3

    if 'semestral' in frecuencia:
        return 6

    if 'anual' in frecuencia:
        return 12

    return 1


def sumar_meses(fecha, meses):
    mes = fecha.month - 1 + meses
    anio = fecha.year + mes // 12
    mes = mes % 12 + 1

    return date(anio, mes, 1)


def formatear_periodo(fecha):
    meses = {
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

    return f"{meses.get(fecha.month, fecha.month)} {fecha.year}"


def obtener_siguiente_periodo_esperado(indicador, excluir_medicion_id=None):
    intervalo = obtener_intervalo_meses(indicador)

    primer_periodo = date(
        indicador.fecha_inicio.year,
        indicador.fecha_inicio.month,
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


def generar_alertas_periodos_vencidos(fecha_referencia=None):
    fecha_referencia = fecha_referencia or date.today()

    total_kpi_revisados = 0
    total_alertas_creadas = 0
    total_omitidas = 0
    detalle = []

    indicadores = IndicadorKPI.objects.filter(estado='autorizado').select_related('frecuencia')

    for indicador in indicadores:
        total_kpi_revisados += 1

        if not indicador.fecha_inicio:
            continue

        periodo_esperado = obtener_siguiente_periodo_esperado(indicador)

        if not periodo_esperado:
            continue

        if indicador.fecha_fin:
            fecha_fin_kpi = date(
                indicador.fecha_fin.year,
                indicador.fecha_fin.month,
                1,
            )

            if periodo_esperado > fecha_fin_kpi:
                continue

        intervalo = obtener_intervalo_meses(indicador)
        fecha_cierre = calcular_fecha_cierre_periodo(periodo_esperado, intervalo)

        if fecha_cierre >= fecha_referencia:
            continue

        periodo_nombre = formatear_periodo(periodo_esperado)

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

