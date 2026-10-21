"""Etapa 3 (auditoría C3): agrega al catálogo EstadoCumplimiento el estado
"Sin registro", que se asigna únicamente a los cierres automáticos por
falta de registro.

No es un rango de clasificación: ningún RangoKPI lo usa, así que nunca se
asigna a un resultado real. Solo inserta una fila si no existe; no modifica
ni borra ningún estado existente."""

from django.db import migrations

NOMBRE = 'Sin registro'


def agregar_estado(apps, schema_editor):
    EstadoCumplimiento = apps.get_model('indicadores', 'EstadoCumplimiento')

    if EstadoCumplimiento.objects.filter(nombre__iexact=NOMBRE).exists():
        return

    EstadoCumplimiento.objects.create(
        nombre=NOMBRE,
        descripcion=(
            'El periodo venció sin que se registrara un resultado; el sistema lo '
            'cerró automáticamente. No es un resultado de desempeño del KPI.'
        ),
        color='gris',
        estado=True,
    )


def quitar_estado(apps, schema_editor):
    # Solo se revierte si nadie lo usa todavía (las FK son PROTECT).
    EstadoCumplimiento = apps.get_model('indicadores', 'EstadoCumplimiento')
    Medicion = apps.get_model('indicadores', 'Medicion')
    RangoKPI = apps.get_model('indicadores', 'RangoKPI')

    estado = EstadoCumplimiento.objects.filter(nombre=NOMBRE).first()

    if estado and not Medicion.objects.filter(estado_cumplimiento=estado).exists() \
            and not RangoKPI.objects.filter(estado_cumplimiento=estado).exists():
        estado.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('indicadores', '0014_medicion_valor_resultado_sin_registro'),
    ]

    operations = [
        migrations.RunPython(agregar_estado, quitar_estado),
    ]
