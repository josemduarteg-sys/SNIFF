from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    """Bloque 1 del rediseño: ajuste de compatibilidad únicamente.

    IndicadorKPI.objetivo seguía apuntando a apps.estrategia.Objetivo, que
    esta misma tarea renombra a ObjetivoGeneral. Se retarget la FK para que
    el proyecto siga compilando; no es un cambio funcional de KPI (eso es
    Bloque 3, que además reapuntará esta FK a ObjetivoEspecifico).
    """

    dependencies = [
        ('estrategia', '0002_plan_estrategico_objetivo_general'),
        ('indicadores', '0006_rango_kpi_valor_maximo_nullable'),
    ]

    operations = [
        migrations.AlterField(
            model_name='indicadorkpi',
            name='objetivo',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='indicadores',
                to='estrategia.objetivogeneral',
            ),
        ),
    ]
