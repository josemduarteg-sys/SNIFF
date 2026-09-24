from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    """Bloque 1 del rediseño: Estrategia -> PlanEstrategico, Objetivo -> ObjetivoGeneral.

    Escrita a mano en vez de con `makemigrations` porque el autodetector de
    Django no reconoció el rename automáticamente (el conjunto de campos
    cambia demasiado entre el modelo viejo y el nuevo como para que la
    heurística de similitud lo sugiera solo) y hubiera generado un
    Delete+Create en vez de un Rename real. Se usa `RenameModel`/
    `RenameField` explícitamente para preservar identidad de tabla/columna
    en el historial de migraciones (aunque en la práctica esta migración no
    se aplica sobre la base de datos actual: la base final será nueva).

    Orden importante: las constraints que referencian los campos viejos se
    quitan ANTES de renombrar/eliminar esos campos.

    Dependencia adicional hacia indicadores/0006 (validación post-bloque 1):
    `IndicadorKPI.objetivo` fue creado en indicadores/0001_initial.py como FK
    a `estrategia.Objetivo`, y las migraciones indicadores/0002 a 0006 nunca
    tocan ese campo pero sí dependen, a través del historial encadenado, de
    que el modelo siga llamándose `Objetivo` en el estado de migraciones que
    Django reconstruye. Sin esta dependencia, `estrategia/0002` y la cadena
    `indicadores/0001-0006` son dos ramas independientes que solo cuelgan de
    `estrategia/0001`, y Django podría aplicar este RenameModel antes de que
    esa cadena termine, dejando `indicadores/0001` sin poder resolver
    `to='estrategia.objetivo'`. Se fuerza aquí que TODA la cadena vieja de
    indicadores se aplique primero.
    """

    dependencies = [
        ('estrategia', '0001_initial'),
        ('indicadores', '0006_rango_kpi_valor_maximo_nullable'),
    ]

    operations = [
        # ---------- Estrategia -> PlanEstrategico ----------
        migrations.RenameModel(
            old_name='Estrategia',
            new_name='PlanEstrategico',
        ),
        migrations.RemoveConstraint(
            model_name='planestrategico',
            name='unique_estrategia_por_area',
        ),
        migrations.RemoveField(
            model_name='planestrategico',
            name='area',
        ),
        migrations.RenameField(
            model_name='planestrategico',
            old_name='nombre',
            new_name='titulo',
        ),
        migrations.AlterField(
            model_name='planestrategico',
            name='estado',
            field=models.CharField(
                choices=[
                    ('borrador', 'Borrador'),
                    ('en_uso', 'En uso'),
                    ('cerrado', 'Cerrado'),
                ],
                default='borrador',
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name='planestrategico',
            name='creado_por',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='planes_estrategicos_creados',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterModelOptions(
            name='planestrategico',
            options={
                'ordering': ['-fecha_creacion'],
                'verbose_name': 'Plan estratégico',
                'verbose_name_plural': 'Planes estratégicos',
            },
        ),
        migrations.AlterModelTable(
            name='planestrategico',
            table='plan_estrategico',
        ),

        # ---------- Objetivo -> ObjetivoGeneral ----------
        migrations.RenameModel(
            old_name='Objetivo',
            new_name='ObjetivoGeneral',
        ),
        migrations.RemoveConstraint(
            model_name='objetivogeneral',
            name='unique_objetivo_por_estrategia',
        ),
        migrations.RenameField(
            model_name='objetivogeneral',
            old_name='estrategia',
            new_name='plan_estrategico',
        ),
        migrations.AlterField(
            model_name='objetivogeneral',
            name='plan_estrategico',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='objetivos_generales',
                to='estrategia.planestrategico',
            ),
        ),
        migrations.RemoveField(
            model_name='objetivogeneral',
            name='nombre',
        ),
        migrations.RemoveField(
            model_name='objetivogeneral',
            name='descripcion',
        ),
        migrations.RemoveField(
            model_name='objetivogeneral',
            name='fecha_inicio',
        ),
        migrations.RemoveField(
            model_name='objetivogeneral',
            name='fecha_fin',
        ),
        migrations.RemoveField(
            model_name='objetivogeneral',
            name='estado',
        ),
        migrations.AddField(
            model_name='objetivogeneral',
            name='texto_objetivo',
            field=models.TextField(default=''),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='objetivogeneral',
            name='creado_por',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='objetivos_generales_creados',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterModelOptions(
            name='objetivogeneral',
            options={
                'ordering': ['-fecha_creacion'],
                'verbose_name': 'Objetivo general',
                'verbose_name_plural': 'Objetivos generales',
            },
        ),
        migrations.AlterModelTable(
            name='objetivogeneral',
            table='objetivo_general',
        ),
    ]
