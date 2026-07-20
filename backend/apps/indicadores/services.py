from decimal import Decimal

from django.utils import timezone

from .models import Alerta, EstadoCumplimiento, RangoKPI


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

