"""Rangos fijos para los fixtures de pruebas (D3).

Muchas pruebas anteriores a D3 crean KPI (en % o en "unidades") y esperaban
recibir la plantilla provisional 70/85 al llamar crear_rangos_provisionales.
Desde D3 la plantilla es 60/75 y solo se aplica a KPI en %. Esas pruebas no
evalúan la plantilla sino la clasificación contra los rangos guardados, así
que sus fixtures configuran estos rangos explícitos, independientes de la
plantilla vigente."""

from decimal import Decimal

from .models import EstadoCumplimiento, RangoKPI

RANGOS_70_85 = (
    ('Incumplido', Decimal('0'), Decimal('70')),
    ('En riesgo', Decimal('70'), Decimal('85')),
    ('Favorable', Decimal('85'), None),
)


def configurar_rangos_70_85(indicador):
    for nombre, minimo, maximo in RANGOS_70_85:
        RangoKPI.objects.get_or_create(
            indicador=indicador,
            estado_cumplimiento=EstadoCumplimiento.objects.get(nombre=nombre),
            defaults={'valor_minimo': minimo, 'valor_maximo': maximo, 'estado': True},
        )
