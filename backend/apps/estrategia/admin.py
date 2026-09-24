from django.contrib import admin

from .models import Area, PlanEstrategico, ObjetivoGeneral


@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'estado', 'fecha_creacion')
    search_fields = ('nombre',)
    list_filter = ('estado',)


@admin.register(PlanEstrategico)
class PlanEstrategicoAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'titulo',
        'estado',
        'fecha_inicio',
        'fecha_fin',
        'creado_por',
        'fecha_creacion',
    )
    search_fields = ('titulo', 'descripcion')
    list_filter = ('estado',)


@admin.register(ObjetivoGeneral)
class ObjetivoGeneralAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'texto_objetivo',
        'plan_estrategico',
        'creado_por',
        'fecha_creacion',
    )
    search_fields = ('texto_objetivo',)
    list_filter = ('plan_estrategico',)
