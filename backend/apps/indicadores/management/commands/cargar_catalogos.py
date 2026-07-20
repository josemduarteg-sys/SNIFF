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
        roles = [
            {
                'nombre': 'Administrador',
                'descripcion': 'Gestiona usuarios, roles, permisos y configuración general del sistema.',
            },
            {
                'nombre': 'Supervisor',
                'descripcion': 'Define estrategias, objetivos, KPI, metas y revisa el cumplimiento de indicadores.',
            },
            {
                'nombre': 'Usuario operativo',
                'descripcion': 'Registra mediciones, carga archivos CSV y actualiza información autorizada.',
            },
            {
                'nombre': 'Usuario de consulta',
                'descripcion': 'Consulta dashboard, reportes, gráficas y alertas sin modificar información.',
            },
        ]

        for rol in roles:
            Rol.objects.get_or_create(
                nombre=rol['nombre'],
                defaults={
                    'descripcion': rol['descripcion'],
                    'estado': True,
                }
            )

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
                'nombre': 'Diaria',
                'descripcion': 'Actualización o medición realizada cada día.',
            },
            {
                'nombre': 'Semanal',
                'descripcion': 'Actualización o medición realizada cada semana.',
            },
            {
                'nombre': 'Mensual',
                'descripcion': 'Actualización o medición realizada cada mes.',
            },
            {
                'nombre': 'Trimestral',
                'descripcion': 'Actualización o medición realizada cada trimestre.',
            },
            {
                'nombre': 'Semestral',
                'descripcion': 'Actualización o medición realizada cada semestre.',
            },
            {
                'nombre': 'Anual',
                'descripcion': 'Actualización o medición realizada cada año.',
            },
        ]

        for frecuencia in frecuencias:
            Frecuencia.objects.get_or_create(
                nombre=frecuencia['nombre'],
                defaults={
                    'descripcion': frecuencia['descripcion'],
                    'estado': True,
                }
            )

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