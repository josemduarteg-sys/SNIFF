"""D2: copia las REFERENCIAS de Medicion.evidencia (campo heredado, un
archivo por medición) a EvidenciaMedicion.

- No copia, mueve, renombra ni borra ningún archivo: cada fila nueva apunta
  a la misma ruta que ya tenía la medición.
- Idempotente: si la medición ya tiene una evidencia con esa misma ruta, no
  la duplica.
- Usuario y fecha: los de la medición (quién la registró y cuándo).
- Reversible: deshacerla borra solo las filas que apuntan a la ruta heredada
  de su medición. Borrar una fila no borra el archivo, que además sigue
  referenciado por Medicion.evidencia."""

import mimetypes
import os

from django.db import migrations


def migrar_evidencias(apps, schema_editor):
    Medicion = apps.get_model('indicadores', 'Medicion')
    EvidenciaMedicion = apps.get_model('indicadores', 'EvidenciaMedicion')

    for medicion in Medicion.objects.exclude(evidencia='').exclude(evidencia__isnull=True).order_by('id'):
        ruta = medicion.evidencia.name

        if EvidenciaMedicion.objects.filter(medicion=medicion, archivo=ruta).exists():
            continue

        try:
            tamano = medicion.evidencia.storage.size(ruta)
        except (OSError, NotImplementedError):
            tamano = 0

        EvidenciaMedicion.objects.create(
            medicion=medicion,
            archivo=ruta,
            nombre_original=os.path.basename(ruta)[:255],
            tamano=tamano,
            tipo_contenido=mimetypes.guess_type(ruta)[0] or '',
            subido_por_id=medicion.registrado_por_id,
            fecha_subida=medicion.fecha_registro,
        )


def revertir(apps, schema_editor):
    Medicion = apps.get_model('indicadores', 'Medicion')
    EvidenciaMedicion = apps.get_model('indicadores', 'EvidenciaMedicion')

    for medicion in Medicion.objects.exclude(evidencia='').exclude(evidencia__isnull=True):
        # queryset.delete() no llama a EvidenciaMedicion.delete() del modelo
        # ni borra archivos: solo quita las filas creadas por esta migración.
        EvidenciaMedicion.objects.filter(medicion=medicion, archivo=medicion.evidencia.name).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('indicadores', '0017_evidencia_medicion'),
    ]

    operations = [
        migrations.RunPython(migrar_evidencias, revertir),
    ]
