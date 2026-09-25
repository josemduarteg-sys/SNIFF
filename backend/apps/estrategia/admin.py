from django.contrib import admin

from .models import Area, ObjetivoEspecifico, ObjetivoGeneral, PlanAnual, PlanEstrategico


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


@admin.register(PlanAnual)
class PlanAnualAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'anio',
        'plan_estrategico',
        'estado',
        'creado_por',
        'fecha_creacion',
    )
    search_fields = ('anio', 'plan_estrategico__titulo')
    list_filter = ('estado', 'plan_estrategico')


@admin.register(ObjetivoEspecifico)
class ObjetivoEspecificoAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'texto_objetivo',
        'plan_anual',
        'objetivo_general',
        'creado_por',
        'fecha_creacion',
    )
    search_fields = ('texto_objetivo',)
    list_filter = ('plan_anual',)
