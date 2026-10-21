from django.core.management.base import BaseCommand
from django.db import transaction

from apps.auditoria.services import registrar_ejecucion_tarea_automatica

from apps.indicadores.services import cerrar_mediciones_vencidas


class Command(BaseCommand):
    help = (
        'Cierra automáticamente en 0.00 los periodos de medición de KPI autorizados '
        'cuya ventana de registro (cierre del periodo + el plazo configurado en '
        'ConfiguracionMediciones) ya venció sin que exista una medición manual. '
        'Procesa en orden todos los periodos atrasados de cada KPI (no solo el más '
        'reciente). Idempotente: puede ejecutarse varias veces sin duplicar cierres. '
        'Pensado para programarse una vez al día '
        '(Windows Task Scheduler o cron, ver documentación del proyecto).'
    )

    def add_arguments(self, parser):
        # Etapa 3 (auditoría C1): permite revisar qué cerraría el proceso
        # antes de programarlo, sin guardar nada.
        parser.add_argument(
            '--simular',
            action='store_true',
            help=(
                'Calcula los cierres que se harían hoy dentro de una transacción '
                'que siempre se revierte: no guarda mediciones, periodos ni alertas.'
            ),
        )

    def handle(self, *args, **kwargs):
        simular = kwargs.get('simular', False)

        if simular:
            # Los cierres por periodo usan sus propios atomic() (savepoints)
            # dentro de esta transacción externa, que se marca para
            # revertirse siempre: nada llega a la base de datos.
            with transaction.atomic():
                resultado = cerrar_mediciones_vencidas()
                transaction.set_rollback(True)

            self.stdout.write(self.style.NOTICE(
                'SIMULACIÓN: no se guardó ningún cambio. Resultado de lo que se habría cerrado:'
            ))
        else:
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

        resumen = (
            f"KPI revisados: {resultado['kpi_revisados']} | "
            f"Cierres automáticos creados: {resultado['cierres_creados']} | "
            f"KPI omitidos por jerarquía Cerrada: {resultado['kpi_bloqueados']} | "
            f"KPI en espera por ampliación pendiente: {resultado.get('kpi_en_espera', 0)} | "
            f"Solicitudes de ampliación vencidas: {resultado.get('solicitudes_vencidas', 0)} | "
            f"Solicitudes de ampliación sin efecto: {resultado.get('solicitudes_sin_efecto', 0)} | "
            f"Errores: {len(resultado['errores'])}"
        )

        self.stdout.write(self.style.SUCCESS(f'\n{resumen}'))

        # Etapa 4 (M7): solo las ejecuciones reales quedan en bitácora.
        if not simular:
            registrar_ejecucion_tarea_automatica(
                'Cierre de mediciones vencidas', resumen, con_errores=bool(resultado['errores']),
            )
