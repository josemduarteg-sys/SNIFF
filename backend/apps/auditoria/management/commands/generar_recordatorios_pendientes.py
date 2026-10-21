from django.core.management.base import BaseCommand

from apps.auditoria.services import generar_recordatorios_pendientes, registrar_ejecucion_tarea_automatica


class Command(BaseCommand):
    help = (
        'Genera notificaciones diarias para los Administradores de planificación '
        'con Planes estratégicos en Borrador o KPI pendientes de autorización.'
    )

    def handle(self, *args, **kwargs):
        resultado = generar_recordatorios_pendientes()

        for item in resultado['detalle']:
            if item['accion'] == 'creada':
                self.stdout.write(
                    self.style.WARNING(
                        f"  + Recordatorio creado para {item['usuario']}: {item['elemento']}"
                    )
                )
            else:
                self.stdout.write(
                    f"  · Ya existía recordatorio para {item['usuario']}: {item['elemento']}"
                )

        resumen = (
            f"Elementos revisados: {resultado['revisados']} | "
            f"Notificaciones creadas: {resultado['creadas']} | "
            f"Omitidas: {resultado['omitidas']}"
        )

        self.stdout.write(self.style.SUCCESS(resumen))

        # Etapa 4 (M7): registro de la ejecución en bitácora como "Sistema".
        registrar_ejecucion_tarea_automatica('Recordatorios de pendientes', resumen)
