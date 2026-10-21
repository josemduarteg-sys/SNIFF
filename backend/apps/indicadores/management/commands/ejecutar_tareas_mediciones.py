import logging
from contextlib import contextmanager

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.utils import timezone

from apps.auditoria.services import registrar_ejecucion_tarea_automatica
from apps.indicadores.services import cerrar_mediciones_vencidas, generar_alertas_periodos_vencidos

logger = logging.getLogger(__name__)

# Clave fija del advisory lock de PostgreSQL de este proceso (cualquier
# entero de 64 bits; solo tiene que ser único dentro de SNIFF).
CLAVE_BLOQUEO_TAREAS = 734_201_026


@contextmanager
def bloqueo_exclusivo():
    """Etapa 3 (auditoría C1): impide dos ejecuciones simultáneas (p. ej.
    la tarea programada y una ejecución manual). En PostgreSQL usa un
    advisory lock de sesión, que se libera solo si el proceso muere. En
    otros motores (SQLite de pruebas) no hay bloqueo entre procesos; la
    restricción única (indicador, periodo) sigue impidiendo duplicados."""
    if connection.vendor != 'postgresql':
        yield True
        return

    with connection.cursor() as cursor:
        cursor.execute('SELECT pg_try_advisory_lock(%s)', [CLAVE_BLOQUEO_TAREAS])
        obtenido = cursor.fetchone()[0]

    try:
        yield obtenido
    finally:
        if obtenido:
            with connection.cursor() as cursor:
                cursor.execute('SELECT pg_advisory_unlock(%s)', [CLAVE_BLOQUEO_TAREAS])


class Command(BaseCommand):
    help = (
        'Tarea diaria de mediciones (Etapa 3, C1): ejecuta en orden '
        'cerrar_mediciones_vencidas y generar_alertas_periodos_vencidos, con '
        'bloqueo contra ejecuciones simultáneas. Con --simular calcula todo '
        'y revierte la transacción. Termina con código distinto de 0 si hubo '
        'errores, para que el programador de tareas lo registre como fallo. '
        'Ver backend/docs/TAREAS_PROGRAMADAS.md.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--simular',
            action='store_true',
            help='Calcula cierres y alertas sin guardar nada (la transacción se revierte).',
        )

    def handle(self, *args, **options):
        simular = options['simular']
        inicio = timezone.localtime()
        modo = 'SIMULACIÓN' if simular else 'EJECUCIÓN'

        self.stdout.write(f'[{inicio:%Y-%m-%d %H:%M:%S}] {modo} de tareas de mediciones')

        with bloqueo_exclusivo() as obtenido:
            if not obtenido:
                mensaje = 'Otra ejecución de las tareas de mediciones sigue en curso; no se hizo nada.'
                logger.warning(mensaje)
                raise CommandError(mensaje)

            if simular:
                with transaction.atomic():
                    cierres, alertas = self._ejecutar()
                    transaction.set_rollback(True)
            else:
                cierres, alertas = self._ejecutar()

        resumen = self._informar(cierres, alertas, simular)

        # Etapa 4 (M7): solo las ejecuciones reales quedan en bitácora, como
        # evento del "Sistema". Si este registro falla, el comando termina
        # con error y deja constancia de que lo anterior ya quedó guardado.
        if not simular:
            registrar_ejecucion_tarea_automatica(
                'Tareas diarias de mediciones', resumen, con_errores=bool(cierres['errores']),
            )

        if cierres['errores']:
            raise CommandError(
                f"El cierre automático terminó con {len(cierres['errores'])} error(es); "
                'revisá el detalle de arriba.'
            )

    def _ejecutar(self):
        # El cierre va primero: resuelve las alertas de periodos que acaba
        # de cubrir, y las alertas se calculan sobre el estado ya cerrado.
        cierres = cerrar_mediciones_vencidas()
        alertas = generar_alertas_periodos_vencidos()
        return cierres, alertas

    def _informar(self, cierres, alertas, simular):
        for item in cierres['detalle']:
            self.stdout.write(
                f"  + Cierre automático: KPI {item['indicador_id']} \"{item['indicador']}\" "
                f"- periodo {item['periodo']}"
            )

        for item in cierres['errores']:
            self.stdout.write(self.style.ERROR(
                f"  ! Error en KPI {item['indicador_id']} \"{item['indicador']}\" "
                f"(periodo {item['periodo']}): {item['error']}"
            ))
            logger.error('Cierre automático con error: %s', item)

        for item in alertas['detalle']:
            if item['accion'] == 'creada':
                self.stdout.write(
                    f"  + Alerta de periodo vencido: KPI {item['indicador_id']} - {item['periodo']}"
                )

        resumen = (
            f"KPI revisados: {cierres['kpi_revisados']} | "
            f"Cierres automáticos: {cierres['cierres_creados']} | "
            f"KPI omitidos por jerarquía Cerrada: {cierres['kpi_bloqueados']} | "
            f"KPI en espera por ampliación pendiente: {cierres.get('kpi_en_espera', 0)} | "
            f"Solicitudes de ampliación vencidas: {cierres.get('solicitudes_vencidas', 0)} | "
            f"Solicitudes de ampliación sin efecto: {cierres.get('solicitudes_sin_efecto', 0)} | "
            f"Errores de cierre: {len(cierres['errores'])} | "
            f"Alertas creadas: {alertas['creadas']} | "
            f"Alertas ya existentes: {alertas['omitidas']}"
        )

        texto = f'SIMULACIÓN (no se guardó ningún cambio): {resumen}' if simular else resumen

        logger.info(texto)
        self.stdout.write(self.style.SUCCESS(texto))

        return resumen
