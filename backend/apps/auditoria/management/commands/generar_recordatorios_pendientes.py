from django.core.management.base import BaseCommand

from apps.auditoria.services import generar_recordatorios_pendientes


class Command(BaseCommand):
    help = (
        'Genera notificaciones diarias para administradores, supervisores y usuarios '
        'operativos con estrategias, objetivos o KPI pendientes de revisión o autorización.'
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

        self.stdout.write(
            self.style.SUCCESS(
                f"Elementos revisados: {resultado['revisados']} | "
                f"Notificaciones creadas: {resultado['creadas']} | "
                f"Omitidas: {resultado['omitidas']}"
            )
        )
