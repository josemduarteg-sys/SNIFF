from django.core.management.base import BaseCommand

from apps.indicadores.services import cerrar_mediciones_vencidas


class Command(BaseCommand):
    help = (
        'Cierra automáticamente en 0.00 los periodos de medición de KPI autorizados '
        'cuya ventana de registro (cierre del periodo + 5 días) ya venció sin que '
        'exista una medición manual. Procesa en orden todos los periodos atrasados de '
        'cada KPI (no solo el más reciente). Idempotente: puede ejecutarse varias '
        'veces sin duplicar cierres. Pensado para programarse una vez al día '
        '(Windows Task Scheduler o cron, ver documentación del proyecto).'
    )

    def handle(self, *args, **kwargs):
        resultado = cerrar_mediciones_vencidas()

        for item in resultado['detalle']:
            self.stdout.write(self.style.WARNING(
                f"  + Cierre automático: KPI {item['indicador_id']} \"{item['indicador']}\" "
                f"— periodo {item['periodo']} (medición #{item['medicion_id']})"
            ))

        for item in resultado['errores']:
            self.stdout.write(self.style.ERROR(
                f"  ! Error en KPI {item['indicador_id']} \"{item['indicador']}\" "
                f"(periodo {item['periodo']}): {item['error']}"
            ))

        self.stdout.write(self.style.SUCCESS(
            f"\nKPI revisados: {resultado['kpi_revisados']} | "
            f"Cierres automáticos creados: {resultado['cierres_creados']} | "
            f"KPI omitidos por jerarquía Cerrada: {resultado['kpi_bloqueados']} | "
            f"Errores: {len(resultado['errores'])}"
        ))
