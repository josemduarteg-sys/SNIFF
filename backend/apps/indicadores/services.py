from decimal import Decimal

from .models import EstadoCumplimiento, RangoKPI


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

