from django.core.management.base import BaseCommand

from apps.usuarios.models import Rol
from apps.estrategia.models import Area
from apps.indicadores.models import (
    Frecuencia,
    TipoCalculo,
    FuenteDato,
    EstadoCumplimiento,
)


class Command(BaseCommand):
    help = 'Carga catálogos iniciales del sistema.'

    def handle(self, *args, **kwargs):
        self.cargar_roles()
        self.cargar_area()
        self.cargar_frecuencias()
        self.cargar_tipos_calculo()
        self.cargar_fuentes_dato()
        self.cargar_estados_cumplimiento()

        self.stdout.write(
            self.style.SUCCESS('Catálogos iniciales cargados correctamente.')
        )

    def cargar_roles(self):
        # Nombres de aplicación, no nombres heredados. Las migraciones deben
        # ejecutarse primero. Nunca reasignar cuentas ni reactivar roles aquí.
        roles = [
            ('Administrador del sistema', 'Gestiona cuentas, roles y auditoría.'),
            ('Administrador de planificación', 'Gestiona planificación, KPI y autorizaciones.'),
            ('Ejecutor operativo', 'Registra mediciones y adjunta evidencias.'),
            ('Usuario de consulta', 'Consulta la información sin modificarla.'),
        ]
        for nombre, descripcion in roles:
            rol, _ = Rol.objects.get_or_create(
                nombre__iexact=nombre,
                defaults={'nombre': nombre, 'descripcion': descripcion, 'estado': True},
            )
            if not rol.estado:
                self.stdout.write(self.style.WARNING(
                    f'El rol "{rol.nombre}" ya existe inactivo; se conserva sin cambios.'
                ))
        # Supervisor solo se conserva si existe. No crear un perfil obsoleto
        # ni modificar su estado/asignaciones fuera de una decisión explícita.
        if Rol.objects.filter(nombre__iexact='Supervisor', estado=True).exists():
            self.stdout.write(self.style.WARNING(
                'Supervisor sigue activo: revisar su uso; no se modificó.'
            ))

    def cargar_area(self):
        Area.objects.get_or_create(
            nombre='Créditos y Cobros - Oficinas Centrales',
            defaults={
                'descripcion': 'Área inicial definida para el seguimiento de estrategias empresariales e indicadores KPI.',
                'estado': True,
            }
        )

    def cargar_frecuencias(self):
        frecuencias = [
            {
                'nombre': 'Mensual',
                'descripcion': 'Seguimiento mensual del KPI.',
                'estado': True,
            },
            {
                'nombre': 'Bimestral',
                'descripcion': 'KPI con vigencia o evaluación bimestral.',
                'estado': True,
            },
            {
                'nombre': 'Trimestral',
                'descripcion': 'KPI con vigencia o evaluación trimestral.',
                'estado': True,
            },
            {
                'nombre': 'Semestral',
                'descripcion': 'KPI con vigencia o evaluación semestral.',
                'estado': True,
            },
            {
                'nombre': 'Anual',
                'descripcion': 'KPI con vigencia o evaluación anual.',
                'estado': True,
            },
        ]

        for frecuencia_data in frecuencias:
            frecuencia, created = Frecuencia.objects.get_or_create(
                nombre=frecuencia_data['nombre'],
                defaults={
                    'descripcion': frecuencia_data['descripcion'],
                    'estado': frecuencia_data['estado'],
                },
            )

            if not created:
                frecuencia.descripcion = frecuencia_data['descripcion']
                frecuencia.estado = frecuencia_data['estado']
                frecuencia.save()

        frecuencias_inactivas = ['Diaria', 'Semanal']

        Frecuencia.objects.filter(nombre__in=frecuencias_inactivas).update(estado=False)

    def cargar_tipos_calculo(self):
        tipos_calculo = [
            {
                'nombre': 'Porcentaje',
                'descripcion': 'Calcula el cumplimiento como proporción porcentual entre resultado y meta.',
            },
            {
                'nombre': 'Promedio',
                'descripcion': 'Calcula el resultado a partir del promedio de varios valores.',
            },
            {
                'nombre': 'Acumulado',
                'descripcion': 'Calcula el resultado mediante la suma acumulada de valores durante un periodo.',
            },
            {
                'nombre': 'Relación',
                'descripcion': 'Calcula el indicador mediante la relación entre dos valores.',
            },
            {
                'nombre': 'Conteo',
                'descripcion': 'Calcula el indicador a partir del número de registros o eventos.',
            },
            {
                'nombre': 'Reducción',
                'descripcion': 'Evalúa indicadores donde un valor menor representa mejor desempeño.',
            },
        ]

        for tipo in tipos_calculo:
            TipoCalculo.objects.get_or_create(
                nombre=tipo['nombre'],
                defaults={
                    'descripcion': tipo['descripcion'],
                    'estado': True,
                }
            )

    def cargar_fuentes_dato(self):
        fuentes = [
            {
                'nombre': 'Manual',
                'descripcion': 'Datos ingresados manualmente por usuarios autorizados.',
            },
            {
                'nombre': 'CSV',
                'descripcion': 'Datos cargados desde reportes CSV proporcionados por la cooperativa.',
            },
            {
                'nombre': 'Data Warehouse',
                'descripcion': 'Datos obtenidos desde el Data Warehouse institucional.',
            },
        ]

        for fuente in fuentes:
            FuenteDato.objects.get_or_create(
                nombre=fuente['nombre'],
                defaults={
                    'descripcion': fuente['descripcion'],
                    'estado': True,
                }
            )

    def cargar_estados_cumplimiento(self):
        estados = [
            {
                'nombre': 'Favorable',
                'descripcion': 'El indicador cumple o supera el rango esperado.',
                'color': 'verde',
            },
            {
                'nombre': 'En riesgo',
                'descripcion': 'El indicador presenta avance parcial o requiere seguimiento.',
                'color': 'amarillo',
            },
            {
                'nombre': 'Incumplido',
                'descripcion': 'El indicador no alcanza el rango mínimo esperado.',
                'color': 'rojo',
            },
            {
                'nombre': 'Pendiente de actualización',
                'descripcion': 'El indicador no cuenta con medición registrada para el periodo correspondiente.',
                'color': 'gris',
            },
        ]

        for estado in estados:
            EstadoCumplimiento.objects.get_or_create(
                nombre=estado['nombre'],
                defaults={
                    'descripcion': estado['descripcion'],
                    'color': estado['color'],
                    'estado': True,
                }
            )