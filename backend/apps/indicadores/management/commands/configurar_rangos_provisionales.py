from django.core.management.base import BaseCommand

from apps.indicadores.services import configurar_rangos_provisionales_para_todos


class Command(BaseCommand):
    help = (
        'Configura los RangoKPI provisionales (Incumplido/En riesgo/Favorable) '
        'para todos los KPI existentes: crea los que falten y actualiza los que '
        'coincidan exactamente con la configuración anterior conocida. No '
        'duplica rangos y puede ejecutarse nuevamente sin efectos adicionales. '
        'KPI con una configuración de rangos distinta a la esperada se omiten '
        'y se reportan para revisión manual.'
    )

    def handle(self, *args, **kwargs):
        resultado = configurar_rangos_provisionales_para_todos()

        for item in resultado['detalle']:
            if item['accion'] == 'creado':
                self.stdout.write(self.style.SUCCESS(
                    f"  + KPI {item['indicador_id']} \"{item['indicador']}\": "
                    f"{item['rangos_creados']} rango(s) creado(s)."
                ))
            elif item['accion'] == 'actualizado':
                self.stdout.write(self.style.WARNING(
                    f"  ~ KPI {item['indicador_id']} \"{item['indicador']}\": "
                    f"{item['rangos_actualizados']} rango(s) actualizado(s)."
                ))
            elif item['accion'] == 'sin cambios':
                self.stdout.write(
                    f"  · KPI {item['indicador_id']} \"{item['indicador']}\": "
                    "ya estaba con el criterio provisional, sin cambios."
                )
            else:
                self.stdout.write(self.style.ERROR(
                    f"  ! KPI {item['indicador_id']} \"{item['indicador']}\" OMITIDO: "
                    f"{item['motivo']}"
                ))

        self.stdout.write(self.style.SUCCESS(
            f"\nKPI procesados: {resultado['kpi_procesados']} | "
            f"Rangos creados: {resultado['rangos_creados']} | "
            f"Rangos actualizados: {resultado['rangos_actualizados']}"
        ))
