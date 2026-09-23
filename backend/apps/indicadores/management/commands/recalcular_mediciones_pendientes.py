from django.core.management.base import BaseCommand

from apps.indicadores.services import recalcular_mediciones_pendientes


class Command(BaseCommand):
    help = (
        'Recalcula únicamente las mediciones cuyo estado_cumplimiento actual '
        'es el fallback técnico "Pendiente de actualización", y solo cuando el '
        'KPI correspondiente ya tiene RangoKPI válidos para clasificarlas. No '
        'modifica valor_resultado ni ningún otro dato, y no toca mediciones que '
        'ya estén en Favorable/En riesgo/Incumplido. Debe ejecutarse después de '
        '"configurar_rangos_provisionales".'
    )

    def handle(self, *args, **kwargs):
        resultado = recalcular_mediciones_pendientes()

        for item in resultado['detalle']:
            self.stdout.write(self.style.SUCCESS(
                f"  + Medición {item['medicion_id']} ({item['indicador']}): "
                f"{item['porcentaje_cumplimiento']}% -> "
                f"{item['estado_anterior']} => {item['estado_nuevo']}"
            ))

        self.stdout.write(self.style.SUCCESS(
            f"\nMediciones revisadas: {resultado['revisadas']} | "
            f"Recalculadas: {resultado['recalculadas']}"
        ))
