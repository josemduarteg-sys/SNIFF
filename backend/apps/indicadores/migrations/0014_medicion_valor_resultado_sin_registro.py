"""Etapa 3 (auditoría C3): una medición cerrada automáticamente por falta de
registro ya no guarda un 0.00 inventado, sino valor_resultado NULL ("Sin
registro").

Solo cambia el esquema:
- valor_resultado pasa a admitir NULL.
- Restricción: NULL únicamente si cierre_automatico = True (una medición
  manual siempre tiene resultado). PostgreSQL la valida contra las filas
  existentes al crearla; todas tienen resultado (verificado antes de
  aplicarla), así que ninguna fila se modifica.

No reinterpreta mediciones existentes: un cierre automático anterior en
0.00 (si existiera en alguna base) se conserva tal cual."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('indicadores', '0013_seed_configuracion_mediciones'),
    ]

    operations = [
        migrations.AlterField(
            model_name='medicion',
            name='valor_resultado',
            field=models.DecimalField(
                blank=True,
                decimal_places=4,
                help_text='Resultado real del periodo. Vacío solo en cierres automáticos por falta de registro.',
                max_digits=14,
                null=True,
            ),
        ),
        migrations.AddConstraint(
            model_name='medicion',
            constraint=models.CheckConstraint(
                condition=models.Q(('valor_resultado__isnull', False), ('cierre_automatico', True), _connector='OR'),
                name='medicion_sin_resultado_solo_en_cierre_automatico',
            ),
        ),
    ]
