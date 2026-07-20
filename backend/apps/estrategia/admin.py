from django.contrib import admin

from .models import Area, Estrategia, Objetivo


@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'estado', 'fecha_creacion')
    search_fields = ('nombre',)
    list_filter = ('estado',)


@admin.register(Estrategia)
class EstrategiaAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'nombre',
        'area',
        'estado',
        'fecha_inicio',
        'fecha_fin',
        'creado_por',
        'fecha_creacion',
    )
    search_fields = ('nombre', 'descripcion')
    list_filter = ('estado', 'area')


@admin.register(Objetivo)
class ObjetivoAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'nombre',
        'estrategia',
        'estado',
        'fecha_inicio',
        'fecha_fin',
        'creado_por',
        'fecha_creacion',
    )
    search_fields = ('nombre', 'descripcion')
    list_filter = ('estado', 'estrategia')