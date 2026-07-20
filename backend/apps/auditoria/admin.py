from django.contrib import admin

from .models import Bitacora


@admin.register(Bitacora)
class BitacoraAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'usuario',
        'accion',
        'modulo',
        'fecha_hora',
        'ip_usuario',
    )
    search_fields = ('usuario__username', 'accion', 'modulo', 'descripcion')
    list_filter = ('accion', 'modulo')
    readonly_fields = ('fecha_hora',)


