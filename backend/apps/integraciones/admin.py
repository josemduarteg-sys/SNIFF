from django.contrib import admin

from .models import ArchivoImportado, ConexionDW, ConsultaDW


@admin.register(ArchivoImportado)
class ArchivoImportadoAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'nombre_archivo',
        'tipo_archivo',
        'fecha_importacion',
        'estado_importacion',
        'registros_procesados',
        'registros_con_error',
        'importado_por',
    )
    search_fields = ('nombre_archivo',)
    list_filter = ('estado_importacion', 'tipo_archivo')


@admin.register(ConexionDW)
class ConexionDWAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'nombre',
        'servidor',
        'base_datos',
        'esquema',
        'estado',
        'fecha_creacion',
    )
    search_fields = ('nombre', 'servidor', 'base_datos')
    list_filter = ('estado',)


@admin.register(ConsultaDW)
class ConsultaDWAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'nombre',
        'conexion_dw',
        'indicador',
        'frecuencia_ejecucion',
        'estado',
        'fecha_creacion',
    )
    search_fields = ('nombre', 'indicador__nombre')
    list_filter = ('estado', 'frecuencia_ejecucion')

