from django.core.management.base import BaseCommand

from apps.indicadores.services import generar_alertas_periodos_vencidos


class Command(BaseCommand):
    help = (
        'Genera alertas para KPI autorizados cuyo siguiente periodo esperado '
        'de medición ya venció sin que exista una medición registrada.'
    )

    def handle(self, *args, **kwargs):
        resultado = generar_alertas_periodos_vencidos()

        for item in resultado['detalle']:
            if item['accion'] == 'creada':
                self.stdout.write(
                    self.style.WARNING(
                        f"  + Alerta creada: {item['indicador']} — periodo {item['periodo']}"
                    )
                )
            else:
                self.stdout.write(
                    f"  · Ya existía alerta: {item['indicador']} — periodo {item['periodo']}"
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"KPI revisados: {resultado['revisados']} | "
                f"Alertas creadas: {resultado['creadas']} | "
                f"Omitidas: {resultado['omitidas']}"
            )
        )
