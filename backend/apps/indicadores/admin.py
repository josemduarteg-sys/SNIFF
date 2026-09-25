from django.contrib import admin

from .models import (
    Frecuencia,
    TipoCalculo,
    FuenteDato,
    IndicadorKPI,
    MetaKPI,
    ResponsableKPI,
    EstadoCumplimiento,
    RangoKPI,
    PeriodoMedicion,
    Medicion,
    Alerta,
)


@admin.register(Frecuencia)
class FrecuenciaAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'estado')
    search_fields = ('nombre',)
    list_filter = ('estado',)


@admin.register(TipoCalculo)
class TipoCalculoAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'estado')
    search_fields = ('nombre',)
    list_filter = ('estado',)


@admin.register(FuenteDato)
class FuenteDatoAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'estado')
    search_fields = ('nombre',)
    list_filter = ('estado',)


@admin.register(IndicadorKPI)
class IndicadorKPIAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'nombre',
        'objetivo_especifico',
        'frecuencia',
        'unidad_medida',
        'valor_meta',
        'estado',
        'fecha_creacion',
    )
    search_fields = ('nombre', 'descripcion', 'objetivo_especifico__texto_objetivo')
    list_filter = ('estado', 'frecuencia')


@admin.register(MetaKPI)
class MetaKPIAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'indicador',
        'valor_meta',
        'fecha_inicio',
        'fecha_fin',
        'estado',
    )
    search_fields = ('indicador__nombre',)
    list_filter = ('estado',)


@admin.register(ResponsableKPI)
class ResponsableKPIAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'indicador',
        'usuario',
        'fecha_asignacion',
        'estado',
    )
    search_fields = ('indicador__nombre', 'usuario__username')
    list_filter = ('estado',)


@admin.register(EstadoCumplimiento)
class EstadoCumplimientoAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'color', 'estado')
    search_fields = ('nombre',)
    list_filter = ('estado',)


@admin.register(RangoKPI)
class RangoKPIAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'indicador',
        'estado_cumplimiento',
        'valor_minimo',
        'valor_maximo',
        'estado',
    )
    search_fields = ('indicador__nombre',)
    list_filter = ('estado', 'estado_cumplimiento')


@admin.register(PeriodoMedicion)
class PeriodoMedicionAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'tipo_periodo',
        'fecha_inicio',
        'fecha_fin',
        'anio',
        'mes',
        'semana',
        'dia',
    )
    list_filter = ('tipo_periodo', 'anio', 'mes')


@admin.register(Medicion)
class MedicionAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'indicador',
        'periodo',
        'meta',
        'estado_cumplimiento',
        'valor_resultado',
        'cierre_automatico',
        'fecha_medicion',
        'registrado_por',
        'archivo_importado',
        'consulta_dw',
        'fecha_registro',
    )
    search_fields = ('indicador__nombre',)
    list_filter = (
        'estado_cumplimiento',
        'cierre_automatico',
        'fecha_medicion',
        'periodo__tipo_periodo',
    )


@admin.register(Alerta)
class AlertaAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'indicador',
        'medicion',
        'tipo_alerta',
        'estado_alerta',
        'fecha_generacion',
        'fecha_revision',
        'revisado_por',
    )
    search_fields = ('indicador__nombre', 'tipo_alerta', 'mensaje')
    list_filter = ('estado_alerta', 'tipo_alerta')

