from django.db import migrations, models
import django.core.validators
import django.db.models.deletion


class Migration(migrations.Migration):
    """Bloque 3 del rediseño: IndicadorKPI pasa a depender de
    ObjetivoEspecifico (antes ObjetivoGeneral, ajuste de compatibilidad
    temporal del Bloque 1/2). Además:

    - se agrega `formula_medicion` (obligatorio);
    - se eliminan `tipo_calculo`, `fuente_dato`, `fecha_inicio`, `fecha_fin`
      del propio IndicadorKPI (los catálogos TipoCalculo/FuenteDato NO se
      eliminan, solo dejan de estar relacionados al KPI);
    - `valor_meta` pasa a ser obligatorio;
    - la unicidad (antes `objetivo` + `nombre`) pasa a ser
      `objetivo_especifico` + `nombre`.

    Escrita a mano (no generada con `makemigrations` en modo interactivo)
    porque el autodetector no reconoce esto como un rename — la FK cambia
    de modelo destino (ObjetivoGeneral -> ObjetivoEspecifico) — y porque en
    esta base de desarrollo la tabla `indicador_kpi` está vacía (0
    registros verificados antes de escribir esta migración), así que no
    hace falta un valor por defecto para las columnas nuevas no nulas.

    Orden importante: la constraint vieja se quita ANTES de eliminar el
    campo `objetivo` que referencia.
    """

    dependencies = [
        ('estrategia', '0003_plananual_objetivoespecifico_and_more'),
        ('indicadores', '0007_indicadorkpi_objetivo_general'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='indicadorkpi',
            name='unique_indicador_por_objetivo',
        ),
        migrations.RemoveField(
            model_name='indicadorkpi',
            name='objetivo',
        ),
        migrations.RemoveField(
            model_name='indicadorkpi',
            name='tipo_calculo',
        ),
        migrations.RemoveField(
            model_name='indicadorkpi',
            name='fuente_dato',
        ),
        migrations.RemoveField(
            model_name='indicadorkpi',
            name='fecha_inicio',
        ),
        migrations.RemoveField(
            model_name='indicadorkpi',
            name='fecha_fin',
        ),
        migrations.AddField(
            model_name='indicadorkpi',
            name='objetivo_especifico',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='indicadores',
                to='estrategia.objetivoespecifico',
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name='indicadorkpi',
            name='objetivo_especifico',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='indicadores',
                to='estrategia.objetivoespecifico',
            ),
        ),
        migrations.AddField(
            model_name='indicadorkpi',
            name='formula_medicion',
            field=models.TextField(
                default='',
                help_text=(
                    'Explicación funcional de cómo se obtiene el resultado del KPI '
                    '(no se interpreta ni se ejecuta). Ejemplo: "(Ventas actuales / '
                    'Meta de ventas) × 100".'
                ),
            ),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='indicadorkpi',
            name='valor_meta',
            field=models.DecimalField(
                decimal_places=4,
                max_digits=14,
                validators=[django.core.validators.MinValueValidator(0)],
                help_text='Meta del KPI para el año de su Plan anual.',
            ),
        ),
        migrations.AddConstraint(
            model_name='indicadorkpi',
            constraint=models.UniqueConstraint(
                fields=('objetivo_especifico', 'nombre'),
                name='unique_indicador_por_objetivo_especifico',
            ),
        ),
    ]
