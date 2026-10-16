from django.db import migrations


def sembrar_configuracion(apps, schema_editor):
    """Bloque 4: siembra la única fila de configuración (pk=1) con el
    valor que ya regía en código antes de esta corrección
    (VENTANA_REGISTRO_DIAS=5), para que el comportamiento de cierre
    automático/validación de periodos no cambie para nadie hasta que la
    administración edite el plazo explícitamente."""
    ConfiguracionMediciones = apps.get_model('indicadores', 'ConfiguracionMediciones')
    ConfiguracionMediciones.objects.get_or_create(pk=1, defaults={'dias_plazo_registro': 5})


def revertir_configuracion(apps, schema_editor):
    ConfiguracionMediciones = apps.get_model('indicadores', 'ConfiguracionMediciones')
    ConfiguracionMediciones.objects.filter(pk=1).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('indicadores', '0012_configuracionmediciones'),
    ]

    operations = [
        migrations.RunPython(sembrar_configuracion, revertir_configuracion),
    ]
