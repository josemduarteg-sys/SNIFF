"""Etapa 4 (auditoría M7): la bitácora distingue las acciones de usuarios de
los eventos que ejecuta automáticamente el sistema (tareas programadas).
Un registro del sistema queda con usuario NULL y se muestra como "Sistema";
no se crea ninguna cuenta ficticia.

Solo cambia el esquema (DROP NOT NULL): ninguna fila existente se modifica,
y todas conservan su usuario (verificado antes de aplicarla)."""

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('auditoria', '0002_notificacion'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name='bitacora',
            name='usuario',
            field=models.ForeignKey(
                blank=True,
                help_text='Vacío únicamente en eventos ejecutados automáticamente por el sistema.',
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='registros_bitacora',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
