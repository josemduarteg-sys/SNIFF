from django.contrib import admin

from .models import Bitacora


class OrigenBitacoraFilter(admin.SimpleListFilter):
    """Etapa 4 (M7): acciones de usuarios frente a eventos del sistema."""

    title = 'origen'
    parameter_name = 'origen'

    def lookups(self, request, model_admin):
        return [(Bitacora.ORIGEN_USUARIO, 'Usuario'), (Bitacora.ORIGEN_SISTEMA, 'Sistema')]

    def queryset(self, request, queryset):
        if self.value() == Bitacora.ORIGEN_SISTEMA:
            return queryset.filter(usuario__isnull=True)

        if self.value() == Bitacora.ORIGEN_USUARIO:
            return queryset.filter(usuario__isnull=False)

        return queryset


@admin.register(Bitacora)
class BitacoraAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'autor',
        'accion',
        'modulo',
        'fecha_hora',
        'ip_usuario',
    )
    search_fields = ('usuario__username', 'accion', 'modulo', 'descripcion')
    list_filter = (OrigenBitacoraFilter, 'accion', 'modulo')
    readonly_fields = ('fecha_hora',)

    @admin.display(description='Usuario', ordering='usuario__username')
    def autor(self, obj):
        return obj.autor
