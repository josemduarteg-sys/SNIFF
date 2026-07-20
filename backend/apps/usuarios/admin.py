from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Rol, Usuario


@admin.register(Rol)
class RolAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'estado', 'fecha_creacion')
    search_fields = ('nombre',)
    list_filter = ('estado',)


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    model = Usuario

    list_display = (
        'id',
        'username',
        'first_name',
        'last_name',
        'correo',
        'rol',
        'estado',
        'is_staff',
        'is_active',
    )

    search_fields = (
        'username',
        'first_name',
        'last_name',
        'correo',
    )

    list_filter = (
        'rol',
        'estado',
        'is_staff',
        'is_active',
    )

    fieldsets = UserAdmin.fieldsets + (
        ('Información del sistema', {
            'fields': (
                'rol',
                'correo',
                'estado',
                'ultimo_acceso',
            )
        }),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Información del sistema', {
            'fields': (
                'correo',
                'rol',
                'estado',
            )
        }),
    )