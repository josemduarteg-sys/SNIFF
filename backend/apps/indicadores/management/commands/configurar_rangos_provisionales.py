from django.core.management.base import BaseCommand

from apps.indicadores.services import configurar_rangos_provisionales_para_todos


class Command(BaseCommand):
    help = (
        'Completa los RangoKPI (Incumplido/En riesgo/Favorable, plantilla 60/75) '
        'SOLO en los KPI en porcentaje que no tienen ningún rango. Nunca modifica '
        'rangos existentes (personalizados, invertidos o de la plantilla anterior) '
        'ni asigna rangos porcentuales a KPI en otra unidad: esos casos se informan '
        'como omitidos. Puede ejecutarse nuevamente sin efectos adicionales.'
    )

    def handle(self, *args, **kwargs):
        resultado = configurar_rangos_provisionales_para_todos()

        for item in resultado['detalle']:
            if item['accion'] == 'creado':
                self.stdout.write(self.style.SUCCESS(
                    f"  + KPI {item['indicador_id']} \"{item['indicador']}\": "
                    f"{item['rangos_creados']} rango(s) creado(s)."
                ))
            else:
                self.stdout.write(
                    f"  · KPI {item['indicador_id']} \"{item['indicador']}\" omitido: {item['motivo']}"
                )

        self.stdout.write(self.style.SUCCESS(
            f"\nKPI procesados: {resultado['kpi_procesados']} | "
            f"Rangos creados: {resultado['rangos_creados']} | "
            'Rangos existentes modificados: 0'
        ))
